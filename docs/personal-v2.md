# Personal character, HUD, and fireball builder

The original V2 output was confirmed working by its owner in the GOG DOOM + DOOM II rerelease on 2026-10-12. This is a local asset pipeline, not a distributable game mod: supply your own licensed game data and personal artwork. Nothing in this repository includes those assets.

Install Node.js and run npm ci, then:

```powershell
npm run build:personal-v2 -- "PATH/TO/GAME" "heads.png" "fireballs.png" "faces.wad" "outputs/new-build"
```

Inputs, in order:

- Game directory containing the tested Ultimate Doom doom.wad. The generated Windows launcher expects doom_gog.exe there.
- Transparent eight-head sheet: equal 4-by-2 grid. Top row: front, left three-quarter, left profile, left rear three-quarter. Bottom row: back, front pain, left hurt, front dead. Include short necks below intact heads.
- Transparent four-fireball sheet: equal 2-by-2 grid. Top row: two flight frames. Bottom row: initial impact and dissipating impact.
- HUD WAD containing the 42 original STF* face replacement names and dimensions.
- A new output directory; missing parent directories are created. Existing directories are rejected to preserve earlier builds.

Launch only PERSONAL_DOOM_V2.wad using the generated Play Personal Doom V2.cmd. EVERYONE_IS_YOU.wad is an intermediate patch collection, not the final game-compatible output.

The builder connects neck artwork to retained collars on PLAY, POSS, SPOS, and TROO frames; later destroyed-head gore remains original. All original sprites are retained in the final namespace, with HUD patches outside it. This full namespace was necessary for the tested rerelease; earlier sparse builds crashed. BAL1, BAL2, and BAL7 fireballs receive the supplied flaming-face animation. Flying projectiles are rendered at 28 by 30 pixels for readability; gameplay definitions, damage, and collision are unchanged.

The pipeline validates saved patch decoding, original character headers, body pixels outside edited regions, exact fireball pixel round-trips, complete sprite count, unique names, and unrelated sprite bytes. Reports and previews accompany each build. New artwork or different IWADs still need their own game tests. The standalone Node workflow does not change Python atlas manifest formats or defaults.

Generated WADs include graphics from your purchased game; keep those outputs local. Photos, sheets, WADs, archives, and outputs are ignored by Git.
