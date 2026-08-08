#!/usr/bin/env python3
"""Extract sprites for one or more sprite prefixes out of a WAD and pack
them into square PNG atlas page(s) (1024x1024 by default), plus a manifest
that records exactly where each sprite landed.

Sprites are packed with a shelf-based bin packer: as many as fit are placed
on one page, and additional pages are created automatically once a page
fills up. Nothing about the layout needs to be tracked by hand -- it's all
recorded in <output-dir>/<asset>_manifest.json, which the companion
rebuild_sprite_atlas.py script reads back.

Example:
    python scripts/extract_sprite_atlas.py --wad DOOM2.WAD --sprite TROO \\
        --output-dir atlases/troo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from doomwad.atlas import DEFAULT_ATLAS_SIZE, DEFAULT_PADDING, build_atlas, save_atlas
from doomwad.exceptions import DoomWadError
from doomwad.palette import Palette
from doomwad.sprites import decode_patch, find_sprite_lumps
from doomwad.wad import Wad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--wad", required=True, help="WAD file containing the sprites")
    parser.add_argument(
        "--palette-wad",
        help="WAD to read PLAYPAL from, if different from --wad (e.g. the IWAD, "
        "since PWADs usually don't carry their own palette)",
    )
    parser.add_argument(
        "--sprite",
        "--asset",
        dest="sprites",
        action="append",
        required=True,
        metavar="PREFIX",
        help="Sprite name prefix to extract (e.g. TROO). Repeat to pack several "
        "sprites' frames into the same atlas set.",
    )
    parser.add_argument(
        "--output-dir", help="Directory to write PNGs + manifest to (default: <asset>_atlas)"
    )
    parser.add_argument(
        "--atlas-size", type=int, default=DEFAULT_ATLAS_SIZE, help="Page width/height in pixels"
    )
    parser.add_argument(
        "--padding", type=int, default=DEFAULT_PADDING, help="Pixels of spacing between tiles"
    )
    args = parser.parse_args(argv)

    wad = Wad.load(args.wad)
    palette_wad = Wad.load(args.palette_wad) if args.palette_wad else wad
    try:
        palette = Palette.from_wad(palette_wad)
    except DoomWadError:
        parser.error(
            "No PLAYPAL lump found in "
            f"{args.palette_wad or args.wad}. Pass --palette-wad pointing at a "
            "WAD (e.g. the IWAD) that has one."
        )

    lumps = find_sprite_lumps(wad, args.sprites)
    if not lumps:
        parser.error(f"No sprites found matching: {', '.join(args.sprites)}")

    patches = [decode_patch(lump.name, lump.data, palette) for lump in lumps]

    pages, manifest = build_atlas(
        patches, palette, atlas_size=args.atlas_size, padding=args.padding
    )

    asset_name = "_".join(args.sprites)
    output_dir = args.output_dir or f"{asset_name}_atlas"
    page_paths, manifest_path = save_atlas(pages, manifest, output_dir, asset_name)

    print(f"Extracted {len(patches)} sprite(s) across {len(page_paths)} page(s):")
    for path in page_paths:
        print(f"  {path}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
