from PIL import Image

from doomwad.palette import Palette
from doomwad.sprites import (
    decode_patch,
    encode_patch,
    find_sprite_lumps,
    list_sprite_prefixes,
    sprite_name_matches,
)
from doomwad.wad import Wad


def _test_palette() -> Palette:
    colors = [(i, (i * 3) % 256, (i * 7) % 256) for i in range(256)]
    return Palette(colors)


def _sample_image(palette: Palette) -> Image.Image:
    # A small sprite with a transparent border, a solid block, and a hole
    # in the middle -- exercises multiple posts per column. Colors are
    # sampled directly from the palette so the round trip is lossless.
    fill = palette.rgb(11)
    accent = palette.rgb(200)
    img = Image.new("RGBA", (6, 8), (0, 0, 0, 0))
    px = img.load()
    for x in range(1, 5):
        for y in range(1, 7):
            if y == 4:
                continue  # transparent gap -> forces a second post
            px[x, y] = (*fill, 255)
    px[2, 2] = (*accent, 255)
    return img


def test_encode_decode_round_trip_preserves_pixels_and_offsets():
    palette = _test_palette()
    original = _sample_image(palette)

    data = encode_patch(original, left_offset=3, top_offset=-2, palette=palette)
    decoded = decode_patch("TESTA1", data, palette)

    assert decoded.left_offset == 3
    assert decoded.top_offset == -2
    assert decoded.image.size == original.size

    for x in range(original.width):
        for y in range(original.height):
            orig_px = original.getpixel((x, y))
            dec_px = decoded.image.getpixel((x, y))
            if orig_px[3] < 128:
                assert dec_px[3] == 0
            else:
                assert dec_px[:3] == orig_px[:3]
                assert dec_px[3] == 255


def test_encode_rejects_oversized_height():
    palette = _test_palette()
    img = Image.new("RGBA", (2, 300), (0, 0, 0, 255))
    try:
        encode_patch(img, 0, 0, palette)
        assert False, "expected ValueError for oversized patch"
    except ValueError:
        pass


def test_sprite_name_matches():
    assert sprite_name_matches("TROOA1", "TROO")
    assert sprite_name_matches("TROOA2A8", "TROO")
    assert not sprite_name_matches("POSSA1", "TROO")
    assert not sprite_name_matches("TROO", "TROO")  # missing frame/rotation
    assert not sprite_name_matches("MAP01", "TROO")


def test_find_sprite_lumps_respects_markers_and_prefix():
    wad = Wad()
    wad.add("DEMO1", b"")
    wad.add("S_START", b"")
    wad.add("TROOA1", b"patchdata")
    wad.add("TROOA2A8", b"patchdata")
    wad.add("POSSA1", b"otherpatch")
    wad.add("S_END", b"")
    wad.add("PLAYPAL", b"\x00" * 768)

    found = find_sprite_lumps(wad, ["TROO"])
    assert [lump.name for lump in found] == ["TROOA1", "TROOA2A8"]


def test_list_sprite_prefixes_groups_and_excludes_non_sprites():
    wad = Wad()
    wad.add("DEMO1", b"")
    wad.add("S_START", b"")
    wad.add("TROOA1", b"")
    wad.add("TROOA2A8", b"")
    wad.add("TROOB1", b"")
    wad.add("POSSA1", b"")
    wad.add("S_END", b"")
    wad.add("PLAYPAL", b"\x00" * 768)

    prefixes = list_sprite_prefixes(wad)

    assert prefixes == {
        "POSS": ["POSSA1"],
        "TROO": ["TROOA1", "TROOA2A8", "TROOB1"],
    }
