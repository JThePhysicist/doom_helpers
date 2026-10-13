import pytest
from PIL import Image

from doomwad import Palette, encode_patch, decode_patch


@pytest.mark.parametrize('height,start',[(256,255),(600,0),(1000,700),(32767,32700)])
def test_source_port_tall_posts(height,start):
    palette=Palette([(i,i,i) for i in range(256)])
    image=Image.new('RGBA',(1,height))
    for y in range(start,height):
        if y % 9 != 0: image.putpixel((0,y),(42,42,42,255))
    data=encode_patch(image,0,0,palette,profile='source-port')
    decoded=decode_patch('TROOA1',data,palette,profile='source-port')
    assert decoded.image.tobytes()==image.tobytes()
    with pytest.raises(ValueError): encode_patch(image,0,0,palette)


def test_long_solid_column_and_known_relative_fixture():
    palette=Palette([(i,i,i) for i in range(256)])
    image=Image.new('RGBA',(1,800),(42,42,42,255))
    data=encode_patch(image,0,0,palette,profile='source-port')
    assert decode_patch('TROOA1',data,palette,profile='source-port').image.tobytes()==image.tobytes()
    import struct
    data=struct.pack('<hhhhI',1,300,0,0,12)+bytes([254,0,0,0, 1,1,0,42,0,255])
    assert decode_patch('TROOA1',data,palette,profile='source-port').image.getpixel((0,255))==(42,42,42,255)
