# Implementation and delivery status

Each of the 19 original backlog items has its own branch, based on the previous
branch. A final integration branch updates documentation, corrects integration
edge cases, and records complete-stack validation. Branches are pushed; PR creation
is currently blocked by GitHub API network access. The initial fixes/documentation
were already pushed to the repository default branch, so that PR also needs a
maintainer-selected target branch.

| Order | Improvement branch | Result |
| --- | --- | --- |
| 1 | [improve/01-manifest-validation](https://github.com/JThePhysicist/doom_helpers/tree/improve/01-manifest-validation) | Validate atlas manifests before processing files |
| 2 | [improve/02-stable-edit-regions](https://github.com/JThePhysicist/doom_helpers/tree/improve/02-stable-edit-regions) | Persist stable nonoverlapping sprite editing allocations |
| 3 | [improve/03-recoverable-writes](https://github.com/JThePhysicist/doom_helpers/tree/improve/03-recoverable-writes) | Make output writes recoverable and require explicit overwrite |
| 4 | [improve/04-binary-validation](https://github.com/JThePhysicist/doom_helpers/tree/improve/04-binary-validation) | Bound binary parsing and fuzz malformed WAD and patch inputs |
| 5 | [improve/05-marker-duplicate-policy](https://github.com/JThePhysicist/doom_helpers/tree/improve/05-marker-duplicate-policy) | Define strict sprite markers and explicit duplicate selection |
| 6 | [improve/06-unified-atlas-cli](https://github.com/JThePhysicist/doom_helpers/tree/improve/06-unified-atlas-cli) | Expose installed atlas extract, realign, and rebuild commands |
| 7 | [improve/07-palette-controls](https://github.com/JThePhysicist/doom_helpers/tree/improve/07-palette-controls) | Select PLAYPAL palettes and optionally preserve source color indices |
| 8 | [improve/08-tall-patch-profiles](https://github.com/JThePhysicist/doom_helpers/tree/improve/08-tall-patch-profiles) | Add explicit vanilla and source-port tall patch profiles |
| 9 | [improve/09-edit-preview](https://github.com/JThePhysicist/doom_helpers/tree/improve/09-edit-preview) | Add self-contained read-only atlas previews and visual diffs |
| 10 | [improve/10-packing-options](https://github.com/JThePhysicist/doom_helpers/tree/improve/10-packing-options) | Validate packing parameters and make placement order reproducible |
| 11 | [improve/11-map-aware-editing](https://github.com/JThePhysicist/doom_helpers/tree/improve/11-map-aware-editing) | Add map-scoped editing, reference validation, and node-builder hooks |
| 12 | [improve/12-engine-smoke-workflow](https://github.com/JThePhysicist/doom_helpers/tree/improve/12-engine-smoke-workflow) | Add an optional engine timedemo and distributable generated sprite fixture |
| 13 | [improve/13-lazy-archive-scale](https://github.com/JThePhysicist/doom_helpers/tree/improve/13-lazy-archive-scale) | Profile archive memory and add indexed read-only lump access |
| 14 | [improve/14-ci-and-dependency-lock](https://github.com/JThePhysicist/doom_helpers/tree/improve/14-ci-and-dependency-lock) | Add locked dependencies and supported-Python CI builds |
| 15 | [improve/15-coverage-and-edge-cases](https://github.com/JThePhysicist/doom_helpers/tree/improve/15-coverage-and-edge-cases) | Report coverage and exercise map, palette, archive, and CLI edge cases |
| 16 | [improve/16-clean-wheel-verification](https://github.com/JThePhysicist/doom_helpers/tree/improve/16-clean-wheel-verification) | Verify built wheels with an isolated end-to-end CLI smoke test |
| 17 | [improve/17-release-and-manifest-policy](https://github.com/JThePhysicist/doom_helpers/tree/improve/17-release-and-manifest-policy) | Define releases, coordinated versioning, and manifest compatibility |
| 18 | [improve/18-mit-license](https://github.com/JThePhysicist/doom_helpers/tree/improve/18-mit-license) | Include the declared MIT license in source and built distributions |
| 19 | [improve/19-cli-diagnostics](https://github.com/JThePhysicist/doom_helpers/tree/improve/19-cli-diagnostics) | Normalize CLI errors and make raw extraction overwrite explicit |
| 20 | [improve/20-integration-docs](https://github.com/JThePhysicist/doom_helpers/tree/improve/20-integration-docs) | Integrate docs, pixel budgets, node-builder vertex imports, and real-engine validation |

## Validation evidence

- All 106 tests pass locally on Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14.
  Python 3.12 branch-inclusive coverage is 90.36%, above the 80% CI gate.
  Locked installs and the CI workflow cover that supported range.
- A clean built wheel runs the atlas pipeline and preview outside the checkout,
  with imports verified from site-packages rather than source.
- Chocolate Doom 3.1.0 + Freedoom Phase 2 0.13.0 loaded the generated mod and
  completed 105 game tics. The timedemo's documented exit status 255 is accepted
  only with the exact completion message. Visual correctness remains a manual check.
- [Memory profiling](performance.md) compared 10,000 1-KiB lumps: indexed reads
  used about 2.08 MiB peak Python allocations vs 31.23 MiB for eager reads.
- The wheel and source distribution contain LICENSE and declare MIT metadata.
- No package release, publishing token, or Git tag was created. No new branch
  has been merged into the default branch; review the stack in order.

## Defined scope and remaining dependencies

Map editing implements a standard Doom map abstraction and an explicit external
node-builder hook. It does not implement Hexen/UDMF or an internal node generator.
Node-builder transfer and failure behavior are unit tested, but compatibility with
an actual node builder is not yet established. Packing keeps deterministic shelves;
alternate algorithms remain a measured future option. The preview is read-only,
and indexed reads do not make the entire atlas pipeline streaming.

See [feature gaps](feature-gaps.md) for the remaining opportunities and
[release policy](releases.md) for migration and publication steps.
