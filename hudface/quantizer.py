from __future__ import annotations

from typing import cast

from PIL import Image

from doomwad.palette import Palette

RGB = tuple[int, int, int]

DOOM_CYAN: tuple[int, int, int] = (0, 255, 255)
DEFAULT_SPRITE_SIZE: tuple[int, int] = (24, 29)


def remove_background(image: Image.Image) -> Image.Image:
    """Cut the subject out onto a transparent background via rembg.

    Kept as its own function (rather than inlined into `quantize`) so the
    pure Pillow steps below -- which is where the palette-mapping mutation
    tests live -- can be exercised without the `rembg`/`onnxruntime` extra
    installed.
    """
    from rembg import remove

    result = remove(image)
    if not isinstance(result, Image.Image):
        raise TypeError(f"rembg.remove returned unexpected type: {type(result)!r}")
    return result.convert("RGBA")


def composite_on_cyan_background(foreground_rgba: Image.Image) -> Image.Image:
    """Flatten an RGBA image onto an opaque Doom-cyan (#00FFFF) background."""
    if foreground_rgba.mode != "RGBA":
        foreground_rgba = foreground_rgba.convert("RGBA")
    background = Image.new("RGB", foreground_rgba.size, DOOM_CYAN)
    background.paste(foreground_rgba, (0, 0), mask=foreground_rgba)
    return background


def resize_to_sprite_box(image: Image.Image, size: tuple[int, int] = DEFAULT_SPRITE_SIZE) -> Image.Image:
    """Downscale `image` to fit within `size` preserving aspect ratio, then
    center it on a Doom-cyan canvas of exactly `size`."""
    target_width, target_height = size
    scale = min(target_width / image.width, target_height / image.height)
    scaled_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.convert("RGB").resize(scaled_size, Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", size, DOOM_CYAN)
    offset = ((target_width - scaled_size[0]) // 2, (target_height - scaled_size[1]) // 2)
    canvas.paste(resized, offset)
    return canvas


def quantize_to_palette(image: Image.Image, palette: Palette) -> Image.Image:
    """Map every pixel of `image` to its nearest PLAYPAL color.

    Delegates the actual Euclidean nearest-color search to
    `doomwad.palette.Palette.nearest_index` instead of reimplementing it.
    """
    rgb_image = image.convert("RGB")
    pixels = rgb_image.load()
    assert pixels is not None
    width, height = rgb_image.size
    quantized = Image.new("RGB", (width, height))
    out_pixels = quantized.load()
    assert out_pixels is not None
    for y in range(height):
        for x in range(width):
            index = palette.nearest_index(cast(RGB, pixels[x, y]))
            out_pixels[x, y] = palette.rgb(index)
    return quantized


def quantize(
    generated_image: Image.Image,
    palette: Palette,
    size: tuple[int, int] = DEFAULT_SPRITE_SIZE,
) -> Image.Image:
    """Full Phase 4 pipeline: background removal -> cyan key -> resize ->
    PLAYPAL quantization. Returns a PNG-ready RGB image."""
    foreground = remove_background(generated_image)
    keyed = composite_on_cyan_background(foreground)
    resized = resize_to_sprite_box(keyed, size)
    return quantize_to_palette(resized, palette)
