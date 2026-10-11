from __future__ import annotations

import json
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from PIL import Image

from .exceptions import DoomWadError
from .palette import Palette
from .manifest import validate_manifest
from .storage import atomic_batch
from .sprites import DecodedPatch

MANIFEST_VERSION = 1
DEFAULT_ATLAS_SIZE = 1024
DEFAULT_PADDING = 2


def allocate_regions(manifest):
    """Assign disjoint immutable search rectangles, including diagonal neighbors."""
    size = manifest['atlas_size']
    margin = manifest['padding']
    entries = manifest['sprites']
    for entry in entries:
        if 'allocation' in entry:
            continue
        x, y, w, h = (entry[k] for k in ('x', 'y', 'width', 'height'))
        left, top = max(0, x-margin), max(0, y-margin)
        right, bottom = min(size, x+w+margin), min(size, y+h+margin)
        for other in entries:
            if other is entry or other['page'] != entry['page']:
                continue
            ox, oy, ow, oh = (other[k] for k in ('x', 'y', 'width', 'height'))
            gx = max(ox-(x+w), x-(ox+ow))
            gy = max(oy-(y+h), y-(oy+oh))
            if gx < 0 and gy < 0:
                raise DoomWadError('Overlapping sprite tiles cannot receive editing regions')
            if gx >= gy:
                if ox >= x+w:
                    right = min(right, (x+w+ox)//2)
                else:
                    left = max(left, (ox+ow+x)//2)
            elif oy >= y+h:
                bottom = min(bottom, (y+h+oy)//2)
            else:
                top = max(top, (oy+oh+y)//2)
        entry['allocation'] = [left, top, right-left, bottom-top]
    return manifest


class Placement(NamedTuple):
    name: str
    page: int
    x: int
    y: int
    width: int
    height: int


class ShelfPacker:
    """Simple shelf (row-based) bin packer for laying sprites onto square pages."""

    def __init__(self, size: int = DEFAULT_ATLAS_SIZE, padding: int = DEFAULT_PADDING):
        if type(size) is not int or not 1 <= size <= 32767:
            raise DoomWadError('Atlas size must be a positive integer up to 32767')
        if type(padding) is not int or padding < 0:
            raise DoomWadError('Atlas padding must be a nonnegative integer')
        self.size = size
        self.padding = padding
        self._pages: list[list[dict]] = []  # per page: list of shelf dicts

    def pack(self, items: list[tuple[str, int, int]]) -> list[Placement]:
        """Pack (name, width, height) items; returns placements in page order."""
        placements: list[Placement] = []
        for name, w, h in sorted(items, key=lambda it: (-it[2], it[0])):
            if type(w) is not int or type(h) is not int or w <= 0 or h <= 0:
                raise DoomWadError('Sprite dimensions must be positive integers')
            if w > self.size or h > self.size:
                raise DoomWadError(
                    f"Sprite {name!r} ({w}x{h}) is larger than the atlas size "
                    f"({self.size}x{self.size})"
                )
            placements.append(self._place(name, w, h))
        return placements

    def _place(self, name: str, w: int, h: int) -> Placement:
        for page_index, shelves in enumerate(self._pages):
            for shelf in shelves:
                if shelf["height"] >= h and shelf["cursor_x"] + w <= self.size:
                    x, y = shelf["cursor_x"], shelf["y"]
                    shelf["cursor_x"] += w + self.padding
                    return Placement(name, page_index, x, y, w, h)
            new_y = shelves[-1]["y"] + shelves[-1]["height"] + self.padding if shelves else 0
            if new_y + h <= self.size and w <= self.size:
                shelves.append({"y": new_y, "height": h, "cursor_x": w + self.padding})
                return Placement(name, page_index, 0, new_y, w, h)

        self._pages.append([{"y": 0, "height": h, "cursor_x": w + self.padding}])
        return Placement(name, len(self._pages) - 1, 0, 0, w, h)

    @property
    def page_count(self) -> int:
        return len(self._pages)


def build_atlas(
    patches: list[DecodedPatch],
    palette: Palette,
    atlas_size: int = DEFAULT_ATLAS_SIZE,
    padding: int = DEFAULT_PADDING,
    *, preserve_indices: bool = False,
) -> tuple[list[Image.Image], dict]:
    """Pack decoded sprite patches onto 1..N square pages of `atlas_size`.

    Returns the page images and a manifest dict recording exactly where each
    sprite landed, so the packing never needs to be tracked by hand.
    """
    names = [patch.name for patch in patches]
    if len(set(names)) != len(names):
        raise DoomWadError("Duplicate sprite names cannot be represented in an atlas")
    packer = ShelfPacker(size=atlas_size, padding=padding)
    items = [(p.name, p.image.width, p.image.height) for p in patches]
    placements = packer.pack(items)

    pages = [
        Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))
        for _ in range(packer.page_count)
    ]

    by_name = {p.name: p for p in patches}
    sprite_entries = []
    for placement in placements:
        patch = by_name[placement.name]
        pages[placement.page].paste(patch.image, (placement.x, placement.y))
        if preserve_indices:
            if patch.palette_indices is None:
                raise DoomWadError('Index preservation requires decoded palette indices')
            if 'palette_indices' not in pages[placement.page].info:
                pages[placement.page].info['palette_indices'] = Image.new('L', (atlas_size, atlas_size))
            pages[placement.page].info['palette_indices'].paste(patch.palette_indices, (placement.x, placement.y))
        sprite_entries.append(
            {
                "name": placement.name,
                "page": placement.page,
                "x": placement.x,
                "y": placement.y,
                "width": placement.width,
                "height": placement.height,
                "left_offset": patch.left_offset,
                "top_offset": patch.top_offset,
            }
        )

    manifest = {
        "version": MANIFEST_VERSION,
        "atlas_size": atlas_size,
        "padding": padding,
        "palette": palette.to_manifest(),
        "pages": [f"page_{i}.png" for i in range(len(pages))],  # renamed by save_atlas
        "sprites": sprite_entries,
    }
    allocate_regions(manifest)
    return pages, manifest


def save_atlas(
    pages: list[Image.Image], manifest: dict, output_dir: str | Path, asset_name: str,
    *, overwrite: bool = False
) -> tuple[list[Path], Path]:
    """Write atlas page PNGs and the manifest JSON to `output_dir`."""
    filenames = [f"{asset_name}_{i}.png" for i in range(len(pages))]
    validate_manifest(dict(manifest, pages=filenames), pages)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_paths = []
    page_filenames = []
    outputs = []
    for i, page in enumerate(pages):
        filename = f"{asset_name}_{i}.png"
        path = output_dir / filename
        encoded = BytesIO()
        page.save(encoded, format="PNG")
        outputs.append((path, encoded.getvalue()))
        if 'palette_indices' in page.info:
            index_name = f'{asset_name}_{i}_indices.png'
            index_buffer = BytesIO()
            page.info['palette_indices'].save(index_buffer, format='PNG')
            outputs.append((output_dir / index_name, index_buffer.getvalue()))
        page_paths.append(path)
        page_filenames.append(filename)

    manifest = dict(manifest, pages=page_filenames)
    if any('palette_indices' in page.info for page in pages):
        manifest['index_pages'] = [f'{asset_name}_{i}_indices.png' for i in range(len(pages))]
    manifest_path = output_dir / f"{asset_name}_manifest.json"
    outputs.append((manifest_path, json.dumps(manifest, indent=2).encode()))
    atomic_batch(outputs, overwrite=overwrite)

    return page_paths, manifest_path


def load_manifest(path: str | Path) -> dict:
    try:
        return validate_manifest(json.loads(Path(path).read_text()))
    except (ValueError, UnicodeError) as exc:
        raise DoomWadError(f"Invalid manifest JSON: {exc}") from exc


def load_atlas_pages(manifest: dict, atlas_dir: str | Path) -> list[Image.Image]:
    validate_manifest(manifest)
    atlas_dir = Path(atlas_dir)
    pages = []
    for filename in manifest["pages"]:
        page_path = atlas_dir / filename
        if not page_path.exists():
            raise DoomWadError(f"Atlas page {page_path} referenced by manifest is missing")
        pages.append(Image.open(page_path).convert("RGBA"))
    if 'index_pages' in manifest:
        for page, filename in zip(pages, manifest['index_pages']):
            with Image.open(atlas_dir / filename) as indices:
                if indices.mode != 'L' or indices.size != page.size:
                    raise DoomWadError('Index pages must be grayscale with matching dimensions')
                page.info['palette_indices'] = indices.copy()
    validate_manifest(manifest, pages)
    return pages


def iter_manifest_sprites(
    manifest: dict, pages: list[Image.Image]
) -> "list[tuple[str, Image.Image, int, int]]":
    """Crop each sprite's tile back out of its atlas page.

    Yields (name, image, left_offset, top_offset) ready for re-encoding.
    """
    validate_manifest(manifest, pages)
    results = []
    for entry in manifest["sprites"]:
        page = pages[entry["page"]]
        x, y, w, h = entry["x"], entry["y"], entry["width"], entry["height"]
        tile = page.crop((x, y, x + w, y + h))
        if 'palette_indices' in page.info:
            tile.info['palette_indices'] = page.info['palette_indices'].crop((x,y,x+w,y+h))
        results.append((entry["name"], tile, entry["left_offset"], entry["top_offset"]))
    return results


@dataclass
class RealignResult:
    name: str
    changed: bool
    dx: int
    dy: int
    old_box: tuple[int, int, int, int]  # x, y, width, height
    new_box: tuple[int, int, int, int]
    warning: str | None = None


def realign_sprites(
    manifest: dict,
    pages: list[Image.Image],
    alpha_threshold: int = 128,
    margin: int | None = None,
) -> list[RealignResult]:
    """Re-detect each sprite's tight bounding box within its allotted tile.

    Hand-edited atlas art is rarely pixel-perfect: a redrawn frame might be
    smaller than the original tile or shifted a few pixels within it. This
    re-scans each tile (plus a small margin so content drawn right up to the
    original edge isn't missed), trims to the opaque pixels found, and
    shifts left_offset/top_offset by the same amount so the sprite's anchor
    point still lines up in-game. Pixels on the atlas page are never moved
    or resized -- only the manifest's bookkeeping is updated.

    Mutates `manifest["sprites"]` in place and also returns one
    RealignResult per sprite, so callers can report what moved and flag
    anything that looks like it spilled past its allotted space.
    """
    validate_manifest(manifest, pages)
    if margin is not None and (type(margin) is not int or margin < 0):
        raise DoomWadError("Realignment margin must be a nonnegative integer")
    if type(alpha_threshold) is not int or not 0 <= alpha_threshold <= 255:
        raise DoomWadError("Alpha threshold must be between 0 and 255")
    if margin is not None and not any('allocation' in e for e in manifest['sprites']):
        # Legacy manifests can choose their initial allocation margin once.
        allocate_regions(dict(manifest, padding=margin))
    if margin is None:
        margin = manifest.get("padding", DEFAULT_PADDING)

    allocate_regions(manifest)
    results = []
    for entry in manifest["sprites"]:
        page = pages[entry["page"]]
        page_w, page_h = page.size
        x, y, w, h = entry["x"], entry["y"], entry["width"], entry["height"]

        search_left, search_top, search_w, search_h = entry['allocation']
        search_right = search_left + search_w
        search_bottom = search_top + search_h
        region = page.crop((search_left, search_top, search_right, search_bottom))
        alpha = region.split()[-1]
        mask = alpha.point(lambda a, t=alpha_threshold: 255 if a >= t else 0)
        bbox = mask.getbbox()

        if bbox is None:
            results.append(
                RealignResult(
                    name=entry["name"],
                    changed=False,
                    dx=0,
                    dy=0,
                    old_box=(x, y, w, h),
                    new_box=(x, y, w, h),
                    warning=(
                        f"{entry['name']!r} has no opaque pixels in its tile "
                        "(fully transparent) -- left unchanged"
                    ),
                )
            )
            continue

        bx0, by0, bx1, by1 = bbox
        new_x, new_y = search_left + bx0, search_top + by0
        new_w, new_h = bx1 - bx0, by1 - by0
        dx, dy = new_x - x, new_y - y

        warning = None
        if bx0 == 0 or by0 == 0 or bx1 == region.width or by1 == region.height:
            warning = (
                f"{entry['name']!r} content touches the edge of its search area "
                f"({margin}px margin) -- it may be clipped; re-extract with more "
                "padding or shrink the artwork to fit"
            )

        entry["x"], entry["y"] = new_x, new_y
        entry["width"], entry["height"] = new_w, new_h
        entry["left_offset"] = entry["left_offset"] - dx
        entry["top_offset"] = entry["top_offset"] - dy

        results.append(
            RealignResult(
                name=entry["name"],
                changed=(dx != 0 or dy != 0 or new_w != w or new_h != h),
                dx=dx,
                dy=dy,
                old_box=(x, y, w, h),
                new_box=(new_x, new_y, new_w, new_h),
                warning=warning,
            )
        )

    return results
