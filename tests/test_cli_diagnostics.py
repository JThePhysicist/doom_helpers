import subprocess
import sys
from pathlib import Path

from doomwad import Wad
from doomwad.cli import main


def test_missing_input_and_lump_have_clean_errors(tmp_path,capsys):
    assert main(['info',str(tmp_path/'missing.wad')])==1
    captured=capsys.readouterr();assert 'error:' in captured.err and 'Traceback' not in captured.err
    wad=Wad();wad.save(tmp_path/'empty.wad')
    assert main(['extract',str(tmp_path/'empty.wad'),'MISSING','-o',str(tmp_path/'out')])==1
    assert not (tmp_path/'out').exists()


def test_malformed_palette_is_not_reported_as_missing(tmp_path,capsys):
    wad=Wad();wad.add('PLAYPAL',b'x');wad.save(tmp_path/'bad.wad')
    assert main(['atlas','extract','--wad',str(tmp_path/'bad.wad'),'--sprite','TROO'])==1
    captured=capsys.readouterr()
    assert 'too small' in captured.err and 'No PLAYPAL' not in captured.err


def test_legacy_script_has_same_clean_failure(tmp_path):
    script=Path(__file__).parents[1]/'scripts/rebuild_sprite_atlas.py'
    result=subprocess.run([sys.executable,str(script),'--manifest',str(tmp_path/'missing.json'),'--output',str(tmp_path/'out.wad')],capture_output=True,text=True)
    assert result.returncode==1 and 'error:' in result.stderr and 'Traceback' not in result.stderr


def test_output_collision_requires_explicit_overwrite(tmp_path,capsys):
    wad=Wad();wad.add('ONE',b'new');wad.save(tmp_path/'source.wad')
    output=tmp_path/'one';output.write_bytes(b'old')
    args=['extract',str(tmp_path/'source.wad'),'ONE','-o',str(output)]
    assert main(args)==1 and output.read_bytes()==b'old'
    capsys.readouterr()
    assert main(args+['--overwrite'])==0 and output.read_bytes()==b'new'
