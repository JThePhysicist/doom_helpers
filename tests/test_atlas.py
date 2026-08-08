from PIL import Image

from doomwad.atlas import (
    ShelfPacker,
    build_atlas,
    iter_manifest_sprites,
    load_atlas_pages,
    load_manifest,
    realign_sprites,
    save_atlas,
)
from doomwad.exceptions import DoomWadError
from doomwad.palette import Palette
from doomwad.sprites import DecodedPatch, encode_patch


def _test_palette() -> Palette:
    colors = [(i, (i * 5) % 256, (i * 9) % 256) for i in range(256)]
    return Palette(colors)


def _solid_patch(name: str, w: int, h: int, color) -> DecodedPatch:
    img = Image.new("RGBA", (w, h), (*color, 255))
    return DecodedPatch(name=name, image=img, left_offset=w // 2, top_offset=h)


def test_shelf_packer_fits_four_same_size_tiles_on_one_page():
    packer = ShelfPacker(size=1024, padding=0)
    items = [(f"S{i}", 255, 255) for i in range(4)]
    placements = packer.pack(items)
    assert packer.page_count == 1
    assert {p.name for p in placements} == {"S0", "S1", "S2", "S3"}
    for p in placements:
        assert p.x + p.width <= 1024
        assert p.y + p.height <= 1024


def test_shelf_packer_overflows_to_second_page():
    # 512x512 tiles: only 4 fit per 1024x1024 page, so a 5th must spill over.
    packer = ShelfPacker(size=1024, padding=0)
    items = [(f"S{i}", 512, 512) for i in range(5)]
    placements = packer.pack(items)
    assert packer.page_count == 2
    pages_used = {p.page for p in placements}
    assert pages_used == {0, 1}


def test_shelf_packer_rejects_oversized_sprite():
    packer = ShelfPacker(size=1024, padding=0)
    try:
        packer.pack([("HUGE", 2000, 10)])
        assert False, "expected DoomWadError"
    except DoomWadError as exc:
        assert "larger than the atlas size" in str(exc)


def test_build_atlas_and_manifest_round_trip(tmp_path):
    palette = _test_palette()
    patches = [
        _solid_patch("TROOA1", 40, 60, palette.rgb(5)),
        _solid_patch("TROOA2A8", 40, 60, palette.rgb(6)),
        _solid_patch("TROOB1", 50, 70, palette.rgb(7)),
    ]

    pages, manifest = build_atlas(patches, palette, atlas_size=1024, padding=2)
    page_paths, manifest_path = save_atlas(pages, manifest, tmp_path, "TROO")

    assert len(page_paths) == 1
    assert manifest_path.exists()

    loaded_manifest = load_manifest(manifest_path)
    assert loaded_manifest["atlas_size"] == 1024
    assert len(loaded_manifest["sprites"]) == 3

    loaded_pages = load_atlas_pages(loaded_manifest, tmp_path)
    reloaded_palette = Palette.from_manifest(loaded_manifest["palette"])

    sprites = iter_manifest_sprites(loaded_manifest, loaded_pages)
    names = {name for name, _img, _l, _t in sprites}
    assert names == {"TROOA1", "TROOA2A8", "TROOB1"}

    by_name = {p.name: p for p in patches}
    for name, image, left_offset, top_offset in sprites:
        original = by_name[name]
        assert image.size == original.image.size
        assert left_offset == original.left_offset
        assert top_offset == original.top_offset
        # every sprite should still re-encode cleanly with the recovered palette
        encode_patch(image, left_offset, top_offset, reloaded_palette)


def _blank_page(size=(200, 200)) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _paint_rect(page: Image.Image, box, color=(50, 60, 70, 255)) -> None:
    x0, y0, x1, y1 = box
    fill = Image.new("RGBA", (x1 - x0, y1 - y0), color)
    page.paste(fill, (x0, y0))


def _single_sprite_manifest(x, y, w, h, left_offset, top_offset, padding=2) -> dict:
    return {
        "version": 1,
        "atlas_size": 200,
        "padding": padding,
        "palette": Palette([(0, 0, 0)] * 256).to_manifest(),
        "pages": ["page0.png"],
        "sprites": [
            {
                "name": "TROOA1",
                "page": 0,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "left_offset": left_offset,
                "top_offset": top_offset,
            }
        ],
    }


def test_realign_trims_shifted_content_and_adjusts_offsets():
    # Tile reserved at (10, 10, 40, 60), but the edited artwork only fills a
    # 30x40 patch of it, shifted 3px right and 5px down from the tile origin.
    manifest = _single_sprite_manifest(x=10, y=10, w=40, h=60, left_offset=20, top_offset=60)
    page = _blank_page()
    _paint_rect(page, (13, 15, 43, 55))

    results = realign_sprites(manifest, [page])

    assert len(results) == 1
    r = results[0]
    assert r.changed
    assert r.warning is None
    assert r.dx == 3
    assert r.dy == 5
    assert r.new_box == (13, 15, 30, 40)

    entry = manifest["sprites"][0]
    assert (entry["x"], entry["y"], entry["width"], entry["height"]) == (13, 15, 30, 40)
    assert entry["left_offset"] == 20 - 3
    assert entry["top_offset"] == 60 - 5


def test_realign_flags_content_touching_search_margin():
    # Artwork drawn right up to (and past) the padding margin on the right
    # edge -- should be flagged as possibly clipped.
    manifest = _single_sprite_manifest(x=10, y=10, w=40, h=60, left_offset=20, top_offset=60)
    page = _blank_page()
    _paint_rect(page, (40, 20, 52, 30))  # spills into the 2px margin, touches its edge

    results = realign_sprites(manifest, [page])

    assert results[0].warning is not None
    assert "TROOA1" in results[0].warning


def test_realign_leaves_fully_transparent_sprite_unchanged():
    manifest = _single_sprite_manifest(x=10, y=10, w=40, h=60, left_offset=20, top_offset=60)
    page = _blank_page()  # nothing painted -- sprite was deleted/never drawn

    results = realign_sprites(manifest, [page])

    assert not results[0].changed
    assert results[0].warning is not None
    assert "transparent" in results[0].warning
    entry = manifest["sprites"][0]
    assert (entry["x"], entry["y"], entry["width"], entry["height"]) == (10, 10, 40, 60)
