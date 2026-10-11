import pytest
from doomwad import DoomWadError
from doomwad.atlas import ShelfPacker


@pytest.mark.parametrize('size,padding',[(0,2),(-1,2),(32768,2),(8,-1),(True,2)])
def test_invalid_packing_parameters(size,padding):
    with pytest.raises(DoomWadError): ShelfPacker(size,padding)


def test_packing_is_reproducible_across_input_order():
    items=[('B',4,4),('A',4,4),('C',2,3)]
    assert ShelfPacker(12,2).pack(items)==ShelfPacker(12,2).pack(list(reversed(items)))
    with pytest.raises(DoomWadError): ShelfPacker().pack([('BAD',0,3)])
