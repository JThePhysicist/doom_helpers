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


def test_page_budget_is_checked_before_image_allocation():
    from PIL import Image
    from doomwad import Palette
    from doomwad.atlas import build_atlas
    from doomwad.sprites import DecodedPatch
    with pytest.raises(DoomWadError,match='pixel budget'):
        build_atlas([DecodedPatch('TROOA1',Image.new('RGBA',(2,2)),0,0)],
                    Palette([(0,0,0)]*256),atlas_size=10000,max_pixels=100)
