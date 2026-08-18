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
│   ├── realign_sprite_atlas.py     # re-fit tiles to hand-edited art + fix offsets
│   └── rebuild_sprite_atlas.py     # PNG atlas page(s) + manifest -> WAD sprites
├── src/doomface/           # tokenless headshot -> Doom HUD sprite pipeline
│   ├── parser.py             # Phase 1: STF filename -> FaceState
│   ├── geometry.py             # Phase 2: MediaPipe gaze/expression validation + crop
│   ├── generator.py              # Phase 3: SD1.5 + ControlNet + IP-Adapter style transfer
│   ├── quantizer.py                # Phase 4: resize, cyan key, PLAYPAL quantization
│   └── main.py                       # Phase 5: tokenless DAG orchestrator (CLI)
├── tests/
├── Dockerfile
├── docker-compose.yml
├── Makefile
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

## Tests

```bash
pytest
```

## doomface: tokenless Doom HUD sprite style-transfer pipeline

`src/doomface/` converts headshot photos into 1993 Doom status-bar face
(`STF...`) sprites, quantized to a Doom `PLAYPAL`. It's a strict,
deterministic Directed Acyclic Graph -- a plain `argparse` orchestrator
calling five phases in order, no LLM/agentic routing:

1. **`doomface.parser`** -- parses `STF...` filenames into `FaceState`
   (expression, health tier, gaze direction), per the real 1993 naming
   convention from `st_stuff.c`.
2. **`doomface.geometry`** -- validates a source headshot's gaze/expression
   against a target `FaceState` via MediaPipe face landmarks, and crops it
   to the face (+20% margin). Raises on mismatch.
3. **`doomface.generator`** -- style-transfers the aligned crop toward the
   original Doom sprite's look via Stable Diffusion 1.5 + ControlNet
   (Canny, for structural lock) + an IP-Adapter, with a health-tier-driven
   damage prompt.
4. **`doomface.quantizer`** -- downscales to ~24x29px, keys the background
   to exact Doom cyan (`#00FFFF`), and maps every pixel to the nearest
   `PLAYPAL` color, reusing `doomwad.Palette.nearest_index` rather than
   reimplementing color-distance math. Saves a palette-indexed PNG under
   the original `STF...` filename, ready for SLADE3 import.
5. **`doomface.main`** -- iterates the target `STF` filename list (all 42
   standard faces by default), scanning the source headshot directory in a
   fixed order until phase 2 accepts one candidate per target, then runs
   it through phases 3-4.

Every phase's heavy dependency (MediaPipe, torch/diffusers) sits behind a
small `Protocol` (`FaceLandmarker`, `BackgroundSegmenter`,
`FaceStyleGenerator`) so the parsing, geometry math, and palette-mapping
logic are unit-testable without installing torch or a GPU; only the real
`MediaPipe*`/`DoomFaceGenerator` implementations need them, and those are
imported lazily.

### Install

```bash
pip install -e ".[doomface]"       # runtime: torch, diffusers, mediapipe, opencv, numpy
pip install -e ".[doomface-dev]"   # + pytest-bdd, mutmut, radon, xenon, mypy
```

MediaPipe's Tasks API needs two model bundles downloaded once and cached
locally (inference itself then stays fully local/offline):

- [`face_landmarker.task`](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task)
- [`selfie_segmenter.tflite`](https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite)

### CLI

```bash
doomface \
  --source-dir ./data/source \
  --playpal ./data/wad/DOOM2.WAD \
  --reference-wad ./data/wad/DOOM2.WAD \
  --face-model ./models/face_landmarker.task \
  --segmenter-model ./models/selfie_segmenter.tflite \
  --output-dir ./output
```

`--playpal` accepts either a `.wad` (palette read via `doomwad.Palette.from_wad`)
or a raw 768-byte `.pal` file. `--reference-wad` supplies the original Doom
sprites used as IP-Adapter style references. Omit `--target`/`--targets-file`
to generate all 42 standard faces; pass `--target STFOUCH2.png` (repeatable)
or `--targets-file names.txt` to generate a subset.

### Docker

```bash
docker compose run --rm doomface
```

Requires the NVIDIA Container Toolkit on the host (8GB+ VRAM). Place
headshots in `./data/source`, the IWAD in `./data/wad`, and the two
MediaPipe model bundles in `./models`; sprites land in `./output`.

### QA

```bash
make test         # pytest, including the Phase 1 pytest-bdd suite
make typecheck     # mypy --strict src/doomface
make complexity    # radon + xenon -b B -m A -a A
make mutmut        # mutation testing of the Phase 4 palette-mapping logic
make check         # all of the above
```
