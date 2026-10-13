from copy import deepcopy

from PIL import Image

from doomwad.atlas import allocate_regions, realign_sprites
from doomwad.manifest import validate_manifest


def test_diagonal_and_repeated_edits_keep_stable_bounds():
    manifest = {'version':1, 'atlas_size':20, 'padding':4,
                'palette':[[0,0,0]]*256, 'pages':['p.png'], 'sprites':[
                    {'name':name,'page':0,'x':x,'y':y,'width':4,'height':4,
                     'left_offset':0,'top_offset':0}
                    for name,x,y in [('TROOA1',2,2),('TROOB1',8,8)]]}
    reversed_manifest = deepcopy(manifest)
    reversed_manifest['sprites'].reverse()
    allocate_regions(manifest)
    allocate_regions(reversed_manifest)
    assert {e['name']:e['allocation'] for e in manifest['sprites']} == {
        e['name']:e['allocation'] for e in reversed_manifest['sprites']}
    validate_manifest(manifest)
    allocations = [e['allocation'][:] for e in manifest['sprites']]
    page = Image.new('RGBA',(20,20))
    page.putpixel((3,3),(0,0,0,255));page.putpixel((9,9),(0,0,0,255))
    realign_sprites(manifest,[page])
    page.putpixel((2,2),(0,0,0,255))
    realign_sprites(manifest,[page])
    assert [e['allocation'] for e in manifest['sprites']] == allocations
    assert manifest['sprites'][0]['x'] == 2
    assert manifest['sprites'][1]['x'] == 9
    validate_manifest(manifest)


def test_explicit_margin_is_limited_to_stable_allocation(manifest):
    page=Image.new('RGBA',(8,8));page.putpixel((0,0),(0,0,0,255));page.putpixel((4,0),(0,0,0,255))
    allocate_regions(manifest)
    allocation=manifest['sprites'][0]['allocation'][:]
    realign_sprites(manifest,[page],margin=0)
    assert manifest['sprites'][0]['width']==1
    assert manifest['sprites'][0]['allocation']==allocation
    realign_sprites(manifest,[page])
    assert manifest['sprites'][0]['width']==5
