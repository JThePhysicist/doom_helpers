# doomwad

A Python library and CLI for reading and editing Doom WAD files.

## Project layout

```
doom_helpers/
├── doomwad/            # library source
│   ├── __init__.py     # public API (Wad, Lump, exceptions)
│   ├── wad.py           # Wad: read/write WAD headers, directory, lump bytes
│   ├── lump.py           # Lump: a single named chunk of raw data
│   ├── exceptions.py     # DoomWadError, InvalidWadError, LumpNotFoundError
│   ├── cli.py             # `doomwad` command-line tool
│   └── lumps/              # typed parsers for structured lump data
│       ├── __init__.py
│       └── maps.py          # THINGS/LINEDEFS/SIDEDEFS/VERTEXES/SECTORS
├── tests/
│   └── test_wad.py
└── pyproject.toml
```

## Install (editable, for development)

```bash
pip install -e ".[dev]"
```

## Usage

```python
from doomwad import Wad

wad = Wad.load("DOOM2.WAD")
print(len(wad.lumps), "lumps")

lump = wad.find("MAP01")
wad.replace("MAP01", b"...")
wad.save("out.wad")
```

## CLI

```bash
doomwad list mywad.wad
doomwad info mywad.wad
doomwad extract mywad.wad MAP01 -o map01.bin
```

## Tests

```bash
pytest
```
