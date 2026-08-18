"""Phase 5: Tokenless Orchestrator.

Plain, deterministic control flow -- no agentic routing, no LLM decisions.
For each target STF filename: parse its required face state, scan the
source headshot directory in a fixed order until Phase 2 accepts one,
style-transfer it (Phase 3) against the original Doom reference sprite,
and quantize it into a WAD-ready PNG (Phase 4).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from doomwad import Palette, Wad, decode_patch

from .generator import DoomFaceGenerator, FaceStyleGenerator
from .geometry import FaceLandmarker, GeometryValidationError, validate_and_align
from .parser import FaceState, iter_standard_stf_filenames, parse_stf_filename
from .quantizer import BackgroundSegmenter, quantize_to_wad_sprite

_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")


class NoMatchingHeadshotError(RuntimeError):
    """Raised when no source headshot satisfies a target face state."""


@dataclass(frozen=True, slots=True)
class TargetResult:
    target_filename: str
    output_path: Path | None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.output_path is not None


def iter_source_images(source_dir: str | Path) -> tuple[Path, ...]:
    """List candidate headshots in ``source_dir``, in a fixed, deterministic order."""
    paths = [
        path
        for path in Path(source_dir).iterdir()
        if path.suffix.lower() in _IMAGE_SUFFIXES
    ]
    return tuple(sorted(paths))


def find_aligned_match(
    target_state: FaceState,
    source_images: Sequence[Path],
    landmarker: FaceLandmarker,
) -> NDArray[np.uint8]:
    """Return the first source headshot whose geometry matches ``target_state``."""
    for candidate in source_images:
        try:
            _, aligned = validate_and_align(str(candidate), target_state, landmarker)
        except GeometryValidationError:
            continue
        return aligned
    raise NoMatchingHeadshotError(
        f"no headshot among {len(source_images)} candidates matches "
        f"{target_state.expression.value} tier {target_state.health_tier} "
        f"gaze {target_state.gaze_direction.name}"
    )


def load_reference_sprite(
    reference_wad: Wad, palette: Palette, target_filename: str
) -> NDArray[np.uint8]:
    """Decode the original Doom sprite for ``target_filename`` as an RGB array."""
    lump_name = Path(target_filename).stem.upper()
    lump = reference_wad.find(lump_name)
    decoded = decode_patch(lump_name, lump.data, palette)
    return np.asarray(decoded.image.convert("RGB"), dtype=np.uint8)


def process_target(
    target_filename: str,
    source_images: Sequence[Path],
    palette: Palette,
    reference_wad: Wad,
    landmarker: FaceLandmarker,
    generator: FaceStyleGenerator,
    segmenter: BackgroundSegmenter,
    output_dir: str | Path,
) -> TargetResult:
    """Run Phases 1-4 for a single target STF filename."""
    try:
        target_state = parse_stf_filename(target_filename)
        aligned = find_aligned_match(target_state, source_images, landmarker)
        reference_sprite = load_reference_sprite(reference_wad, palette, target_filename)
        generated = generator.generate(aligned, reference_sprite, target_state.health_tier)
        output_path = quantize_to_wad_sprite(
            generated, palette, target_filename, output_dir, segmenter
        )
    except (NoMatchingHeadshotError, GeometryValidationError, ValueError) as exc:
        return TargetResult(target_filename, output_path=None, error=str(exc))
    return TargetResult(target_filename, output_path=output_path)


def run_pipeline(
    target_filenames: Sequence[str],
    source_dir: str | Path,
    palette: Palette,
    reference_wad: Wad,
    landmarker: FaceLandmarker,
    generator: FaceStyleGenerator,
    segmenter: BackgroundSegmenter,
    output_dir: str | Path,
) -> tuple[TargetResult, ...]:
    """Iterate every target filename through the DAG, in order."""
    source_images = iter_source_images(source_dir)
    return tuple(
        process_target(
            target_filename,
            source_images,
            palette,
            reference_wad,
            landmarker,
            generator,
            segmenter,
            output_dir,
        )
        for target_filename in target_filenames
    )


def _load_palette(playpal_path: str | Path) -> Palette:
    path = Path(playpal_path)
    if path.suffix.lower() == ".wad":
        return Palette.from_wad(Wad.load(str(path)))
    return Palette.from_playpal_bytes(path.read_bytes())


def _load_target_filenames(args: argparse.Namespace) -> tuple[str, ...]:
    if args.targets_file is not None:
        lines = Path(args.targets_file).read_text().splitlines()
        return tuple(line.strip() for line in lines if line.strip())
    if args.target:
        return tuple(args.target)
    return iter_standard_stf_filenames()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doomface",
        description="Tokenless Doom HUD sprite style-transfer pipeline",
    )
    parser.add_argument("--source-dir", required=True, help="Directory of source headshots")
    parser.add_argument(
        "--playpal", required=True, help="Path to a PLAYPAL .wad or a raw .pal palette file"
    )
    parser.add_argument(
        "--reference-wad",
        required=True,
        help="WAD containing the original STF sprites used as IP-Adapter style references",
    )
    parser.add_argument(
        "--face-model", required=True, help="Path to MediaPipe's face_landmarker.task"
    )
    parser.add_argument(
        "--segmenter-model", required=True, help="Path to MediaPipe's selfie_segmenter.tflite"
    )
    parser.add_argument("--output-dir", required=True, help="Directory to write sprite PNGs to")
    parser.add_argument(
        "--target",
        action="append",
        help="A target STF filename (repeatable); defaults to all 42 standard faces",
    )
    parser.add_argument(
        "--targets-file", help="Text file of target STF filenames, one per line"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from .geometry import MediaPipeFaceLandmarker
    from .quantizer import MediaPipeSelfieSegmenter

    args = build_arg_parser().parse_args(argv)

    palette = _load_palette(args.playpal)
    reference_wad = Wad.load(args.reference_wad)
    landmarker = MediaPipeFaceLandmarker(args.face_model)
    generator = DoomFaceGenerator()
    segmenter = MediaPipeSelfieSegmenter(args.segmenter_model)
    target_filenames = _load_target_filenames(args)

    results = run_pipeline(
        target_filenames,
        args.source_dir,
        palette,
        reference_wad,
        landmarker,
        generator,
        segmenter,
        args.output_dir,
    )

    for result in results:
        status = str(result.output_path) if result.succeeded else f"FAILED: {result.error}"
        print(f"{result.target_filename}: {status}")

    return 0 if all(result.succeeded for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
