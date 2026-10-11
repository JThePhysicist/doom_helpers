# Remaining feature gaps and opportunities

The original 19-item backlog has been implemented as individual stacked branches.
[Implementation status](implementation-status.md) maps each item to its branch and
records validation. These remaining opportunities extend that delivered scope.

| Area | Delivered | Remaining opportunity |
| --- | --- | --- |
| Manifest validation | Versioned structure, bounds, palette, paths, allocations and sidecars | Explicit migration commands for a future incompatible manifest version |
| Editing regions | Immutable nonoverlapping allocation rectangles, including diagonal neighbors | A graphical tool to resize/repack regions instead of editing allocation JSON |
| Recoverable writes | Staged atomic file replacement, exclusive outputs, ordinary batch rollback | Crash-atomic multi-file publication, e.g. generation directories with a pointer |
| Input hardening | WAD, post and offset validation, byte/lump/pixel budgets, Hypothesis checks | Larger real-world corpus fuzzing and sanitizer-backed engine tests |
| Marker/duplicate policy | Strict paired markers and explicit first/last selection | Archive repair commands and broader engine-specific namespace conventions |
| Atlas CLI | Installed extract/realign/rebuild/preview commands, script wrappers | Interactive wizard or graphical editing interface |
| Palette controls | Alternate PLAYPAL palettes and unchanged-pixel index preservation | Optional perceptual quantization, dithering, and palette visualization workflows |
| Patch profiles | Vanilla and source-port relative topdelta codecs | Visual target-engine tests for tall sprites and more engine-specific profiles |
| Preview | Self-contained HTML, allocations, anchors, palette, and baseline pixel diffs | Editable overlays, rotation/frame animation, and anchor-aligned diffs for resized tiles |
| Packing | Parameter checks and reproducible shelf placement | Benchmark alternative packing before selecting one; allocation editing UI |
| Map-aware editing | Standard map scoping, reference validation, dirty guard, external builder hook | Real node-builder integration tests; separate Hexen/UDMF implementations |
| Engine integration | CC0 generated fixture and passing Chocolate Doom/Freedoom timedemo | Automated graphical validation and additional source-port integration |
| Scale | Measured indexed reader and configurable budgets | Streaming decode/atlas writes, cancellation and progress for very large jobs |
| CI and lock | Universal uv lock and Python 3.9–3.14 workflow | Observe remote CI on submitted PRs and add other operating systems |
| Coverage | Branch-inclusive reports, subprocess coverage and regression cases | Broader format corpora and testing uncommon error paths |
| Distribution | Clean wheel install and end-to-end smoke, license packaging | Release registry verification once a release is authorized |
| Release process | Coordinated versions, changelog, manifest policy and checklist | Execute an actual maintainer-reviewed release; no release was published here |
| Licensing | Declared MIT text and packaged metadata; generated fixture art is CC0 | Keep third-party asset attribution separate when adding real sample archives |
| Diagnostics | Concise failures, nonzero statuses and optional debug tracebacks | Structured JSON diagnostics for automated callers |

Visual game behavior and external node-builder compatibility need their own
integration evidence. The core is still a local tool; no hosted service, user
accounts, or collaborative editing backend is proposed by these changes.
