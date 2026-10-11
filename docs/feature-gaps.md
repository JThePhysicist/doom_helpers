# Feature gaps and improvement opportunities

This backlog describes the implementation after the seven bug fixes in commit `3c7c6d7`. These are proposed improvements, not implemented promises. The current supported workflow is documented in [the user guide](user-guide.md); its structure is shown in [the architecture](architecture.html).

## Highest-value follow-up work

| Opportunity | Current behavior and user impact | Suggested next step and acceptance evidence |
| --- | --- | --- |
| Validate manifests before processing | JSON is loaded without validating version, required keys, unique names, palette channels, page indices, or rectangle bounds. Pillow can silently pad crops outside page bounds. | Add a versioned schema validator used by all scripts; malformed manifests must produce actionable errors before any output is written. |
| Allocate stable editing regions | Realignment derives search limits from current rectangles. Midpoint clipping addresses neighboring rows/columns, but does not establish permanent ownership of every padding pixel or diagonal spillover. Repeated runs use already-adjusted bounds. | Store immutable allocation rectangles separately from crop bounds; test diagonal neighbors, repeated edits, page edges, and order independence. |
| Make writes recoverable | WADs, PNGs, and JSON are written directly. Interruptions or disk exhaustion can leave partial files; re-extraction overwrites matching output names. | Use staged files and atomic replacement where supported; make overwrite behavior explicit and test interrupted writes. |
| Harden binary input validation | Negative WAD fields and truncated posts are now rejected, but column offsets pointing into headers and oversized decoded-image allocations need stronger validation. Some malformed input can consume substantial memory. | Check patch column locations and configurable resource limits; add property-based/fuzz tests for counts, offsets, posts, and dimensions. |
| Define duplicate and marker policy | Raw lookup/replacement uses the first matching name; atlas extraction rejects duplicate names. Sprite discovery accepts marker starts/ends as a stream; rebuilding chooses the last end marker. Unmatched/reversed markers and existing sprites outside ranges are ambiguous. | Add archive validation and explicit duplicate resolution; regression-test unmatched, mixed, nested, repeated, and reversed marker sequences. |

## Workflow and format improvements

- **Unified commands:** Atlas workflows are repository scripts, while the installed CLI only exposes inspection and raw extraction. Add `atlas extract`, `atlas realign`, and `atlas rebuild` commands with shared argument validation and consistent error messages. Verify installed-wheel use outside the checkout.
- **Palette controls:** Extraction uses palette zero and rebuilding quantizes by squared RGB distance. Duplicate RGB entries can lose their original indices. Add palette selection and an optional index-preserving representation; test alternate palettes and duplicate-color round trips.
- **Tall patches and engine targets:** Encoding is limited to 255-pixel height. The decoder assumes absolute post offsets and does not implement source-port relative topdelta extensions. Declare supported engine/format profiles and add tall-patch fixtures before advertising extended support.
- **Better edit previews:** There is no built-in graphical preview, anchor overlay, palette browser, or visual diff. A read-only preview tool could show tile allocation, mirrored frame uses, opaque bounds, and anchor positions before rebuilding.
- **Packing options:** Shelf packing is simple and predictable but can waste space. Validate positive page sizes and nonnegative padding, then consider alternate packing strategies and explicit user-defined tile allocations. Preserve reproducibility of page placement.
- **Map-aware editing:** Typed parsers cover five standard Doom lump types, without map-scoped lookup, reference validation, node generation, or BLOCKMAP/REJECT regeneration. Add a map abstraction first; test archives with multiple repeated map lump names. Treat Hexen and UDMF support as distinct format work.
- **Reliable engine integration:** Python tests do not establish that a PWAD works in every Doom engine. Introduce an optional legally distributable fixture and documented target-engine smoke tests; distinguish vanilla and source-port sprite replacement requirements.
- **Scale:** Whole archives, decoded patches, and atlas pages are held in memory. Profile large archives before adding lazy lump access, streaming, configurable memory budgets, or progress reporting.

## Developer experience and release work

- The project has no checked-in CI workflow, dependency lock, or Python-version matrix. Run tests and build/install checks on supported Python versions; preserve the advertised Python >=3.9 support.
- Add coverage reporting for CLI error cases, palettes, all map records, invalid names, packing parameters, missing pages, and malformed manifests. The current 30 tests include 11 new regression cases but are not comprehensive format validation.
- Test a built wheel from a clean environment, separate from the editable checkout. Repository scripts are currently not wheel entry points.
- Establish a release/versioning process and changelog. Define the manifest compatibility policy before changing its version or fields.
- `pyproject.toml` declares MIT licensing, but there is no repository LICENSE file. Confirm the intended license and add its complete text before distribution.
- Normalize CLI failures into concise diagnostics and nonzero statuses. Several filesystem, parsing, Pillow, and encoding errors currently escape as tracebacks; malformed PLAYPAL can be reported as if it were missing.

## Suggested delivery order

1. Manifest/argument validation, marker policy, atomic writes, and stable allocation bounds.
2. CI, clean wheel installation, broader malformed-input tests, and supported-Python checks.
3. Unified atlas CLI, palette controls, and visual inspection tools.
4. Explicit engine profiles, tall-patch formats, map-aware editing, and measured scalability work.

Choose priorities around actual modding workflows and target engines. This list distinguishes observed limitations from ideas requiring product decisions; it does not imply that all opportunities must ship together.
