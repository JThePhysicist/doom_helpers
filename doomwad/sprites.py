from __future__ import annotations

import re
import struct
from dataclasses import dataclass

from PIL import Image

from .exceptions import DoomWadError
from .lump import Lump
from .palette import Palette
from .wad import Wad

# A Doom sprite/patch lump name is a 4-character sprite prefix, a frame
# letter, and a rotation digit (0 = no rotation variants, 1-8 for the eight
# view angles), optionally repeated once more for a mirrored frame that
# reuses the same patch (e.g. "TROOA2A8").
_SPRITE_NAME_RE = re.compile(
    r"^(?P<prefix>[A-Z0-9]{4})"
    r"(?P<frame1>[A-Z])(?P<rot1>[0-8])"
    r"(?:(?P<frame2>[A-Z])(?P<rot2>[0-8]))?$"
)

_SPRITE_MARKER_PAIRS = (("S_START", "S_END"), ("SS_START", "SS_END"))

_HEADER_FORMAT = "<hhhh"
_HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)
_ALPHA_OPAQUE_THRESHOLD = 128
# topdelta is a single byte and 0xFF is reserved as the column terminator,
# so the tallest row a post can start at is 254 -> max image height 255.
_MAX_PATCH_HEIGHT = 255


@dataclass
class DecodedPatch:
    name: str
    image: Image.Image  # RGBA
    left_offset: int
    top_offset: int
    palette_indices: Image.Image | None = None


def sprite_name_matches(name: str, prefix: str) -> bool:
    """True if `name` is a sprite/patch lump belonging to sprite `prefix`."""
    match = _SPRITE_NAME_RE.match(name)
    return bool(match) and match.group("prefix") == prefix


def find_sprite_lumps(wad: Wad, prefixes: list[str], *, duplicate_policy: str = "error") -> list[Lump]:
    """Find all lumps in `wad` for the given sprite prefixes (e.g. ["TROO"]).

    Restricts the search to between S_START/S_END (or SS_START/SS_END)
    markers when present, matching how sprites are stored in real WADs.
    """
    candidates = _lumps_in_sprite_range(wad)
    prefix_set = set(prefixes)
    return resolve_duplicates([
        lump
        for lump in candidates
        if any(sprite_name_matches(lump.name, p) for p in prefix_set)
    ], duplicate_policy)


def list_sprite_prefixes(wad: Wad) -> dict[str, list[str]]:
    """Group every sprite/patch lump in `wad` by its 4-character prefix.

    This is how you discover which sprite "entities" (e.g. TROO, POSS,
    SARG) a WAD actually contains, so you know what to pass to
    `find_sprite_lumps` / `--sprite` without already knowing the WAD's
    contents by heart. Returns {prefix: [lump names sorted]}, restricted to
    the S_START/S_END (or SS_START/SS_END) range when present.
    """
    groups: dict[str, list[str]] = {}
    for lump in _lumps_in_sprite_range(wad):
        match = _SPRITE_NAME_RE.match(lump.name)
        if not match:
            continue
        groups.setdefault(match.group("prefix"), []).append(lump.name)
    return {prefix: sorted(names) for prefix, names in sorted(groups.items())}


def sprite_ranges(wad: Wad) -> list[tuple[int, int]]:
    """Return paired marker bounds; malformed or mixed ranges are errors."""
    starts = dict(_SPRITE_MARKER_PAIRS)
    ends = set(starts.values())
    active = None
    ranges = []
    for i, lump in enumerate(wad.lumps):
        if lump.name in starts:
            if active is not None:
                raise DoomWadError('Nested sprite start markers are not supported')
            active = (i, starts[lump.name])
        elif lump.name in ends:
            if active is None or lump.name != active[1]:
                raise DoomWadError('Unmatched or mixed sprite end marker')
            ranges.append((active[0], i))
            active = None
    if active is not None:
        raise DoomWadError('Unmatched sprite start marker')
    return ranges


def _lumps_in_sprite_range(wad: Wad) -> list[Lump]:
    ranges = sprite_ranges(wad)
    return [lump for start, end in ranges for lump in wad.lumps[start+1:end]] if ranges else list(wad.lumps)


def resolve_duplicates(lumps: list[Lump], policy: str = 'error') -> list[Lump]:
    if policy not in ('error', 'first', 'last'):
        raise DoomWadError('Duplicate policy must be error, first, or last')
    result = {}
    for lump in lumps:
        if lump.name in result:
            if policy == 'error':
                raise DoomWadError(f'Duplicate sprite {lump.name!r}; select first or last explicitly')
            if policy == 'first':
                continue
        result[lump.name] = lump
    return list(result.values())


def update_sprite(wad: Wad, name: str, data: bytes, duplicate_policy: str = 'error') -> None:
    ranges = sprite_ranges(wad)
    matches = [i for i,lump in enumerate(wad.lumps) if lump.name == name]
    resolve_duplicates([wad.lumps[i] for i in matches], duplicate_policy)
    if matches:
        chosen = matches[-1] if duplicate_policy == 'last' else matches[0]
        if ranges and not any(start < chosen < end for start,end in ranges):
            raise DoomWadError(f'Sprite {name!r} exists outside a sprite range')
        wad.lumps[chosen] = Lump(name, data)
    elif ranges:
        wad.insert(ranges[-1][1], name, data)
    else:
        wad.add('S_START', b'')
        wad.add(name, data)
        wad.add('S_END', b'')


def decode_patch(name: str, data: bytes, palette: Palette, *,
                 max_pixels: int = 4_194_304, profile: str = "vanilla") -> DecodedPatch:
    """Decode a Doom picture-format lump into an RGBA Pillow image."""
    if profile not in ("vanilla", "source-port"):
        raise DoomWadError("Patch profile must be vanilla or source-port")
    if len(data) < _HEADER_SIZE:
        raise DoomWadError(f"Patch {name!r} is too small to contain a header")

    width, height, left, top = struct.unpack_from(_HEADER_FORMAT, data, 0)
    if width <= 0 or height <= 0:
        raise DoomWadError(f"Patch {name!r} has invalid dimensions {width}x{height}")

    if width * height > max_pixels:
        raise DoomWadError(f"Patch {name!r} exceeds configured pixel limit")

    columnofs_fmt = f"<{width}I"
    columnofs_size = struct.calcsize(columnofs_fmt)
    if _HEADER_SIZE + columnofs_size > len(data):
        raise DoomWadError(f"Patch {name!r} column table extends past end of lump")
    columnofs = struct.unpack_from(columnofs_fmt, data, _HEADER_SIZE)

    if any(offset < _HEADER_SIZE + columnofs_size or offset >= len(data) for offset in columnofs):
        raise DoomWadError(f"Patch {name!r} column offset is outside post data")

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = image.load()
    indices = Image.new("L", (width, height))

    for col in range(width):
        offset = columnofs[col]
        previous_top = -1
        while True:
            if offset >= len(data):
                raise DoomWadError(f"Patch {name!r} column {col} runs off the end")
            topdelta = data[offset]
            if topdelta == 0xFF:
                break
            if offset + 3 > len(data):
                raise DoomWadError(f"Patch {name!r} column {col} has a truncated post header")
            length = data[offset + 1]
            if offset + 3 + length + 1 > len(data):
                raise DoomWadError(f"Patch {name!r} column {col} has truncated post data")
            if profile == 'source-port' and topdelta <= previous_top:
                topdelta += previous_top
            previous_top = topdelta
            if topdelta + length > height:
                raise DoomWadError(f"Patch {name!r} post extends beyond image height")
            pixel_offset = offset + 3
            for i in range(length):
                index = data[pixel_offset + i]
                r, g, b = palette.rgb(index)
                y = topdelta + i
                if y < height:
                    pixels[col, y] = (r, g, b, 255)
                    indices.putpixel((col, y), index)
            offset = pixel_offset + length + 1

    return DecodedPatch(name=name, image=image, left_offset=left, top_offset=top, palette_indices=indices)


def encode_patch(
    image: Image.Image,
    left_offset: int,
    top_offset: int,
    palette: Palette,
    alpha_threshold: int = _ALPHA_OPAQUE_THRESHOLD,
    *, palette_indices: Image.Image | None = None, profile: str = "vanilla",
) -> bytes:
    """Encode an RGBA Pillow image back into Doom picture-format lump bytes."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError(f"Cannot encode an image with size {width}x{height}")
    if profile not in ('vanilla', 'source-port'):
        raise ValueError('Patch profile must be vanilla or source-port')
    if width > 32767 or height > 32767:
        raise ValueError('Patch dimensions must fit signed 16-bit fields')
    if profile == 'vanilla' and height > _MAX_PATCH_HEIGHT:
        raise ValueError(
            f"Image height {height} exceeds the Doom picture format's limit "
            f"of {_MAX_PATCH_HEIGHT}px (single-byte post offsets)"
        )

    if palette_indices is not None and (palette_indices.mode != 'L' or palette_indices.size != image.size):
        raise ValueError('Palette index image must be L mode with the same size as the patch')
    pixels = image.load()
    column_bytes: list[bytes] = []

    for x in range(width):
        col = bytearray()
        y = 0
        previous_top = -1
        while y < height:
            if pixels[x, y][3] < alpha_threshold:
                y += 1
                continue
            run_start = y
            run = bytearray()
            while y < height and pixels[x, y][3] >= alpha_threshold and len(run) < 255:
                r, g, b, _a = pixels[x, y]
                original = palette_indices.getpixel((x, y)) if palette_indices is not None else None
                index = original if original is not None and palette.rgb(original) == (r,g,b) else palette.nearest_index((r,g,b))
                run.append(index)
                y += 1
            if profile == 'source-port' and run_start > 254:
                if previous_top < 254:
                    col += bytes([254, 0, 0, 0])
                    previous_top = 254
                while run_start - previous_top > 254:
                    col += bytes([254, 0, 0, 0])
                    previous_top += 254
                delta = run_start - previous_top
            else:
                delta = run_start
            col += bytes([delta, len(run), 0]) + bytes(run) + bytes([0])
            previous_top = run_start
        col.append(0xFF)
        column_bytes.append(bytes(col))

    header_size = _HEADER_SIZE + 4 * width
    offsets = []
    running = header_size
    for cb in column_bytes:
        offsets.append(running)
        running += len(cb)

    header = struct.pack(_HEADER_FORMAT, width, height, left_offset, top_offset)
    header += struct.pack(f"<{width}I", *offsets)
    return header + b"".join(column_bytes)
