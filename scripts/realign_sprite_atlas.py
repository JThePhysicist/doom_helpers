#!/usr/bin/env python3
"""Compatibility wrapper for doomwad atlas realign."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from doomwad.commands.realign import main

if __name__ == '__main__':
    raise SystemExit(main())
