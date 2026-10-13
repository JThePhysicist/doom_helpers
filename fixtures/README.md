# Optional engine fixture

`tools/engine_smoke.py` generates checkerboard sprite artwork and a 105-tic,
no-input Doom 1.9 demo. The authored artwork and demo are dedicated to the public
domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
No commercial IWAD data is checked in or redistributed.

Install Chocolate Doom separately, then use a compatible Doom II or Freedoom
Phase 2 IWAD you have available:

```bash
python tools/engine_smoke.py --iwad /path/to/freedoom2.wad --engine chocolate-doom
```

The test builds a PWAD replacing every source TROO frame, starts Chocolate Doom
with dummy video/audio drivers, and requires the exact timedemo completion record
for 105 game tics. Chocolate Doom 3.1 ends successful timedemos through `I_Error`,
which exits with status 255 on Linux; the harness accepts that status only with
the matching completion record. See upstream [g_game.c](https://github.com/chocolate-doom/chocolate-doom/blob/chocolate-doom-3.1.0/src/doom/g_game.c)
and [i_system.c](https://github.com/chocolate-doom/chocolate-doom/blob/chocolate-doom-3.1.0/src/i_system.c). Timeouts, engine errors, or a missing completion count fail the
check. This verifies loading and execution, not visual correctness. Inspect the
artwork and anchors interactively as described in the user guide.

This optional check is separate from pytest and requires an external engine and
IWAD. It passed in the cloud environment using Chocolate Doom 3.1.0 and Freedoom
Phase 2 0.13.0, installed in an isolated workspace from Debian
signature-verified package indexes and checksum-verified archives. A vanilla-compatible complete sprite set is used rather than assuming
that a subset replacement works in older engines. Source-port tall patches need
separate engine-specific visual tests; the codec unit tests do not establish
support in every engine.
