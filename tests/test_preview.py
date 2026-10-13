from copy import deepcopy
from PIL import Image

from doomwad import Palette
from doomwad.atlas import build_atlas
from doomwad.preview import preview_html
from doomwad.sprites import DecodedPatch


def test_preview_is_embedded_escaped_read_only_and_compares_pixels():
    pages,m=build_atlas([DecodedPatch('<A>A0',Image.new('RGBA',(2,2),(10,10,10,255)),1,2)],Palette([(i,i,i) for i in range(256)]),atlas_size=8)
    old=deepcopy(m);baseline=[page.copy() for page in pages]
    pages[0].putpixel((0,0),(20,20,20,255))
    document=preview_html(m,pages,(m,baseline))
    assert '1 changed pixels' in document
    assert '&lt;A&gt;A0' in document and '<A>A0' not in document
    assert 'data:image/png;base64,' in document
    assert 'stroke="orange"' in document and 'fill="red"' in document
    assert m==old
