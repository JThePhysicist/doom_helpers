import fs from 'node:fs/promises';
import path from 'node:path';
import { PNG } from 'pngjs';
import { buildCharacterWad } from './build_character_wad_v2.mjs';
import { finalizePersonalV2 } from './finalize_personal_v2.mjs';
const args = process.argv.slice(2);
if (args.length !== 5) {
  console.error('Usage: npm run build:personal-v2 -- GAME_DIR HEAD_SHEET FIREBALL_SHEET HUD_WAD NEW_OUTPUT_DIR');
  process.exitCode = 2;
} else {
  const [game, heads, fireballs, hud, output] = args.map(p => path.resolve(p));
  try {
    // Validate required files before creating an output directory. Never overwrite a prior build.
    for (const file of [path.join(game, 'doom.wad'), heads, fireballs, hud]) await fs.access(file);
    await fs.mkdir(path.dirname(output), {recursive: true});
    await fs.mkdir(output);
    await fs.copyFile(heads, path.join(output, 'personal-head-angles.png'));
    await fs.copyFile(fireballs, path.join(output, 'concerned-fireball-sheet.png'));
    await fs.copyFile(hud, path.join(output, 'hud-input.wad'));
    await buildCharacterWad(PNG, game, path.dirname(output), output);
    const result = await finalizePersonalV2(PNG, path.dirname(output), game, output);
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
