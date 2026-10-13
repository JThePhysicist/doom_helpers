from pathlib import Path
import subprocess
import sys

from PIL import Image

from doomwad import Wad, Palette, encode_patch


def test_installed_cli_pipeline_outside_checkout(tmp_path):
    palette=Palette([(i,i,i) for i in range(256)])
    wad=Wad();wad.add('PLAYPAL',bytes(c for color in palette.colors for c in color))
    wad.add('S_START',b'');wad.add('TROOA1',encode_patch(Image.new('RGBA',(4,4),(10,10,10,255)),0,0,palette));wad.add('S_END',b'')
    source=tmp_path/'source.wad';wad.save(source)
    cli=Path(sys.executable).parent/'doomwad'
    def run(*args):
        result=subprocess.run([str(cli),*args],cwd=tmp_path,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    run('atlas','extract','--wad',str(source),'--sprite','TROO','--output-dir','atlas')
    run('atlas','realign','--manifest','atlas/TROO_manifest.json','--dry-run')
    run('atlas','rebuild','--manifest','atlas/TROO_manifest.json','--output','rebuilt.wad')
    assert 'TROOA1' in Wad.load(tmp_path/'rebuilt.wad')
