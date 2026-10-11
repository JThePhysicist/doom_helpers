"""Installed command implementations and consistent user-facing failures."""
import argparse
import struct
import sys

from PIL import Image
from doomwad.exceptions import DoomWadError


def execute(action,args,parser):
    try:
        return action(args,parser)
    except (DoomWadError,OSError,ValueError,struct.error,Image.DecompressionBombError) as exc:
        if getattr(args,'debug',False): raise
        print(f'{parser.prog}: error: {exc}',file=sys.stderr)
        return 1


def legacy_main(module,argv=None):
    parser=argparse.ArgumentParser(description=module.__doc__)
    module.configure_parser(parser)
    args=parser.parse_args(argv)
    return execute(module.run,args,parser)
