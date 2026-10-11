# doomwad user guide

`doomwad` inspects and edits Doom WAD archives and converts sprite patches to editable PNG atlases and back. It is a Python library, a small inspection CLI, and three repository scripts. There is no graphical editor or hosted service.

See [the C4 architecture](architecture.html) for the design and [feature gaps](feature-gaps.md) for current limitations.

## 1. Install and verify

Use Python 3.9 or newer. These commands assume Bash on Linux or macOS and run from the repository root:

```bash
git clone --branch claude/doom-wad-editor-module-ky7og6 https://github.com/JThePhysicist/doom_helpers.git
cd doom_helpers
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pip check
python -m pytest -q
doomwad --help
```

For an existing checkout, skip cloning and enter that checkout. On Windows PowerShell, create the environment with `py -m venv .venv` and activate it with `.\.venv\Scripts\Activate.ps1`; use the same Python commands afterward. The cloud environment already has an editable installation: `cd /workspace/doom_helpers` and `source /workspace/venvs/doom_helpers/bin/activate`.

Pillow handles images; pytest is included by the development extra. The suite currently has 30 passing test cases, including subprocess atlas pipelines. Tests generate their own WAD fixtures. Actual game assets are supplied by you. No API keys, database, or background services are needed. Run the atlas scripts from the checkout; they are not installed as console commands.

## 2. Prepare inputs and inspect a WAD

Keep originals unchanged and write results to a different path. In the examples below, place your IWAD at `assets/DOOM2.WAD`. An IWAD is the base game archive; a PWAD is an add-on archive. Create working directories:

```bash
mkdir -p assets atlases build
# Copy your own DOOM2.WAD into assets/ before continuing.
doomwad info assets/DOOM2.WAD
doomwad list assets/DOOM2.WAD
doomwad list-sprites assets/DOOM2.WAD -v
```

`info` prints archive type and lump count; `list` prints directory indices, names, and byte sizes. `list-sprites -v` groups sprite names by their four-character prefix and lists frames. Use an exact uppercase prefix from that output. `TROO` is used below as an example. Sprite names such as `TROOA2A8` encode two frame/rotation uses of a single patch; preserve the name when editing.

To extract any raw lump:

```bash
doomwad extract assets/DOOM2.WAD PLAYPAL -o build/playpal.bin
```

This writes raw bytes, not a decoded image. The inspection CLI has four commands: `info`, `list`, `list-sprites`, and `extract`. Editing is done through the scripts or Python API.

## 3. Extract a sprite atlas

```bash
python scripts/extract_sprite_atlas.py \
  --wad assets/DOOM2.WAD --sprite TROO \
  --output-dir atlases/troo --atlas-size 1024 --padding 8
```

Expect `atlases/troo/TROO_0.png` (and numbered additional pages if needed) and `atlases/troo/TROO_manifest.json`. The script prints every output path. Each manifest entry records a patch name, page index, tile rectangle, and left/top anchor offsets; the manifest also embeds the RGB palette. A patch larger than the requested page causes an error. Duplicate patch names are rejected rather than silently choosing artwork.

For sprites in a PWAD that has no PLAYPAL, explicitly supply a palette IWAD:

```bash
python scripts/extract_sprite_atlas.py \
  --wad assets/source-mod.wad --palette-wad assets/DOOM2.WAD \
  --sprite TROO --output-dir atlases/troo --padding 8
```

Choose one extraction command for your source. Both commands write the same output paths, so rerunning them replaces your atlas files. Multiple prefixes can share an atlas:

```bash
python scripts/extract_sprite_atlas.py \
  --wad assets/DOOM2.WAD --sprite TROO --sprite SARG \
  --output-dir atlases/monsters
```

That produces `TROO_SARG_manifest.json` and `TROO_SARG_0.png`, with further numbered pages as required. Defaults are 1024-pixel square pages and two pixels of packing padding. `--asset` is an alias for `--sprite`.

## 4. Edit the PNGs

Open the page PNGs in an image editor with RGBA transparency support. Keep their filenames, dimensions, and positions intact. Edit the pixels inside the intended tile; do not rearrange the page or move other sprites. Keep the manifest beside the pages. Make a backup of both before editing.

Transparent pixels represent empty space. Rebuild treats alpha below 128 as transparent and alpha at or above 128 as opaque. Colors are mapped to the nearest embedded palette color by squared RGB distance; antialiasing and arbitrary colors can change during conversion. Prefer that palette for predictable results.

Leave room between sprites. Realignment searches near the original rectangle but divides shared gaps between adjacent tiles at their midpoint. The full packing padding is not independently available to both neighbors. Large or diagonal spillover can still be ambiguous; keep artwork within its own space. For bigger artwork, re-extract into a separate directory with more padding and transfer your edits there.

## 5. Preview and apply realignment

```bash
python scripts/realign_sprite_atlas.py \
  --manifest atlases/troo/TROO_manifest.json --dry-run
```

Review the reported old/new dimensions and positions and any warnings. No files are written during a dry run. Then save a separate adjusted manifest:

```bash
python scripts/realign_sprite_atlas.py \
  --manifest atlases/troo/TROO_manifest.json \
  --output atlases/troo/TROO_realigned.json
```

Realignment changes only the JSON rectangles and anchor offsets; it does not move or resize pixels. A positive crop shift decreases the corresponding anchor offset so the sprite's position relative to its anchor is preserved. Fully transparent tiles remain unchanged and emit a warning. A boundary warning requires visual inspection: it may signal clipping, including at a page edge.

Options: `--atlas-dir` overrides the page directory; `--margin N` overrides the initial search margin; `--alpha-threshold N` changes the realignment mask. Keep the threshold at 128 to match rebuilding, whose threshold is not exposed as a script option. Omitting `--output` overwrites the input manifest. If placing an adjusted manifest elsewhere, provide `--atlas-dir` on later commands because relative page filenames resolve against the manifest's directory by default.

## 6. Rebuild into a new mod

```bash
python scripts/rebuild_sprite_atlas.py \
  --manifest atlases/troo/TROO_realigned.json \
  --output build/troo-mod.wad
```

This creates a PWAD containing the encoded patches and sprite markers. It does not copy the original IWAD, PLAYPAL, maps, or unrelated lumps. To update an existing mod while retaining its other lumps:

```bash
python scripts/rebuild_sprite_atlas.py \
  --manifest atlases/troo/TROO_realigned.json \
  --wad assets/source-mod.wad --output build/source-mod-edited.wad
```

Existing names are replaced at their first occurrence. Missing names are inserted before the last sprite end marker, or a marker range is created when none exists. Prefer unique sprite names and well-formed marker ranges. The existing WAD's IWAD/PWAD type is retained. Input and output can technically be the same file, but a separate output preserves recovery options. Output parent directories must already exist.

The encoder currently supports patch heights up to 255 pixels; taller crops fail. Offsets are signed 16-bit values. Rebuilding can change palette indices where multiple palette colors have the same RGB value, and does not promise byte-identical WAD output.

## 7. Verify and run in your target engine

```bash
doomwad info build/troo-mod.wad
doomwad list-sprites build/troo-mod.wad -v
doomwad list build/troo-mod.wad
```

Confirm the expected patch names appear inside the sprite markers. Inspect the rebuilt graphics by extracting them again with the same base palette:

```bash
python scripts/extract_sprite_atlas.py \
  --wad build/troo-mod.wad --palette-wad assets/DOOM2.WAD \
  --sprite TROO --output-dir build/recheck
```

Open `build/recheck/TROO_0.png` and compare it with your edits. For a source port you have separately installed, a typical command is:

```bash
gzdoom -iwad assets/DOOM2.WAD -file build/troo-mod.wad
```

GZDoom is not included or required by this package; this command is an example for that external engine. Check all relevant frames, rotations, mirrored views, palette colors, and anchor alignment in-game. Engine behavior and load-order compatibility are not verified by the Python tests. Some older engines impose additional sprite replacement requirements.

## Python library workflows

Read and manipulate raw lumps:

```python
from doomwad import Wad

wad = Wad.load('assets/DOOM2.WAD')
print(wad.wad_type, len(wad))
print(wad.find('PLAYPAL').size)
mod = Wad('PWAD')
mod.add('MYDATA', b'hello')
mod.replace('MYDATA', b'updated')
mod.save('build/data-mod.wad')
```

`find`, `index_of`, `replace`, and `remove` operate on the first matching name; `find_all` returns every match. `insert(index, name, data)` inserts at a directory position. Names are truncated to eight characters when added/inserted; serialization requires ASCII. Load reads the whole file into memory. `Wad.to_bytes()` and `Wad.from_bytes()` support in-memory workflows.

Decode and encode a patch:

```python
from doomwad import Palette, decode_patch, encode_patch

palette = Palette.from_wad(wad)  # PLAYPAL palette zero by default
patch = decode_patch('TROOA1', wad.find('TROOA1').data, palette)
patch.image.save('build/frame.png')
encoded = encode_patch(patch.image, patch.left_offset, patch.top_offset, palette)
```

For standard binary Doom maps, use `Thing`, `Linedef`, `Sidedef`, `Vertex`, and `Sector` from `doomwad.lumps`. Each has `list_from_bytes` and `list_to_bytes`. Select the correct map's lump by directory position: `wad.find('THINGS')` alone always returns the first map's THINGS. Linedef back-sidedef `-1` represents no back side. Vertex/sidedef/sector references are unsigned; coordinates and texture offsets are signed. Hexen and UDMF map formats are unsupported. These parsers do not rebuild nodes, validate cross-references, or update BLOCKMAP/REJECT; geometry editing requires external map tooling.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `doomwad` missing or Pillow import fails | Activate the correct environment and rerun the editable install. |
| No PLAYPAL | Supply `--palette-wad` with a compatible IWAD; inspect malformed palette data if one exists. |
| No matching sprites | Run `list-sprites -v`; use an exact uppercase prefix and inspect marker ranges. |
| Duplicate sprite names | Resolve duplicates in the source archive; extraction cannot represent separate same-name tiles. |
| Sprite exceeds atlas size | Increase `--atlas-size`. |
| Patch height exceeds 255 | Reduce artwork height; tall-patch encoding is not implemented. |
| Realignment boundary warning | Inspect the tile; shrink the edit or allocate more space in a new extraction. |
| Missing PNG or incorrect crop | Restore the original page names/layout and matching manifest; use `--atlas-dir` when needed. |
| Invalid WAD or truncated patch | Verify the input archive; the reader raises format errors for these cases. |
| Output cannot be written | Create its parent directory and check filesystem permissions. |
| Looks wrong in-game | Check palette, anchor offsets, frame names, sprite range, engine compatibility, and mod load order. |

Do not repeatedly realign changing artwork without retaining the original manifest: adjusted rectangles become the next search bounds. To recover, restore the backed-up manifest and pages or extract into a fresh directory.
