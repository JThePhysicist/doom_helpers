from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from doomwad import LumpNotFoundError, Wad
from doomwad.palette import Palette
from doomwad.sprites import decode_patch

from . import generator, geometry, quantizer
from .generator import StyleKnobs
from .parser import FaceState, parse_stf_filename

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


def read_target_filenames(targets_path: str | Path) -> list[str]:
    """Read target STF filenames, one per line. Blank lines and lines
    starting with '#' are ignored."""
    lines = Path(targets_path).read_text().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def find_matching_source(sources_dir: str | Path, state: FaceState) -> "np.ndarray | None":
    """Try every file in `sources_dir`, in sorted (deterministic) order,
    until one satisfies `state`'s gaze/expression requirements.

    Returns None if nothing matches -- a plain "no match" outcome for the
    caller to handle, not an LLM-style retry/fallback.
    """
    for source_path in sorted(Path(sources_dir).iterdir()):
        if not source_path.is_file():
            continue
        try:
            return geometry.validate_and_align(str(source_path), state)
        except ValueError:
            continue
    return None


def load_reference_sprite(wad: Wad, palette: Palette, lump_name: str) -> "np.ndarray":
    """Decode the original Doom STF sprite for `lump_name` out of `wad`, for
    use as the Phase 3 IP-Adapter style reference."""
    import numpy as np

    lump = wad.find(lump_name)
    decoded = decode_patch(lump.name, lump.data, palette)
    result: np.ndarray = np.array(decoded.image.convert("RGB"))
    return result


def process_target(
    target_filename: str,
    sources_dir: str | Path,
    wad: Wad,
    palette: Palette,
    output_dir: str | Path,
    knobs: StyleKnobs | None = None,
) -> bool:
    """Run one target filename through Phases 1-4. Returns True on success."""
    state = parse_stf_filename(target_filename)

    aligned = find_matching_source(sources_dir, state)
    if aligned is None:
        logger.warning("No source photo matched %s (%s); skipping", target_filename, state)
        return False

    lump_name = Path(target_filename).stem.upper()
    try:
        reference_sprite = load_reference_sprite(wad, palette, lump_name)
    except LumpNotFoundError:
        logger.warning(
            "IWAD has no %s reference sprite; skipping %s", lump_name, target_filename
        )
        return False

    generated = generator.generate(
        aligned, reference_sprite, state.health_tier, state.expression, knobs
    )
    final = quantizer.quantize(generated, palette)

    output_path = Path(output_dir) / target_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(output_path)
    logger.info("Wrote %s", output_path)
    return True


def run(
    sources_dir: str | Path,
    targets_path: str | Path,
    iwad_path: str | Path,
    output_dir: str | Path,
    knobs: StyleKnobs | None = None,
) -> list[str]:
    """Tokenless DAG: for every target filename, parse -> align -> generate
    -> quantize -> save, in order. `knobs` (wound_intensity/tiredness/
    gore_level) is applied uniformly to every sprite in the run. Returns
    the target filenames that couldn't be produced (no matching source
    photo or missing reference sprite in the IWAD)."""
    wad = Wad.load(iwad_path)
    palette = Palette.from_wad(wad)

    failures = []
    for target_filename in read_target_filenames(targets_path):
        if not process_target(target_filename, sources_dir, wad, palette, output_dir, knobs):
            failures.append(target_filename)
    return failures


def build_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(
        description="Convert headshot photos into a Doom STF status-bar face sprite set."
    )
    arg_parser.add_argument(
        "--sources-dir", required=True, help="Directory of candidate source photos"
    )
    arg_parser.add_argument(
        "--targets", required=True, help="File listing target STF filenames, one per line"
    )
    arg_parser.add_argument(
        "--iwad", required=True, help="Doom IWAD providing PLAYPAL and reference STF sprites"
    )
    arg_parser.add_argument(
        "--output-dir", required=True, help="Directory to write generated sprites into"
    )
    arg_parser.add_argument(
        "--wound-intensity",
        type=int,
        choices=range(5),
        default=None,
        help="0 (unhurt) - 4 (most wounded); overrides each frame's own health tier. "
        "Default: derive from each target's health tier, per the real Doom face grid.",
    )
    arg_parser.add_argument(
        "--tiredness",
        type=int,
        choices=range(5),
        default=0,
        help="0 (fresh) - 4 (utterly exhausted); applied uniformly to every sprite. Default: 0.",
    )
    arg_parser.add_argument(
        "--gore-level",
        type=int,
        choices=range(5),
        default=2,
        help="0 (clean/tasteful) - 4 (extremely graphic); how explicit wound wording gets, "
        "independent of --wound-intensity. Default: 2 (moderate).",
    )
    return arg_parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_arg_parser().parse_args(argv)
    knobs = StyleKnobs(
        wound_intensity=args.wound_intensity, tiredness=args.tiredness, gore_level=args.gore_level
    )
    failures = run(args.sources_dir, args.targets, args.iwad, args.output_dir, knobs)
    if failures:
        logger.error("%d target(s) failed: %s", len(failures), ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
