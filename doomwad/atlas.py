from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from PIL import Image

from .exceptions import DoomWadError
from .palette import Palette
from .sprites import DecodedPatch

MANIFEST_VERSION = 1
DEFAULT_ATLAS_SIZE = 1024
DEFAULT_PADDING = 2


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
        self.size = size
        self.padding = padding
        self._pages: list[list[dict]] = []  # per page: list of shelf dicts

    def pack(self, items: list[tuple[str, int, int]]) -> list[Placement]:
        """Pack (name, width, height) items; returns placements in page order."""
        placements: list[Placement] = []
        for name, w, h in sorted(items, key=lambda it: it[2], reverse=True):
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
) -> tuple[list[Image.Image], dict]:
    """Pack decoded sprite patches onto 1..N square pages of `atlas_size`.

    Returns the page images and a manifest dict recording exactly where each
    sprite landed, so the packing never needs to be tracked by hand.
    """
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
        "pages": [],  # filled in by save_atlas once page filenames are known
        "sprites": sprite_entries,
    }
    return pages, manifest


def save_atlas(
    pages: list[Image.Image], manifest: dict, output_dir: str | Path, asset_name: str
) -> tuple[list[Path], Path]:
    """Write atlas page PNGs and the manifest JSON to `output_dir`."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    page_paths = []
    page_filenames = []
    for i, page in enumerate(pages):
        filename = f"{asset_name}_{i}.png"
        path = output_dir / filename
        page.save(path)
        page_paths.append(path)
        page_filenames.append(filename)

    manifest = dict(manifest, pages=page_filenames)
    manifest_path = output_dir / f"{asset_name}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return page_paths, manifest_path


def load_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def load_atlas_pages(manifest: dict, atlas_dir: str | Path) -> list[Image.Image]:
    atlas_dir = Path(atlas_dir)
    pages = []
    for filename in manifest["pages"]:
        page_path = atlas_dir / filename
        if not page_path.exists():
            raise DoomWadError(f"Atlas page {page_path} referenced by manifest is missing")
        pages.append(Image.open(page_path).convert("RGBA"))
    return pages


def iter_manifest_sprites(
    manifest: dict, pages: list[Image.Image]
) -> "list[tuple[str, Image.Image, int, int]]":
    """Crop each sprite's tile back out of its atlas page.

    Yields (name, image, left_offset, top_offset) ready for re-encoding.
    """
    results = []
    for entry in manifest["sprites"]:
        page = pages[entry["page"]]
        x, y, w, h = entry["x"], entry["y"], entry["width"], entry["height"]
        tile = page.crop((x, y, x + w, y + h))
        results.append((entry["name"], tile, entry["left_offset"], entry["top_offset"]))
    return results
