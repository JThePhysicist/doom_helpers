import struct

from PIL import Image

from doomwad import Palette, decode_patch, encode_patch
from doomwad.atlas import build_atlas, save_atlas, load_manifest, load_atlas_pages, iter_manifest_sprites


def test_duplicate_rgb_indices_survive_atlas_round_trip(tmp_path):
    palette=Palette([(0,0,0)]*256)
    raw=struct.pack('<hhhhI',1,1,0,0,12)+bytes([0,1,0,42,0,255])
    patch=decode_patch('TROOA1',raw,palette)
    pages,m=build_atlas([patch],palette,atlas_size=8,preserve_indices=True)
    _,path=save_atlas(pages,m,tmp_path,'TROO')
    manifest=load_manifest(path);pages=load_atlas_pages(manifest,tmp_path)
    name,tile,left,top=iter_manifest_sprites(manifest,pages)[0]
    rebuilt=encode_patch(tile,left,top,palette,palette_indices=tile.info['palette_indices'])
    assert rebuilt==raw


def test_alternate_palette_and_edited_pixel_fallback():
    data=bytes([0])*768+bytes([100])*768
    palette=Palette.from_playpal_bytes(data,palette_index=1)
    assert palette.rgb(42)==(100,100,100)
    palette=Palette([(i,i,i) for i in range(256)])
    image=Image.new('RGBA',(1,1),(200,200,200,255))
    encoded=encode_patch(image,0,0,palette,palette_indices=Image.new('L',(1,1),42))
    assert encoded[15]==200
