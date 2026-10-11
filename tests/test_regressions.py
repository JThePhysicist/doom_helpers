import struct
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from doomwad import DoomWadError, InvalidWadError, Palette, Wad
from doomwad.atlas import build_atlas, realign_sprites, save_atlas
from doomwad.lumps.maps import Linedef, Sidedef
from doomwad.sprites import DecodedPatch, decode_patch, find_sprite_lumps


@pytest.fixture
def palette():
    return Palette([(i, i, i) for i in range(256)])


@pytest.mark.parametrize('data', [
    struct.pack('<4sii', b'PWAD', -1, 12),
    struct.pack('<4sii', b'PWAD', 1, 12) + struct.pack('<ii8s', 12, -1, b'BAD'),
])
def test_negative_wad_fields_rejected(data):
    with pytest.raises(InvalidWadError):
        Wad.from_bytes(data)


@pytest.mark.parametrize('tail', [b'\x00', b'\x00\x03\x00\x01'])
def test_truncated_patch_posts_rejected(palette, tail):
    data = struct.pack('<hhhhI', 1, 3, 0, 0, 12) + tail
    with pytest.raises(DoomWadError):
        decode_patch('BAD', data, palette)


def test_unsigned_map_references_and_missing_back_side():
    linedef = Linedef(40000, 50000, 32768, 0, 0, 40000, -1)
    assert Linedef.list_from_bytes(Linedef.list_to_bytes([linedef])) == [linedef]
    sidedef = Sidedef(-8, 12, '-', '-', 'STONE', 40000)
    assert Sidedef.list_from_bytes(Sidedef.list_to_bytes([sidedef])) == [sidedef]


def test_all_sprite_ranges_are_discovered():
    wad = Wad()
    for name in ['S_START', 'TROOA1', 'S_END', 'SS_START', 'TROOB1', 'SS_END',
                 'S_START', 'TROOC1', 'S_END', 'TROOD1']:
        wad.add(name, b'')
    assert [lump.name for lump in find_sprite_lumps(wad, ['TROO'])] == [
        'TROOA1', 'TROOB1', 'TROOC1']


def test_duplicate_patch_names_rejected(palette):
    patch = DecodedPatch('TROOA1', Image.new('RGBA', (4, 4)), 0, 0)
    with pytest.raises(DoomWadError, match='Duplicate'):
        build_atlas([patch, patch], palette)


@pytest.mark.parametrize('vertical', [False, True])
def test_realign_shared_padding_does_not_contaminate_neighbor(palette, vertical):
    patches = [DecodedPatch(name, Image.new('RGBA', (6 if vertical else 4, 4), (20, 20, 20, 255)), 0, 0)
               for name in ['TROOA1', 'TROOB1']]
    pages, manifest = build_atlas(patches, palette, atlas_size=10 if vertical else 32)
    pages[0].putpixel((1, 4) if vertical else (4, 1), (10, 10, 10, 255))
    realign_sprites(manifest, pages)
    first, second = manifest['sprites']
    assert (first['width'], first['height']) == ((6, 5) if vertical else (5, 4))
    assert (second['width'], second['height']) == (6 if vertical else 4, 4)


@pytest.mark.parametrize('existing', [False, True])
def test_rebuild_places_new_sprites_inside_markers(tmp_path, palette, existing):
    patch = DecodedPatch('TROOA1', Image.new('RGBA', (4, 4), (20, 20, 20, 255)), 0, 0)
    pages, manifest = build_atlas([patch], palette)
    _, manifest_path = save_atlas(pages, manifest, tmp_path, 'TROO')
    output = tmp_path / 'output.wad'
    script = Path(__file__).resolve().parents[1] / 'scripts/rebuild_sprite_atlas.py'
    command = [sys.executable, str(script), '--manifest', str(manifest_path), '--output', str(output)]
    if existing:
        wad = Wad()
        for name in ['S_START', 'POSSA1', 'S_END', 'OTHER']:
            wad.add(name, b'')
        source = tmp_path / 'source.wad'
        wad.save(source)
        command.extend(['--wad', str(source)])
    subprocess.run(command, check=True, capture_output=True, text=True)
    rebuilt = Wad.load(output)
    assert [lump.name for lump in find_sprite_lumps(rebuilt, ['TROO'])] == ['TROOA1']
    assert rebuilt.index_of('S_START') < rebuilt.index_of('TROOA1') < rebuilt.index_of('S_END')
    if existing:
        assert rebuilt.find('OTHER').data == b''
