from __future__ import annotations

import argparse
import sys

from .wad import Wad


def cmd_list(args: argparse.Namespace) -> int:
    wad = Wad.load(args.wad)
    for i, lump in enumerate(wad.lumps):
        print(f"{i:5d}  {lump.name:<8s}  {lump.size:8d}")
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
    with open(out_path, "wb") as f:
        f.write(lump.data)
    print(f"Wrote {lump.size} bytes to {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doomwad", description="Inspect and edit Doom WAD files")
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
    p_extract.set_defaults(func=cmd_extract)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
