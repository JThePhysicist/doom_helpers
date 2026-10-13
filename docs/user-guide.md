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

Pillow handles images; pytest is included by the development extra. The suite includes format, property-based, regression, subprocess, and packaging checks; run it to obtain the current test count. Tests generate their own WAD fixtures. Actual game assets are supplied by you. No API keys, database, or background services are needed. The installed `doomwad atlas` commands work outside the checkout. The original scripts remain compatibility wrappers.

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

This writes raw bytes, not a decoded image. The inspection CLI has four commands: `info`, `list`, `list-sprites`, and `extract`. Installed `atlas` subcommands and the Python API provide editing. Pass `--overwrite` to replace an existing raw extraction output.

## 3. Extract a sprite atlas

```bash
doomwad atlas extract \
  --wad assets/DOOM2.WAD --sprite TROO \
  --output-dir atlases/troo --atlas-size 1024 --padding 8
```

Expect `atlases/troo/TROO_0.png` (and numbered additional pages if needed) and `atlases/troo/TROO_manifest.json`. The script prints every output path. Each manifest entry records a patch name, page index, tile rectangle, and left/top anchor offsets; the manifest also embeds the RGB palette. A patch larger than the requested page causes an error. Duplicate patch names are rejected by default. Use `--duplicates first` or `--duplicates last` explicitly to choose a source occurrence. Malformed or mixed marker ranges are errors.

For sprites in a PWAD that has no PLAYPAL, explicitly supply a palette IWAD:

```bash
doomwad atlas extract \
  --wad assets/source-mod.wad --palette-wad assets/DOOM2.WAD \
  --sprite TROO --output-dir atlases/troo --padding 8
```

Choose one extraction command for your source. Both commands write the same output paths. Extraction refuses existing outputs; supply `--overwrite` only when intentionally replacing them. Multiple prefixes can share an atlas:

```bash
doomwad atlas extract \
  --wad assets/DOOM2.WAD --sprite TROO --sprite SARG \
  --output-dir atlases/monsters
```

That produces `TROO_SARG_manifest.json` and `TROO_SARG_0.png`, with further numbered pages as required. Defaults are 1024-pixel square pages and two pixels of packing padding. `--asset` is an alias for `--sprite`.

## 4. Edit the PNGs

Open the page PNGs in an image editor with RGBA transparency support. Keep their filenames, dimensions, and positions intact. Edit the pixels inside the intended tile; do not rearrange the page or move other sprites. Keep the manifest beside the pages. Make a backup of both before editing.

Transparent pixels represent empty space. Rebuild treats alpha below 128 as transparent and alpha at or above 128 as opaque. Colors are mapped to the nearest embedded palette color by squared RGB distance; antialiasing and arbitrary colors can change during conversion. Prefer that palette for predictable results.

Leave room between sprites. Each sprite has an immutable `allocation` editing rectangle. Shared gaps, including diagonal neighbors, are partitioned deterministically. Crop rectangles may change without shrinking that allocation. Keep artwork within the allocation shown by the preview; the full packing padding is not independently available to both neighbors. For bigger artwork, re-extract into a separate directory with more padding and transfer your edits there.

## 5. Preview and apply realignment

```bash
doomwad atlas realign \
  --manifest atlases/troo/TROO_manifest.json --dry-run
```

Review the reported old/new dimensions and positions and any warnings. No files are written during a dry run. Then save a separate adjusted manifest:

```bash
doomwad atlas realign \
  --manifest atlases/troo/TROO_manifest.json \
  --output atlases/troo/TROO_realigned.json
```

Realignment changes only the JSON rectangles and anchor offsets; it does not move or resize pixels. A positive crop shift decreases the corresponding anchor offset so the sprite's position relative to its anchor is preserved. Fully transparent tiles remain unchanged and emit a warning. A boundary warning requires visual inspection: it may signal clipping, including at a page edge.

Options: `--atlas-dir` overrides the page directory; `--margin N` limits the scan around the current crop, within the stable allocation; `--alpha-threshold N` changes the realignment mask. Keep the threshold at 128 to match rebuilding, whose threshold is not exposed as a script option. Omitting `--output` overwrites the input manifest. If placing an adjusted manifest elsewhere, provide `--atlas-dir` on later commands because relative page filenames resolve against the manifest's directory by default.

## 6. Rebuild into a new mod

```bash
doomwad atlas rebuild \
  --manifest atlases/troo/TROO_realigned.json \
  --output build/troo-mod.wad
```

This creates a PWAD containing the encoded patches and sprite markers. It does not copy the original IWAD, PLAYPAL, maps, or unrelated lumps. To update an existing mod while retaining its other lumps:

```bash
doomwad atlas rebuild \
  --manifest atlases/troo/TROO_realigned.json \
  --wad assets/source-mod.wad --output build/source-mod-edited.wad
```

Existing unique names are replaced; duplicate targets require explicit `--duplicates first` or `last`. Missing names are inserted before the last paired sprite end marker, or a marker range is created when none exists. Existing sprites outside marked ranges are rejected. Prefer unique sprite names and well-formed marker ranges. The existing WAD's IWAD/PWAD type is retained. Input and output can be the same file only with `--overwrite`, but a separate output preserves recovery options. Rebuilding refuses existing outputs by default. Individual replacements are staged and atomic; atlas batches roll back ordinary failures but are not crash-atomic transactions. Output parent directories must already exist.

The default `vanilla` profile supports patch heights up to 255 pixels. For compatible source ports, select `--profile source-port` during extraction; the manifest records that profile and rebuilding uses it. The extended codec supports relative post offsets and dimensions up to 32,767, subject to pixel budgets. Offsets are signed 16-bit values. Use extraction options `--palette-index N` for an alternate PLAYPAL palette and `--preserve-indices` to write grayscale `_indices.png` sidecars. Keep sidecars unchanged: rebuilding preserves original indices for unchanged RGB pixels and quantizes edited colors. Without sidecars duplicate RGB palette entries can change indices. WAD output is not generally byte-identical.

## 7. Verify and run in your target engine

```bash
doomwad info build/troo-mod.wad
doomwad list-sprites build/troo-mod.wad -v
doomwad list build/troo-mod.wad
```

Confirm the expected patch names appear inside the sprite markers. Inspect the rebuilt graphics by extracting them again with the same base palette:

```bash
doomwad atlas extract \
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

For standard binary Doom maps, use `Thing`, `Linedef`, `Sidedef`, `Vertex`, and `Sector` from `doomwad.lumps`. Each has `list_from_bytes` and `list_to_bytes`. Select the correct map's lump by directory position: `wad.find('THINGS')` alone always returns the first map's THINGS. Linedef back-sidedef `-1` represents no back side. Vertex/sidedef/sector references are unsigned; coordinates and texture offsets are signed. Hexen and UDMF map formats are unsupported. Use `DoomMap` for map-scoped record access and cross-reference validation:

```python
from doomwad.lumps import DoomMap
level = DoomMap(wad, 'MAP01')
things = level.records('THINGS')
things[0].x += 16
level.replace_records('THINGS', things)
level.save('build/map-edited.wad')
```

Geometry/sector edits mark this map object dirty, and `level.save()` rejects them until regeneration. `level.rebuild_nodes(['your-builder', '{wad}'])` runs your separately installed builder on a temporary WAD and imports its validated map records and derived lumps. The builder must update the temporary file in place and regenerate nodes, SEGS/SSECTORS, BLOCKMAP, and REJECT. Configure the argv for your specific tool. Actual node-builder compatibility is not established by the unit tests. Direct `Wad` manipulation bypasses the map object's dirty-state guard; use `DoomMap.save` for this workflow.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `doomwad` missing or Pillow import fails | Activate the correct environment and rerun the editable install. |
| No PLAYPAL | Supply `--palette-wad` with a compatible IWAD; inspect malformed palette data if one exists. |
| No matching sprites | Run `list-sprites -v`; use an exact uppercase prefix and inspect marker ranges. |
| Duplicate sprite names | Select `--duplicates first` or `last`, or resolve duplicates in the source archive. |
| Sprite exceeds atlas size | Increase `--atlas-size`. |
| Patch height exceeds 255 | Reduce artwork height for vanilla, or explicitly select the source-port profile for a compatible engine. |
| Realignment boundary warning | Inspect the tile; shrink the edit or allocate more space in a new extraction. |
| Missing PNG or incorrect crop | Restore the original page names/layout and matching manifest; use `--atlas-dir` when needed. |
| Invalid WAD or truncated patch | Verify the input archive; the reader raises format errors for these cases. |
| Output cannot be written | Create its parent directory and check filesystem permissions. |
| Looks wrong in-game | Check palette, anchor offsets, frame names, sprite range, engine compatibility, and mod load order. |

Stable allocation rectangles survive repeated realignment. Keep a backup of the original manifest and pages anyway. Older version-1 manifests acquire allocations on first realignment; save the updated manifest to retain them.

## Preview artwork, anchors, and changes

```bash
doomwad atlas preview --manifest atlases/troo/TROO_realigned.json \
  --output build/troo-preview.html
```

Open the HTML file in a browser. It embeds all images, palette swatches, crop and
allocation bounds, and anchor overlays; there is no service or network dependency.
It changes no input files. Supply `--baseline path/to/original_manifest.json` to
compare matching sprites with a saved baseline atlas. Keep original PNGs beside
that baseline manifest; a JSON copy referencing edited PNGs is not a baseline.
Use `--overwrite` to replace a previous preview.

## Resource limits and repeatable development

Extraction defaults to a total budget of 64,000,000 decoded/atlas pixels; use
`--max-pixels N` to select another positive budget. Individual patch decoding is
limited to 4,194,304 pixels. The WAD reader defaults to 512 MiB and one million
lumps. Library callers can configure limits; see [memory measurements and lazy
reading](performance.md) for large read-only archives.

For locked dependencies, install uv and run `uv sync --locked --extra dev`, then
`uv run python -m pytest -q --cov=doomwad --cov-branch --cov-fail-under=80`.
[Release checks](releases.md) include clean wheel validation. The optional
[engine fixture](../fixtures/README.md) verifies a 105-tic Chocolate Doom run with
an independently supplied compatible IWAD.

Runtime failures print concise diagnostics and return status 1; argparse usage
errors return status 2. Use `doomwad --debug ...` or an atlas command's `--debug`
for full tracebacks when troubleshooting. No publishing action is performed by
these commands.
