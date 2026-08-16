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
├── hudface/                # headshot -> Doom HUD face sprite pipeline (see below)
├── docker/                  # Dockerfile + docker-compose.yml for hudface
├── scripts/
│   ├── extract_sprite_atlas.py     # WAD sprites -> PNG atlas page(s) + manifest
│   ├── realign_sprite_atlas.py     # re-fit tiles to hand-edited art + fix offsets
│   ├── rebuild_sprite_atlas.py     # PNG atlas page(s) + manifest -> WAD sprites
│   └── check_complexity.sh         # xenon/radon complexity gate for hudface
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

Edit the atlas PNGs in any image editor. Edits don't need to land
pixel-perfect inside the original tile -- that's what the next step is for.

`scripts/realign_sprite_atlas.py` re-scans each sprite's tile (plus a small
margin, so art drawn right up to the original edge isn't missed), trims to
the actual opaque pixels the artist left behind, and shifts the patch's
left/top offsets by the same amount so the sprite still lines up on the same
in-game anchor point. It never moves or resizes pixels on the atlas page --
only the manifest's bookkeeping (`x`/`y`/`width`/`height`/offsets) is
updated. Run it before rebuilding:

```bash
python scripts/realign_sprite_atlas.py --manifest atlases/troo/TROO_manifest.json

# preview what would change without writing the manifest
python scripts/realign_sprite_atlas.py --manifest atlases/troo/TROO_manifest.json --dry-run
```

If a sprite's redrawn content touches the edge of the scanned margin, the
script prints a warning -- that usually means the edit spilled past its
allotted tile (drew larger than the original) and needs a bigger tile
(re-extract with more `--padding`) or a smaller redraw; realignment can only
recover content within the tile's reserved space, not content painted over a
neighboring sprite's tile.

`scripts/rebuild_sprite_atlas.py` is the last step: it reads the manifest,
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

The full pipeline: `extract_sprite_atlas.py` -> hand-edit the PNGs ->
`realign_sprite_atlas.py` -> `rebuild_sprite_atlas.py`. The Doom picture
format only supports up to 255px tall images (single-byte post offsets),
which `encode_patch` enforces.

## hudface: headshot -> Doom HUD face sprite pipeline

`hudface/` is a separate, tokenless (no LLM/agentic routing) DAG pipeline
that turns a user's headshot photo into a full set of Doom status-bar face
sprites (`STF*`), ready to import into SLADE3. It runs entirely locally on
an NVIDIA GPU (8GB+ VRAM) and does not call any external APIs.

```
hudface/
├── parser.py      # Phase 1: STF filename -> FaceState (expression, health tier, gaze)
├── geometry.py     # Phase 2: MediaPipe face validation + crop/align to FaceState
├── generator.py      # Phase 3: SD1.5 ControlNet + IP-Adapter style/damage transfer
├── quantizer.py         # Phase 4: resize, cyan-key background, PLAYPAL quantize
└── main.py                # Phase 5: plain sequential orchestrator (no dynamic routing)
```

It reuses `doomwad` for everything WAD/palette-related instead of
reimplementing it: `doomwad.Wad`/`doomwad.Palette.from_wad` load the IWAD's
PLAYPAL, `doomwad.decode_patch` decodes the original `STF*` sprites used as
Phase 3's style reference, and `doomwad.palette.Palette.nearest_index` is
the actual Euclidean-nearest-PLAYPAL-color mapping Phase 4 quantizes onto.

### Install

The core `doomwad`/`hudface.parser` install stays lightweight. The
GPU/ML stack (torch, diffusers, transformers, mediapipe, opencv, rembg) is
an optional extra so it's never required just to run the WAD tooling or the
fast unit tests:

```bash
pip install -e ".[dev]"              # tests, mypy, mutmut, radon/xenon
pip install -e ".[sprite-pipeline]"  # torch/diffusers/mediapipe/... (needs a CUDA GPU)
```

### Run

```bash
python -m hudface.main \
    --sources-dir photos/ \
    --targets targets.txt \
    --iwad DOOM.WAD \
    --output-dir output/
```

- `--sources-dir`: candidate headshot photos. For each target, Phase 2
  tries them in sorted order and uses the first one whose gaze/expression
  matches; a target with no matching photo is skipped (logged), not fatal.
- `--targets`: a text file listing target STF filenames, one per line
  (e.g. `STFST21.png`), blank lines and `#`-comments ignored.
- `--iwad`: a real Doom IWAD (`DOOM.WAD`/`DOOM2.WAD`), used for both the
  PLAYPAL and the original `STF*` sprites (IP-Adapter style references).

Or via Docker Compose (GPU passthrough via `nvidia-container-toolkit`):

```bash
cd docker && docker compose up --build
```

mounting `./sources`, `./targets` (including the IWAD and `targets.txt`),
and `./output` from the repo root.

### Quality gates

```bash
pytest                          # unit + pytest-bdd suites (no GPU/heavy deps needed)
mypy                             # strict type checking, scoped to hudface/
scripts/check_complexity.sh       # xenon/radon cyclomatic complexity gate (max grade B per function)
mutmut run                         # mutation testing on the Phase 4 palette-mapping logic
```

`pytest`, `mypy`, and the complexity gate all run without the
`sprite-pipeline` extra installed: Phase 3 (`generator.py`) and the actual
MediaPipe/torch calls in Phase 2/4 are the only parts that need a real GPU,
and every module defers those heavy imports to the functions that use them
so importing/testing the rest of the pipeline never requires them. The BDD
suite (`tests/features/stf_parsing.feature`) covers every real 1993 STF
face name (`ST`, `OUCH`, `EVL`, `KILL`, `GOD`, `DEAD`, `TL`, `TR`, all
health tiers, all gaze directions). `mutmut` is configured
(`[tool.mutmut]` in `pyproject.toml`) against `hudface/quantizer.py` and
`doomwad/palette.py`'s `Palette.nearest_index`.

## Tests

```bash
pytest
```
