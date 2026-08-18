"""Phase 4: WAD Quantizer.

Downscales a generated face to roughly the Doom status-bar face footprint,
keys out the background to exact Doom cyan, and maps every remaining pixel
to the nearest color in a 256-entry Doom PLAYPAL -- reusing
:class:`doomwad.Palette`'s cached, Euclidean-distance ``nearest_index``
lookup rather than reimplementing color-distance math. The result is saved
as a palette-indexed PNG under the original Phase 1 filename, ready for
SLADE3 import.

Background segmentation is behind the :class:`BackgroundSegmenter`
protocol so the quantization/palette-mapping logic -- the part the spec
calls out for mutation testing -- is fully unit-testable without a
MediaPipe model asset.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from doomwad import Palette

CYAN_RGB: tuple[int, int, int] = (0, 255, 255)
DEFAULT_TARGET_HEIGHT = 29


class BackgroundSegmenter(Protocol):
    """Produces a foreground mask (``True`` = keep, ``False`` = background)."""

    def segment(self, image: NDArray[np.uint8]) -> NDArray[np.bool_]: ...


def resize_to_sprite(
    image: Image.Image, target_height: int = DEFAULT_TARGET_HEIGHT
) -> Image.Image:
    """Downscale ``image`` to ``target_height`` px, preserving aspect ratio."""
    aspect = image.width / image.height
    target_width = max(1, round(target_height * aspect))
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def apply_cyan_background(
    image: Image.Image, mask: NDArray[np.bool_]
) -> Image.Image:
    """Replace every pixel where ``mask`` is ``False`` with exact Doom cyan."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    rgb[~mask] = CYAN_RGB
    return Image.fromarray(rgb, mode="RGB")


def _nearest_indices_for_unique_colors(
    unique_colors: NDArray[np.uint8], palette: Palette
) -> NDArray[np.uint8]:
    return np.array(
        [palette.nearest_index((int(r), int(g), int(b))) for r, g, b in unique_colors],
        dtype=np.uint8,
    )


def quantize_to_palette(image: Image.Image, palette: Palette) -> Image.Image:
    """Map every pixel of ``image`` to its nearest color in ``palette``.

    Returns a palette-indexed (mode "P") PNG using the exact PLAYPAL colors.
    """
    rgb_image = image.convert("RGB")
    pixels = np.asarray(rgb_image, dtype=np.uint8).reshape(-1, 3)
    unique_colors, inverse = np.unique(pixels, axis=0, return_inverse=True)

    index_lookup = _nearest_indices_for_unique_colors(unique_colors, palette)
    index_pixels = index_lookup[inverse].reshape(rgb_image.height, rgb_image.width)

    indexed = Image.fromarray(index_pixels, mode="P")
    indexed.putpalette([channel for rgb in palette.colors for channel in rgb])
    return indexed


def save_sprite(image: Image.Image, target_filename: str, output_dir: str | Path) -> Path:
    """Save ``image`` under ``target_filename`` (the Phase 1 filename) in ``output_dir``."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / Path(target_filename).name
    image.save(out_path, format="PNG")
    return out_path


def quantize_to_wad_sprite(
    generated_image: Image.Image,
    palette: Palette,
    target_filename: str,
    output_dir: str | Path,
    segmenter: BackgroundSegmenter,
    target_height: int = DEFAULT_TARGET_HEIGHT,
) -> Path:
    """Run the full Phase 4 pipeline and return the path of the saved PNG."""
    resized = resize_to_sprite(generated_image, target_height)
    mask = segmenter.segment(np.asarray(resized.convert("RGB"), dtype=np.uint8))
    keyed = apply_cyan_background(resized, mask)
    indexed = quantize_to_palette(keyed, palette)
    return save_sprite(indexed, target_filename, output_dir)


class MediaPipeSelfieSegmenter:
    """Real, local :class:`BackgroundSegmenter` backed by MediaPipe's Image Segmenter Task."""

    def __init__(self, model_asset_path: str | Path) -> None:
        model_path = Path(model_asset_path)
        if not model_path.is_file():
            raise FileNotFoundError(
                f"MediaPipe selfie segmenter model not found at {model_path!r}. "
                "Download 'selfie_segmenter.tflite' from the MediaPipe model zoo "
                "and place it there (see README) -- inference itself stays local."
            )

        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import ImageSegmenter, ImageSegmenterOptions

        options = ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            output_category_mask=True,
        )
        self._segmenter = ImageSegmenter.create_from_options(options)

    def segment(self, image: NDArray[np.uint8]) -> NDArray[np.bool_]:
        import mediapipe as mp

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        result = self._segmenter.segment(mp_image)
        category_mask: NDArray[np.uint8] = result.category_mask.numpy_view()
        # The selfie segmenter's category 0 is background, 1 is person.
        foreground: NDArray[np.bool_] = category_mask > 0
        return foreground
