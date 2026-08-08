#!/usr/bin/env python3
"""Reassemble sprites from atlas PNG page(s) + manifest.json back into a PWAD.

Reads the manifest written by extract_sprite_atlas.py, crops each sprite's
tile back out of its atlas page, re-encodes it as a Doom picture-format
lump using the palette embedded in the manifest, and writes the lumps into
a PWAD (creating a new one, or updating an existing WAD/PWAD in place).

Example:
    python scripts/rebuild_sprite_atlas.py \\
        --manifest atlases/troo/TROO_manifest.json \\
        --output mymod.wad
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from doomwad.atlas import iter_manifest_sprites, load_atlas_pages, load_manifest
from doomwad.palette import Palette
from doomwad.sprites import encode_patch
from doomwad.wad import Wad


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
        "--wad",
        help="Existing WAD/PWAD to update (sprite lumps are replaced if present, "
        "appended otherwise). If omitted, a fresh PWAD is created.",
    )
    parser.add_argument("--output", required=True, help="Path to write the resulting PWAD to")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    atlas_dir = args.atlas_dir or manifest_path.parent

    pages = load_atlas_pages(manifest, atlas_dir)
    palette = Palette.from_manifest(manifest["palette"])

    wad = Wad.load(args.wad) if args.wad else Wad(wad_type="PWAD")

    count = 0
    for name, image, left_offset, top_offset in iter_manifest_sprites(manifest, pages):
        data = encode_patch(image, left_offset, top_offset, palette)
        if name in wad:
            wad.replace(name, data)
        else:
            wad.add(name, data)
        count += 1

    wad.save(args.output)
    print(f"Wrote {count} sprite(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
