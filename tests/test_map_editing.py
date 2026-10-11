import pytest
from doomwad import Wad, DoomWadError
from doomwad.lumps import DoomMap, Thing, Linedef, Sidedef, Vertex, Sector


def fixture():
    wad=Wad()
    for name in ['MAP01','MAP02']:
        wad.add(name,b'')
        for lump,cls,records in [
            ('THINGS',Thing,[Thing(0,0,0,1,7)]),('VERTEXES',Vertex,[Vertex(0,0),Vertex(10,0)]),
            ('LINEDEFS',Linedef,[Linedef(0,1,0,0,0,0,-1)]),
            ('SIDEDEFS',Sidedef,[Sidedef(0,0,'-','-','STONE',0)]),
            ('SECTORS',Sector,[Sector(0,128,'FLOOR','CEIL',160,0,0)])]:
            wad.add(lump,cls.list_to_bytes(records))
        for lump in ['SEGS','SSECTORS','NODES','BLOCKMAP','REJECT']: wad.add(lump,b'')
    return wad


def test_map_scoped_edits_do_not_modify_other_maps(tmp_path):
    wad=fixture();first=DoomMap(wad,'MAP01');second=DoomMap(wad,'MAP02')
    second.replace_records('THINGS',[Thing(5,6,0,40000,32768)])
    assert first.records('THINGS')[0].x==0
    assert second.records('THINGS')[0].x==5
    second.save(tmp_path/'out.wad')


def test_bad_references_and_stale_geometry_block_save(tmp_path):
    map=DoomMap(fixture(),'MAP01');map.replace_records('VERTEXES',[Vertex(0,0)])
    with pytest.raises(DoomWadError,match='vertex'): map.validate()
    map.replace_records('VERTEXES',[Vertex(0,0),Vertex(20,0)])
    with pytest.raises(DoomWadError,match='rebuild'): map.save(tmp_path/'out.wad')
    assert not (tmp_path/'out.wad').exists()


@pytest.mark.parametrize('format_lump',['TEXTMAP','BEHAVIOR'])
def test_other_map_formats_are_explicitly_rejected(format_lump):
    wad=fixture();wad.insert(1,format_lump,b'')
    with pytest.raises(DoomWadError): DoomMap(wad,'MAP01')
