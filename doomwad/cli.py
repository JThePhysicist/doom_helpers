from __future__ import annotations

import argparse
import sys

from .sprites import list_sprite_prefixes
from .wad import Wad
from .storage import atomic_write
from .commands import execute


def cmd_list(args: argparse.Namespace) -> int:
    wad = Wad.load(args.wad)
    for i, lump in enumerate(wad.lumps):
        print(f"{i:5d}  {lump.name:<8s}  {lump.size:8d}")
    return 0


def cmd_list_sprites(args: argparse.Namespace) -> int:
    wad = Wad.load(args.wad)
    prefixes = list_sprite_prefixes(wad)
    if not prefixes:
        print("No sprite lumps found (no S_START/S_END or SS_START/SS_END range?)")
        return 0
    for prefix, names in prefixes.items():
        print(f"{prefix}  ({len(names)} lump{'s' if len(names) != 1 else ''})")
        if args.verbose:
            for name in names:
                print(f"    {name}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    wad = Wad.load(args.wad)
    print(f"Type:  {wad.wad_type}")
    print(f"Lumps: {len(wad.lumps)}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    wad = Wad.load(args.wad)
    lump = wad.find(args.lump)
    out_path = args.output or args.lump
    atomic_write(out_path, lump.data, overwrite=args.overwrite)
    print(f"Wrote {lump.size} bytes to {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doomwad", description="Inspect and edit Doom WAD files")
    parser.add_argument("--debug", action="store_true", help="Show tracebacks for diagnostics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_list = subparsers.add_parser("list", help="List lumps in a WAD")
    p_list.add_argument("wad", help="Path to the WAD file")
    p_list.set_defaults(func=cmd_list)

    p_info = subparsers.add_parser("info", help="Show summary info about a WAD")
    p_info.add_argument("wad", help="Path to the WAD file")
    p_info.set_defaults(func=cmd_info)

    p_extract = subparsers.add_parser("extract", help="Extract a lump's raw data to a file")
    p_extract.add_argument("wad", help="Path to the WAD file")
    p_extract.add_argument("lump", help="Name of the lump to extract")
    p_extract.add_argument("-o", "--output", help="Output file path")
    p_extract.add_argument("--overwrite", action="store_true")
    p_extract.set_defaults(func=cmd_extract)

    p_list_sprites = subparsers.add_parser(
        "list-sprites",
        help="List sprite entities (4-char prefixes like TROO, POSS, SARG) found in a WAD",
    )
    p_list_sprites.add_argument("wad", help="Path to the WAD file")
    p_list_sprites.add_argument(
        "-v", "--verbose", action="store_true", help="Also list each lump name per prefix"
    )
    p_list_sprites.set_defaults(func=cmd_list_sprites)

    p_atlas = subparsers.add_parser('atlas', help='Extract, realign, and rebuild sprite atlases')
    atlas_commands = p_atlas.add_subparsers(dest='atlas_command', required=True)
    from .commands import extract, realign, rebuild, preview
    for name, module in [('extract', extract), ('realign', realign), ('rebuild', rebuild), ('preview', preview)]:
        child = atlas_commands.add_parser(name, description=module.__doc__)
        module.configure_parser(child)
        child.set_defaults(func=lambda args, module=module, child=child: module.run(args, child))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return execute(lambda args, parser: args.func(args), args, parser)


if __name__ == "__main__":
    sys.exit(main())
