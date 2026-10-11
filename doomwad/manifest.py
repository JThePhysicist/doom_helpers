"""Validation for persisted atlas manifests and decoded page dimensions."""
from pathlib import PurePath

from .exceptions import DoomWadError


def _integer(value, field, minimum=None, maximum=None):
    if type(value) is not int or (minimum is not None and value < minimum) or (
        maximum is not None and value > maximum
    ):
        raise DoomWadError(f"Manifest {field} must be an integer in the supported range")


def validate_manifest(manifest, pages=None):
    if not isinstance(manifest, dict):
        raise DoomWadError("Manifest must be a JSON object")
    required = {'version', 'atlas_size', 'padding', 'palette', 'pages', 'sprites'}
    missing = required - manifest.keys()
    if missing:
        raise DoomWadError(f"Manifest missing fields: {', '.join(sorted(missing))}")
    _integer(manifest['version'], 'version', 1, 1)
    _integer(manifest['atlas_size'], 'atlas_size', 1, 32767)
    _integer(manifest['padding'], 'padding', 0)
    palette = manifest['palette']
    if not isinstance(palette, list) or len(palette) != 256:
        raise DoomWadError("Manifest palette must contain 256 RGB triples")
    for color in palette:
        if not isinstance(color, list) or len(color) != 3:
            raise DoomWadError("Manifest palette entries must be RGB triples")
        for channel in color:
            _integer(channel, 'palette channel', 0, 255)
    filenames = manifest['pages']
    if not isinstance(filenames, list):
        raise DoomWadError("Manifest pages must be an array")
    for filename in filenames:
        if (not isinstance(filename, str) or not filename or '\\' in filename
                or PurePath(filename).is_absolute() or '..' in PurePath(filename).parts):
            raise DoomWadError("Manifest pages must be relative paths without traversal")
    if len(set(filenames)) != len(filenames):
        raise DoomWadError("Manifest page filenames must be unique")
    if pages is not None:
        if len(pages) != len(filenames):
            raise DoomWadError("Manifest page count does not match loaded pages")
        for page in pages:
            if page.size != (manifest['atlas_size'], manifest['atlas_size']):
                raise DoomWadError("Atlas page dimensions do not match manifest atlas_size")
    sprites = manifest['sprites']
    if not isinstance(sprites, list):
        raise DoomWadError("Manifest sprites must be an array")
    names = set()
    for entry in sprites:
        if not isinstance(entry, dict):
            raise DoomWadError("Manifest sprite must be an object")
        fields = {'name', 'page', 'x', 'y', 'width', 'height', 'left_offset', 'top_offset'}
        if fields - entry.keys():
            raise DoomWadError("Manifest sprite is missing required fields")
        name = entry['name']
        if (not isinstance(name, str) or not name or len(name) > 8 or not name.isascii()
                or '\x00' in name or name in names):
            raise DoomWadError("Manifest sprite names must be unique nonempty ASCII names of at most 8 bytes")
        names.add(name)
        _integer(entry['page'], f'{name}.page', 0, len(filenames) - 1)
        for field in ['x', 'y']:
            _integer(entry[field], f'{name}.{field}', 0)
        for field in ['width', 'height']:
            _integer(entry[field], f'{name}.{field}', 1)
        for field in ['left_offset', 'top_offset']:
            _integer(entry[field], f'{name}.{field}', -32768, 32767)
        if (entry['x'] + entry['width'] > manifest['atlas_size'] or
                entry['y'] + entry['height'] > manifest['atlas_size']):
            raise DoomWadError(f"Manifest sprite {name!r} extends outside its page")
        if 'allocation' in entry:
            box = entry['allocation']
            if not isinstance(box, list) or len(box) != 4:
                raise DoomWadError("Sprite allocation must be [x, y, width, height]")
            for i, value in enumerate(box):
                _integer(value, 'allocation', 0 if i < 2 else 1)
            ax, ay, aw, ah = box
            if (ax > entry['x'] or ay > entry['y'] or
                    ax+aw < entry['x']+entry['width'] or ay+ah < entry['y']+entry['height'] or
                    ax+aw > manifest['atlas_size'] or ay+ah > manifest['atlas_size']):
                raise DoomWadError("Sprite crop must fit inside its page and allocation")
    for i, entry in enumerate(sprites):
        if 'allocation' not in entry:
            continue
        x, y, w, h = entry['allocation']
        for other in sprites[i+1:]:
            if other['page'] != entry['page'] or 'allocation' not in other:
                continue
            ox, oy, ow, oh = other['allocation']
            if x < ox+ow and ox < x+w and y < oy+oh and oy < y+h:
                raise DoomWadError("Sprite editing allocations overlap")
    return manifest
