from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from doomface.quantizer import (
    CYAN_RGB,
    MediaPipeSelfieSegmenter,
    apply_cyan_background,
    quantize_to_palette,
    quantize_to_wad_sprite,
    resize_to_sprite,
    save_sprite,
)
from doomwad import Palette


def _grayscale_palette_with_cyan() -> Palette:
    colors = [(i, i, i) for i in range(255)] + [CYAN_RGB]
    return Palette(colors)


class _FakeSegmenter:
    def __init__(self, mask: np.ndarray) -> None:
        self._mask = mask

    def segment(self, image: np.ndarray) -> np.ndarray:
        return self._mask


def test_resize_to_sprite_preserves_aspect_ratio() -> None:
    image = Image.new("RGB", (200, 100), color=(1, 2, 3))
    resized = resize_to_sprite(image, target_height=29)
    assert resized.height == 29
    assert resized.width == 58  # 200/100 aspect * 29


def test_resize_to_sprite_never_collapses_to_zero_width() -> None:
    # extreme aspect ratio: 29 * (1/1000) rounds down to 0 without the floor
    image = Image.new("RGB", (1, 1000), color=(1, 2, 3))
    resized = resize_to_sprite(image, target_height=29)
    assert resized.width == 1


def test_resize_to_sprite_matches_spec_default_footprint() -> None:
    # a roughly-portrait crop should land close to the classic 24x29 footprint
    image = Image.new("RGB", (166, 200), color=(1, 2, 3))
    resized = resize_to_sprite(image)
    assert resized.height == 29
    assert resized.width == 24


def test_apply_cyan_background_replaces_only_masked_out_pixels() -> None:
    image = Image.new("RGB", (2, 2), color=(10, 20, 30))
    mask = np.array([[True, False], [False, True]])

    keyed = apply_cyan_background(image, mask)
    result = np.asarray(keyed)

    assert tuple(result[0, 0]) == (10, 20, 30)
    assert tuple(result[0, 1]) == CYAN_RGB
    assert tuple(result[1, 0]) == CYAN_RGB
    assert tuple(result[1, 1]) == (10, 20, 30)


def test_apply_cyan_background_does_not_mutate_source_image() -> None:
    image = Image.new("RGB", (2, 2), color=(10, 20, 30))
    mask = np.zeros((2, 2), dtype=bool)
    apply_cyan_background(image, mask)
    assert image.getpixel((0, 0)) == (10, 20, 30)


def test_quantize_to_palette_exact_match_is_lossless() -> None:
    palette = _grayscale_palette_with_cyan()
    image = Image.new("RGB", (1, 1), color=(100, 100, 100))

    indexed = quantize_to_palette(image, palette)

    assert indexed.mode == "P"
    assert indexed.getpixel((0, 0)) == 100
    assert indexed.getpalette()[300:303] == [100, 100, 100]


def test_quantize_to_palette_picks_nearest_color_by_euclidean_distance() -> None:
    palette = _grayscale_palette_with_cyan()
    # 101 is exactly between 100 and 102 in this ramp; nearest_index breaks
    # ties by taking the first color scanned with the minimum distance.
    image = Image.new("RGB", (1, 1), color=(101, 101, 101))

    indexed = quantize_to_palette(image, palette)

    assert indexed.getpixel((0, 0)) == 101  # exact match wins outright


def test_quantize_to_palette_drops_alpha_from_rgba_input() -> None:
    palette = _grayscale_palette_with_cyan()
    image = Image.new("RGBA", (1, 1), color=(100, 100, 100, 0))  # fully transparent

    indexed = quantize_to_palette(image, palette)

    # alpha must be ignored entirely -- mapped by RGB alone, not left as RGBA
    assert indexed.mode == "P"
    assert indexed.getpixel((0, 0)) == 100


def test_quantize_to_palette_breaks_ties_toward_lower_index() -> None:
    # a palette where two entries are equidistant from the sampled color
    palette = Palette([(0, 0, 0), (10, 0, 0)] + [(0, 0, 0)] * 254)
    image = Image.new("RGB", (1, 1), color=(5, 0, 0))  # equidistant from both

    indexed = quantize_to_palette(image, palette)

    assert indexed.getpixel((0, 0)) == 0


def test_quantize_to_palette_maps_exact_cyan_to_its_palette_slot() -> None:
    palette = _grayscale_palette_with_cyan()
    image = Image.new("RGB", (1, 1), color=CYAN_RGB)

    indexed = quantize_to_palette(image, palette)

    assert indexed.getpixel((0, 0)) == 255


def test_quantize_to_palette_handles_multiple_unique_colors() -> None:
    palette = _grayscale_palette_with_cyan()
    image = Image.new("RGB", (2, 1))
    image.putpixel((0, 0), (0, 0, 0))
    image.putpixel((1, 0), (254, 254, 254))

    indexed = quantize_to_palette(image, palette)

    assert indexed.getpixel((0, 0)) == 0
    assert indexed.getpixel((1, 0)) == 254


def test_save_sprite_uses_only_the_basename_of_target_filename(tmp_path: Path) -> None:
    image = Image.new("P", (2, 2))
    image.putpalette([0, 0, 0] * 256)

    out_path = save_sprite(image, "some/other/dir/STFOUCH2.png", tmp_path)

    assert out_path == tmp_path / "STFOUCH2.png"
    assert out_path.is_file()


def test_save_sprite_creates_output_dir(tmp_path: Path) -> None:
    image = Image.new("P", (1, 1))
    image.putpalette([0, 0, 0] * 256)
    nested = tmp_path / "does" / "not" / "exist"

    out_path = save_sprite(image, "STFGOD0.png", nested)

    assert out_path.is_file()


def test_quantize_to_wad_sprite_end_to_end(tmp_path: Path) -> None:
    palette = _grayscale_palette_with_cyan()
    generated = Image.new("RGB", (40, 48), color=(50, 50, 50))
    mask = np.ones((29, round(29 * 40 / 48)), dtype=bool)
    mask[:5, :] = False  # top strip is "background"
    segmenter = _FakeSegmenter(mask)

    out_path = quantize_to_wad_sprite(
        generated, palette, "STFST00.png", tmp_path, segmenter
    )

    assert out_path == tmp_path / "STFST00.png"
    saved = Image.open(out_path)
    assert saved.mode == "P"
    assert saved.height == 29
    saved_array = np.asarray(saved.convert("RGB"))
    assert tuple(saved_array[0, 0]) == CYAN_RGB
    assert tuple(saved_array[-1, 0]) == (50, 50, 50)


def test_quantize_to_wad_sprite_respects_explicit_target_height(tmp_path: Path) -> None:
    palette = _grayscale_palette_with_cyan()
    generated = Image.new("RGB", (40, 48), color=(50, 50, 50))
    segmenter = _FakeSegmenter(np.ones((10, round(10 * 40 / 48)), dtype=bool))

    out_path = quantize_to_wad_sprite(
        generated, palette, "STFGOD0.png", tmp_path, segmenter, target_height=10
    )

    assert Image.open(out_path).height == 10


def test_quantize_to_wad_sprite_feeds_the_segmenter_three_channels(tmp_path: Path) -> None:
    # generated_image is RGBA; the segmenter must still receive an (H, W, 3)
    # array, proving the RGB conversion before segmentation actually ran.
    palette = _grayscale_palette_with_cyan()
    generated = Image.new("RGBA", (40, 48), color=(50, 50, 50, 255))

    class _ShapeCheckingSegmenter:
        def segment(self, image: np.ndarray) -> np.ndarray:
            assert image.shape[-1] == 3
            return np.ones(image.shape[:2], dtype=bool)

    out_path = quantize_to_wad_sprite(
        generated, palette, "STFDEAD0.png", tmp_path, _ShapeCheckingSegmenter()
    )

    saved_array = np.asarray(Image.open(out_path).convert("RGB"))
    assert tuple(saved_array[0, 0]) == (50, 50, 50)


def test_media_pipe_selfie_segmenter_missing_model_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        MediaPipeSelfieSegmenter(tmp_path / "does_not_exist.tflite")
