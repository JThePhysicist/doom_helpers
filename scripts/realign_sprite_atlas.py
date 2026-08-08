#!/usr/bin/env python3
"""Re-detect each sprite's tight bounding box within its atlas tile.

Run this after hand-editing atlas PNGs and before rebuild_sprite_atlas.py.
Edits rarely land pixel-perfect: a redrawn frame might come out a few
pixels smaller than its original tile, or shifted slightly within it. This
script re-scans each sprite's allotted tile (plus a small margin equal to
the atlas's packing padding, so content drawn right up to the original
edge is still caught), trims to the actual opaque pixels, and adjusts the
patch's left/top offsets so the sprite still lines up on the same anchor
point in-game. Nothing is repacked or resized on the PNG itself -- pixels
stay exactly where they are; only the manifest bookkeeping changes.

Sprites whose content touches the edge of the scanned area are flagged --
that usually means the edit spilled past its allotted tile and needs a
bigger tile (re-extract with more --padding) or a smaller redraw.

Pipeline:
    extract_sprite_atlas.py -> (hand-edit the PNGs) -> realign_sprite_atlas.py
    -> rebuild_sprite_atlas.py

Example:
    python scripts/realign_sprite_atlas.py \\
        --manifest atlases/troo/TROO_manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from doomwad.atlas import load_atlas_pages, load_manifest, realign_sprites


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", required=True, help="Path to the *_manifest.json")
    parser.add_argument(
        "--atlas-dir",
        help="Directory containing the atlas page PNGs (default: the manifest's own directory)",
    )
    parser.add_argument(
        "--output",
        help="Where to write the updated manifest (default: overwrite --manifest in place)",
    )
    parser.add_argument(
        "--alpha-threshold",
        type=int,
        default=128,
        help="Alpha value (0-255) at/above which a pixel counts as opaque (default: 128)",
    )
    parser.add_argument(
        "--margin",
        type=int,
        help="Extra pixels around each tile to search for spillover content "
        "(default: the atlas's packing padding)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report changes without writing anything"
    )
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    atlas_dir = args.atlas_dir or manifest_path.parent
    pages = load_atlas_pages(manifest, atlas_dir)

    results = realign_sprites(
        manifest, pages, alpha_threshold=args.alpha_threshold, margin=args.margin
    )

    changed = [r for r in results if r.changed]
    for r in changed:
        ox, oy, ow, oh = r.old_box
        nx, ny, nw, nh = r.new_box
        print(f"  {r.name}: {ow}x{oh}@({ox},{oy}) -> {nw}x{nh}@({nx},{ny})")

    for r in results:
        if r.warning:
            print(f"WARNING: {r.warning}")

    print(f"{len(changed)}/{len(results)} sprite(s) realigned")

    if args.dry_run:
        print("--dry-run: manifest not written")
        return 0

    output_path = Path(args.output) if args.output else manifest_path
    output_path.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
