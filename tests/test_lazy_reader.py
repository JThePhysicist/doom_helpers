import pytest
from doomwad import Wad, WadReader, DoomWadError


def test_lazy_payloads_and_metadata_match_eager_reader(tmp_path):
    path=tmp_path/'test.wad';wad=Wad();wad.add('ONE',b'first');wad.add('TWO',b'');wad.save(path)
    with WadReader(path) as reader:
        assert reader.wad_type==wad.wad_type
        assert [(l.name,l.size,l.data) for l in reader]==[(l.name,l.size,l.data) for l in wad]
        first=reader.find('ONE')
    with pytest.raises(ValueError): _=first.data


def test_lazy_reader_detects_post_open_truncation_and_limits(tmp_path):
    path=tmp_path/'test.wad';wad=Wad();wad.add('ONE',b'x'*10000);wad.save(path)
    with pytest.raises(DoomWadError): WadReader(path,max_bytes=12)
    with WadReader(path) as reader:
        path.write_bytes(b'')
        with pytest.raises(DoomWadError): _=reader.find('ONE').data


def test_zero_size_marker_does_not_seek_arbitrary_offset(tmp_path):
    import struct
    path=tmp_path/'marker.wad'
    path.write_bytes(struct.pack('<4sii',b'PWAD',1,12)+struct.pack('<ii8s',-1,0,b'MARKER'))
    with WadReader(path) as reader:
        assert reader.find('MARKER').data==Wad.load(path).find('MARKER').data==b''
