from copy import deepcopy

import pytest
from PIL import Image

from doomwad import DoomWadError, Palette
from doomwad.atlas import build_atlas, iter_manifest_sprites, save_atlas
from doomwad.manifest import validate_manifest
from doomwad.sprites import DecodedPatch


@pytest.fixture
def manifest():
    return {'version': 1, 'atlas_size': 8, 'padding': 2,
            'palette': [[i, i, i] for i in range(256)], 'pages': ['page.png'],
            'sprites': [{'name': 'TROOA1', 'page': 0, 'x': 0, 'y': 0,
                         'width': 4, 'height': 4, 'left_offset': 0, 'top_offset': 0}]}


@pytest.mark.parametrize('field,value', [('version', 2), ('version', True),
    ('palette', []), ('pages', ['../escape.png']), ('sprites', {}), ('atlas_size', 0)])
def test_bad_top_level_fields(manifest, field, value):
    manifest[field] = value
    with pytest.raises(DoomWadError): validate_manifest(manifest)


@pytest.mark.parametrize('field,value', [('page', -1), ('x', -1), ('width', 9),
    ('left_offset', 32768), ('name', 'TOOLONGNAME'), ('height', False)])
def test_bad_sprite_fields(manifest, field, value):
    manifest['sprites'][0][field] = value
    with pytest.raises(DoomWadError): validate_manifest(manifest)


def test_duplicate_names_and_wrong_page_size(manifest):
    manifest['sprites'].append(deepcopy(manifest['sprites'][0]))
    with pytest.raises(DoomWadError): validate_manifest(manifest)
    manifest['sprites'].pop()
    with pytest.raises(DoomWadError): iter_manifest_sprites(manifest, [Image.new('RGBA', (4, 4))])


def test_save_validates_before_writing(tmp_path):
    pages, manifest = build_atlas([DecodedPatch('TROOA1', Image.new('RGBA', (4, 4)), 0, 0)],
                                  Palette([(i,i,i) for i in range(256)]), atlas_size=8)
    manifest['sprites'][0]['x'] = 8
    with pytest.raises(DoomWadError): save_atlas(pages, manifest, tmp_path / 'output', 'TROO')
    assert not (tmp_path / 'output').exists()
