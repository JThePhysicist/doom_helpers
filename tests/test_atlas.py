from PIL import Image

from doomwad.atlas import (
    ShelfPacker,
    build_atlas,
    iter_manifest_sprites,
    load_atlas_pages,
    load_manifest,
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
