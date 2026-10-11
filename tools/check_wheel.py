"""Build and validate a wheel in an isolated environment outside the checkout."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

SMOKE = '''
from pathlib import Path
import subprocess, sys
from PIL import Image
from doomwad import Wad, Palette, encode_patch
import doomwad
root = Path.cwd()
assert not Path(doomwad.__file__).is_relative_to(Path(REPO)), doomwad.__file__
palette=Palette([(i,i,i) for i in range(256)])
wad=Wad();wad.add('PLAYPAL',bytes(c for color in palette.colors for c in color))
wad.add('S_START',b'');wad.add('TROOA1',encode_patch(Image.new('RGBA',(4,4),(42,42,42,255)),0,0,palette));wad.add('S_END',b'')
wad.save('source.wad')
cli=Path(sys.executable).parent/('doomwad.exe' if sys.platform=='win32' else 'doomwad')
def run(*args): subprocess.run([str(cli),*args],check=True)
run('atlas','extract','--wad','source.wad','--sprite','TROO','--output-dir','atlas','--preserve-indices')
run('atlas','realign','--manifest','atlas/TROO_manifest.json','--dry-run')
run('atlas','preview','--manifest','atlas/TROO_manifest.json','--output','preview.html')
run('atlas','rebuild','--manifest','atlas/TROO_manifest.json','--output','output.wad')
assert Wad.load('output.wad').find('TROOA1').data==wad.find('TROOA1').data
assert Path('preview.html').exists()
print('Clean wheel smoke passed:', doomwad.__file__)
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',help='Validate an existing wheel instead of building')
    args=parser.parse_args();repo=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as directory:
        work=Path(directory)
        if args.wheel: wheel=Path(args.wheel).resolve()
        else:
            subprocess.run([sys.executable,'-m','build','--wheel','--outdir',str(work/'dist')],cwd=repo,check=True)
            wheel=next((work/'dist').glob('*.whl'))
        venv.EnvBuilder(with_pip=True).create(work/'venv')
        python=work/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env=dict(os.environ);env.pop('PYTHONPATH',None)
        subprocess.run([str(python),'-m','pip','install',str(wheel)],cwd=work,env=env,check=True)
        subprocess.run([str(python),'-c',f'REPO={str(repo)!r}\n'+SMOKE],cwd=work,env=env,check=True)


if __name__=='__main__': main()
