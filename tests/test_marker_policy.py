import pytest

from doomwad import Wad, DoomWadError
from doomwad.sprites import sprite_ranges, find_sprite_lumps, update_sprite


@pytest.mark.parametrize('names', [['S_END'], ['S_START'], ['S_END','S_START'],
    ['S_START','SS_END'], ['S_START','SS_START','SS_END','S_END']])
def test_invalid_marker_ranges_rejected(names):
    wad=Wad()
    for name in names: wad.add(name,b'')
    with pytest.raises(DoomWadError): wad.validate()


def test_duplicate_selection_and_outside_range():
    wad=Wad();wad.add('S_START',b'');wad.add('TROOA1',b'first');wad.add('TROOA1',b'last');wad.add('S_END',b'')
    with pytest.raises(DoomWadError): find_sprite_lumps(wad,['TROO'])
    assert find_sprite_lumps(wad,['TROO'],duplicate_policy='first')[0].data == b'first'
    assert find_sprite_lumps(wad,['TROO'],duplicate_policy='last')[0].data == b'last'
    update_sprite(wad,'TROOA1',b'edited','last')
    assert wad.find_all('TROOA1')[-1].data == b'edited'
    wad.add('TROOB1',b'outside')
    with pytest.raises(DoomWadError,match='outside'): update_sprite(wad,'TROOB1',b'edited')


def test_repeated_marker_pairs_and_map_duplicate_names_are_valid():
    wad=Wad()
    for name in ['S_START','TROOA1','S_END','SS_START','TROOB1','SS_END','THINGS','THINGS']:
        wad.add(name,b'')
    wad.validate()
    assert sprite_ranges(wad)==[(0,2),(3,5)]
