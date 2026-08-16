from PIL import Image

from doomwad.palette import Palette
from hudface.quantizer import (
    DOOM_CYAN,
    composite_on_cyan_background,
    quantize,
    quantize_to_palette,
    resize_to_sprite_box,
)


def _ramp_palette() -> Palette:
    colors = [(i, (i * 5) % 256, (i * 9) % 256) for i in range(256)]
    return Palette(colors)


def test_composite_on_cyan_background_fills_transparent_pixels():
    fg = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    result = composite_on_cyan_background(fg)
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == DOOM_CYAN
    assert result.getpixel((1, 1)) == DOOM_CYAN


def test_composite_on_cyan_background_preserves_opaque_pixels():
    fg = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    fg.putpixel((0, 0), (255, 0, 0, 255))
    result = composite_on_cyan_background(fg)
    assert result.getpixel((0, 0)) == (255, 0, 0)
    assert result.getpixel((1, 1)) == DOOM_CYAN


def test_composite_on_cyan_background_converts_non_rgba_input():
    # A plain "RGB" source has no alpha channel to use as a paste mask, so
    # the function must convert it to RGBA (fully opaque) first.
    fg = Image.new("RGB", (2, 2), (255, 0, 0))
    result = composite_on_cyan_background(fg)
    assert result.getpixel((0, 0)) == (255, 0, 0)
    assert result.getpixel((1, 1)) == (255, 0, 0)


def test_resize_to_sprite_box_matches_requested_size():
    src = Image.new("RGB", (100, 50), (255, 0, 0))
    result = resize_to_sprite_box(src, size=(24, 29))
    assert result.size == (24, 29)


def test_resize_to_sprite_box_width_limited_pads_top_and_bottom():
    # 100x50 into a 24x29 box: scale = min(24/100, 29/50) = 0.24 (width is
    # the limiting dimension) -> scaled content is 24x12, centered with an
    # 8px cyan band above (rows 0-7) and below (rows 20-28).
    src = Image.new("RGB", (100, 50), (255, 0, 0))
    result = resize_to_sprite_box(src, size=(24, 29))
    assert result.getpixel((12, 7)) == DOOM_CYAN
    assert result.getpixel((12, 8)) == (255, 0, 0)
    assert result.getpixel((12, 19)) == (255, 0, 0)
    assert result.getpixel((12, 20)) == DOOM_CYAN


def test_resize_to_sprite_box_height_limited_pads_left_and_right():
    # 100x200 into a 24x29 box: scale = min(24/100, 29/200) = 0.145 (height
    # is the limiting dimension) -> scaled content is 14x29 (fills the box
    # vertically), centered with a 5px cyan band on each side.
    src = Image.new("RGB", (100, 200), (0, 255, 0))
    result = resize_to_sprite_box(src, size=(24, 29))
    assert result.getpixel((4, 14)) == DOOM_CYAN
    assert result.getpixel((5, 14)) == (0, 255, 0)
    assert result.getpixel((18, 14)) == (0, 255, 0)
    assert result.getpixel((19, 14)) == DOOM_CYAN


def test_quantize_to_palette_leaves_exact_palette_colors_unchanged():
    palette = _ramp_palette()
    color = palette.rgb(42)
    image = Image.new("RGB", (2, 2), color)
    result = quantize_to_palette(image, palette)
    assert result.getpixel((0, 0)) == color
    assert result.getpixel((1, 1)) == color


def test_quantize_to_palette_maps_off_palette_color_to_nearest():
    palette = Palette([(i, i, i) for i in range(256)])  # grayscale ramp
    image = Image.new("RGB", (1, 1), (100, 100, 103))  # nearest is index 101 or 102
    result = quantize_to_palette(image, palette)
    r, g, b = result.getpixel((0, 0))
    assert r == g == b
    assert abs(r - 101.5) <= 1.5


def test_quantize_to_palette_converts_non_rgb_input():
    palette = _ramp_palette()
    color = palette.rgb(42)
    image = Image.new("RGBA", (1, 1), (*color, 255))
    result = quantize_to_palette(image, palette)
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == color


def test_quantize_to_palette_breaks_exact_ties_by_first_index():
    # 100 and 102 are equidistant from 101 -- Palette.nearest_index must
    # pick the first minimum encountered (lower index) deterministically.
    palette = Palette([(0, 0, 0)] * 100 + [(100, 100, 100)] + [(102, 102, 102)] + [(0, 0, 0)] * 154)
    image = Image.new("RGB", (1, 1), (101, 101, 101))
    result = quantize_to_palette(image, palette)
    assert result.getpixel((0, 0)) == (100, 100, 100)


def test_quantize_full_pipeline_without_rembg(monkeypatch):
    palette = _ramp_palette()

    def fake_remove_background(image: Image.Image) -> Image.Image:
        return image.convert("RGBA")

    monkeypatch.setattr("hudface.quantizer.remove_background", fake_remove_background)

    source = Image.new("RGB", (48, 58), palette.rgb(10))
    result = quantize(source, palette, size=(24, 29))
    assert result.size == (24, 29)
    assert result.mode == "RGB"


def test_quantize_honors_a_non_default_size(monkeypatch):
    palette = _ramp_palette()

    def fake_remove_background(image: Image.Image) -> Image.Image:
        return image.convert("RGBA")

    monkeypatch.setattr("hudface.quantizer.remove_background", fake_remove_background)

    source = Image.new("RGB", (48, 58), palette.rgb(10))
    result = quantize(source, palette, size=(10, 10))
    assert result.size == (10, 10)
