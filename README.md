# doomwad

A Python library and CLI for reading and editing Doom WAD files.

## Project layout

```
doom_helpers/
├── doomwad/               # library source
│   ├── __init__.py        # public API (Wad, Lump, Palette, exceptions, ...)
│   ├── wad.py               # Wad: read/write WAD headers, directory, lump bytes
│   ├── lump.py               # Lump: a single named chunk of raw data
│   ├── exceptions.py         # DoomWadError, InvalidWadError, LumpNotFoundError
│   ├── palette.py             # Palette: PLAYPAL decoding + nearest-color lookup
│   ├── sprites.py              # Doom picture (patch) format encode/decode
│   ├── atlas.py                 # sprite sheet packing + manifest read/write
│   ├── cli.py                    # `doomwad` command-line tool
│   └── lumps/                     # typed parsers for structured lump data
│       ├── __init__.py
│       └── maps.py                  # THINGS/LINEDEFS/SIDEDEFS/VERTEXES/SECTORS
├── scripts/
│   ├── extract_sprite_atlas.py     # WAD sprites -> PNG atlas page(s) + manifest
│   └── rebuild_sprite_atlas.py     # PNG atlas page(s) + manifest -> WAD sprites
├── tests/
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

## Sprite atlas scripts

`scripts/extract_sprite_atlas.py` pulls all frames/rotations for one or more
sprite prefixes (e.g. `TROO` for the imp) out of a WAD, decodes each Doom
picture-format lump into RGBA, and packs them onto 1024x1024 (configurable)
PNG pages using a shelf bin-packer -- as many sprites as fit go on one page,
and it automatically starts a new page once a page is full. A
`<asset>_manifest.json` file records exactly where every sprite landed (page,
x/y/width/height, the patch's left/top offsets, and the palette used), so
none of that has to be tracked by hand or encoded into the image itself.

```bash
# PWADs usually don't carry PLAYPAL, so point at the IWAD for the palette
python scripts/extract_sprite_atlas.py \
    --wad DOOM2.WAD --sprite TROO --output-dir atlases/troo

# pack several sprites' frames into the same atlas set
python scripts/extract_sprite_atlas.py \
    --wad DOOM2.WAD --sprite TROO --sprite SARG --output-dir atlases/monsters
```

`scripts/rebuild_sprite_atlas.py` is the companion: it reads the manifest,
crops each sprite's tile back out of its atlas page, re-encodes it as a Doom
picture-format lump with the manifest's embedded palette, and writes the
lumps into a PWAD (or updates an existing WAD's matching lumps in place).

```bash
python scripts/rebuild_sprite_atlas.py \
    --manifest atlases/troo/TROO_manifest.json --output mymod.wad

# update lumps in an existing pwad instead of starting a fresh one
python scripts/rebuild_sprite_atlas.py \
    --manifest atlases/troo/TROO_manifest.json --wad mymod.wad --output mymod.wad
```

Edit the atlas PNGs in any image editor between the two steps -- just keep
each sprite's pixels inside its tile bounds from the manifest. The Doom
picture format only supports up to 255px tall images (single-byte post
offsets), which `encode_patch` enforces.

## Tests

```bash
pytest
```
