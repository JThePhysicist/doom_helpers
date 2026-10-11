"""Optional Chocolate Doom timedemo check using a user-supplied compatible IWAD.

The checkerboard patch art and no-input demo generated here are dedicated to
CC0 1.0. No commercial WAD assets are redistributed.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

from PIL import Image
from doomwad import Wad, Palette, encode_patch
from doomwad.sprites import find_sprite_lumps


def build_fixture(iwad, output):
    source=Wad.load(iwad);palette=Palette.from_wad(source)
    image=Image.new('RGBA',(16,16))
    for y in range(16):
        for x in range(16):
            image.putpixel((x,y),(*palette.rgb(0 if (x//4+y//4)%2 else 255),255))
    result=Wad();result.add('S_START',b'')
    # Vanilla sprite replacement needs all source frames for the selected entity.
    sprites=find_sprite_lumps(source,['TROO'])
    if not sprites: raise ValueError('IWAD has no TROO sprite frames')
    for lump in sprites: result.add(lump.name,encode_patch(image,8,16,palette))
    result.add('S_END',b'');result.save(output)


def run_smoke(engine,iwad,timeout=60):
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory);mod=path/'checker.wad';build_fixture(iwad,mod)
        demo=path/'smoke.lmp'
        demo.write_bytes(bytes([109,2,1,1,0,0,0,1,0,1,0,0,0])+bytes(4*105)+bytes([128]))
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
        result=subprocess.run([engine,'-iwad',str(Path(iwad).resolve()),'-file',str(mod),
                               '-timedemo',str(demo),'-nosound','-nodraw'],cwd=directory,
                              env=env,capture_output=True,text=True,timeout=timeout)
        output=result.stdout+'\n'+result.stderr
        if result.returncode or not re.search(r'105\s+gametics',output):
            raise RuntimeError(f'Engine did not complete the 105-tic demo (exit {result.returncode}):\n{output}')
        print('Chocolate Doom completed 105 gametics with the generated sprite PWAD')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',default='chocolate-doom')
    parser.add_argument('--iwad',required=True)
    parser.add_argument('--timeout',type=int,default=60)
    args=parser.parse_args()
    run_smoke(args.engine,args.iwad,args.timeout)
