import struct

import pytest
from hypothesis import given, strategies as st

from doomwad import DoomWadError, Palette, Wad, decode_patch


@given(st.binary(max_size=256))
def test_arbitrary_wad_bytes_fail_with_domain_errors_or_round_trip(data):
    try: wad = Wad.from_bytes(data)
    except DoomWadError: return
    assert Wad.from_bytes(wad.to_bytes()).to_bytes() == wad.to_bytes()


@given(st.binary(max_size=128))
def test_arbitrary_patch_bytes_never_leak_index_errors(data):
    try: decode_patch('TESTA1', data, Palette([(i,i,i) for i in range(256)]), max_pixels=1024)
    except DoomWadError: pass


def test_header_column_offsets_and_limits(tmp_path):
    palette = Palette([(i,i,i) for i in range(256)])
    with pytest.raises(DoomWadError, match='offset'):
        decode_patch('BAD', struct.pack('<hhhhI',1,1,0,0,0)+b'\xff', palette)
    with pytest.raises(DoomWadError, match='pixel limit'):
        decode_patch('BAD', struct.pack('<hhhh',100,100,0,0), palette, max_pixels=99)
    wad = Wad();wad.add('TEST',b'data');path=tmp_path/'w.wad';wad.save(path)
    with pytest.raises(DoomWadError, match='byte limit'): Wad.load(path,max_bytes=12)
    with pytest.raises(DoomWadError, match='lump limit'): Wad.load(path,max_lumps=0)
