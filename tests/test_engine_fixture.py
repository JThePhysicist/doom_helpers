import importlib.util
from pathlib import Path

from PIL import Image
from doomwad import Wad, Palette, encode_patch, decode_patch
from doomwad.sprites import find_sprite_lumps


def test_optional_engine_fixture_replaces_every_frame(tmp_path):
    spec=importlib.util.spec_from_file_location('engine_smoke',Path(__file__).parents[1]/'tools/engine_smoke.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    palette=Palette([(i,i,i) for i in range(256)]);source=Wad()
    source.add('PLAYPAL',bytes(c for color in palette.colors for c in color));source.add('S_START',b'')
    for name in ['TROOA1','TROOA2A8']: source.add(name,encode_patch(Image.new('RGBA',(4,4),(0,0,0,255)),0,0,palette))
    source.add('S_END',b'');source.save(tmp_path/'source.wad')
    module.build_fixture(tmp_path/'source.wad',tmp_path/'mod.wad')
    sprites=find_sprite_lumps(Wad.load(tmp_path/'mod.wad'),['TROO'])
    assert [l.name for l in sprites]==['TROOA1','TROOA2A8']
    assert all(decode_patch(l.name,l.data,palette).image.size==(16,16) for l in sprites)


import pytest


@pytest.mark.parametrize('status,message,passes',[
    (255,'timed 105 gametics in 0 realtics (inf fps)',True),
    (255,'WAD failed to load',False),(0,'No completion record',False),
    (255,'timed 104 gametics in 0 realtics',False)])
def test_engine_harness_distinguishes_timedemo_exit_from_failure(status,message,passes,monkeypatch):
    from types import SimpleNamespace
    spec=importlib.util.spec_from_file_location('engine_smoke',Path(__file__).parents[1]/'tools/engine_smoke.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'build_fixture',lambda *args:None)
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:SimpleNamespace(returncode=status,stdout=message,stderr=''))
    if passes: module.run_smoke('engine','source.wad')
    else:
        with pytest.raises(RuntimeError): module.run_smoke('engine','source.wad')
