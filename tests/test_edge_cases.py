import pytest
from PIL import Image

from doomwad import Wad, Lump, Palette, DoomWadError
from doomwad.atlas import load_atlas_pages, load_manifest
from doomwad.cli import main
from doomwad.lumps import Thing, Linedef, Sidedef, Vertex, Sector


@pytest.mark.parametrize('cls,record',[
    (Thing,Thing(-32768,32767,180,65535,32768)),
    (Linedef,Linedef(65534,0,32768,65535,65535,65534,-1)),
    (Sidedef,Sidedef(-32768,32767,'UPPER','LOWER','MIDDLE',65535)),
    (Vertex,Vertex(-32768,32767)),
    (Sector,Sector(-32768,32767,'FLOOR','CEIL',255,65535,65535))])
def test_all_map_record_boundaries_round_trip(cls,record):
    assert cls.list_from_bytes(cls.list_to_bytes([record]))==[record]


@pytest.mark.parametrize('name',['','é','TOOLONGNAME','BAD\0'])
def test_invalid_archive_names(name):
    wad=Wad();wad.lumps.append(Lump(name,b''))
    with pytest.raises(DoomWadError): wad.validate()


def test_palette_validation_and_nearest_cache():
    with pytest.raises(DoomWadError): Palette.from_playpal_bytes(bytes(768),-1)
    with pytest.raises(ValueError): Palette([(300,0,0)]*256)
    palette=Palette([(i,i,i) for i in range(256)])
    assert palette.nearest_index((100,101,102))==101
    assert palette.nearest_index((100,101,102))==101


def test_missing_pages_and_malformed_json(tmp_path,manifest):
    with pytest.raises(DoomWadError,match='missing'): load_atlas_pages(manifest,tmp_path)
    path=tmp_path/'bad.json';path.write_text('{')
    with pytest.raises(DoomWadError,match='JSON'): load_manifest(path)


def test_inspection_cli_output(tmp_path,capsys):
    wad=Wad();wad.add('ONE',b'test');path=tmp_path/'w.wad';wad.save(path)
    assert main(['info',str(path)])==0
    assert 'Lumps: 1' in capsys.readouterr().out
    assert main(['list',str(path)])==0
    assert 'ONE' in capsys.readouterr().out
    assert main(['extract',str(path),'ONE','-o',str(tmp_path/'one.bin')])==0
    assert (tmp_path/'one.bin').read_bytes()==b'test'
