# Release and compatibility policy

Releases use `MAJOR.MINOR.PATCH`. While the API is below 1.0, a minor version may
contain breaking API changes; patch versions fix behavior without intentionally
changing public contracts. Publish a migration note for changed defaults or files.

Package versions are stored in `pyproject.toml` and `doomwad/__init__.py`. Check or
prepare a version with:

```bash
python tools/prepare_release.py --check
python tools/prepare_release.py 0.2.0 --dry-run
# Apply only when preparing that release:
python tools/prepare_release.py 0.2.0
uv lock
```

The script updates both version declarations. It does not commit, tag, push, or
publish. Move the Unreleased changelog entries into a dated release section,
review the migration notes, and run:

```bash
uv sync --locked --extra dev
uv run python -m pytest -q --cov=doomwad --cov-branch --cov-fail-under=80
uv build
uv run python tools/check_wheel.py --wheel dist/doomwad-0.2.0-py3-none-any.whl
```

Run the CI Python matrix, review the built wheel/sdist and included license, and
perform the optional engine smoke on the advertised targets. Merge the reviewed
release changes, then create and push a matching annotated tag (`v0.2.0` in this
example). Package-registry upload and release creation are explicit maintainer
steps; no publishing token is requested or embedded in this repository.

## Atlas manifest version 1

The implementation writes version 1 and rejects unsupported version numbers.
Required fields are version, atlas_size, padding, palette, pages, and sprites.
Page paths are relative without traversal; sprite names are unique; crop bounds
must be on-page. Allocation bounds, if present, must contain their crops and not
overlap other allocations on that page. Runtime validation supplements the
structural [JSON schema](manifest.schema.json) with these geometric checks.

Version 1 now has additive optional fields:

- `allocation: [x,y,width,height]` per sprite: immutable editing bounds. Legacy
  manifests receive these bounds on first realignment; save the resulting JSON.
- `index_pages`: grayscale PNG filenames parallel to `pages`. Preserve these
  files unchanged to retain original palette indices.
- `patch_profile`: `vanilla` (default) or `source-port` relative-post encoding.

Unknown optional fields are retained by manifest loading/saving. A future change
to required semantics or incompatible representation must increment the manifest
version and provide an explicit migration path. Older implementations may ignore
these optional fields and thus lose their benefits; use the current tools for
stable regions, index preservation, and tall patches.

## Migration from original scripts

Existing script entry points remain wrappers. Prefer `doomwad atlas extract`,
`realign`, `rebuild`, and `preview`. Extraction and rebuilding now refuse existing
output files unless `--overwrite` is supplied. Realignment still overwrites its
input manifest unless `--output` or `--dry-run` is used. Malformed markers are
errors; choose `--duplicates first` or `last` deliberately when resolving repeated
sprite names. Vanilla remains the default patch profile.
