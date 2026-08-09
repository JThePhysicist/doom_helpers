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


def sprite_name_matches(name: str, prefix: str) -> bool:
    """True if `name` is a sprite/patch lump belonging to sprite `prefix`."""
    match = _SPRITE_NAME_RE.match(name)
    return bool(match) and match.group("prefix") == prefix


def find_sprite_lumps(wad: Wad, prefixes: list[str]) -> list[Lump]:
    """Find all lumps in `wad` for the given sprite prefixes (e.g. ["TROO"]).

    Restricts the search to between S_START/S_END (or SS_START/SS_END)
    markers when present, matching how sprites are stored in real WADs.
    """
    candidates = _lumps_in_sprite_range(wad)
    prefix_set = set(prefixes)
    return [
        lump
        for lump in candidates
        if any(sprite_name_matches(lump.name, p) for p in prefix_set)
    ]


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


def _lumps_in_sprite_range(wad: Wad) -> list[Lump]:
    for start_name, end_name in _SPRITE_MARKER_PAIRS:
        if start_name in wad and end_name in wad:
            start = wad.index_of(start_name)
            end = wad.index_of(end_name)
            return wad.lumps[start + 1 : end]
    return list(wad.lumps)


def decode_patch(name: str, data: bytes, palette: Palette) -> DecodedPatch:
    """Decode a Doom picture-format lump into an RGBA Pillow image."""
    if len(data) < _HEADER_SIZE:
        raise DoomWadError(f"Patch {name!r} is too small to contain a header")

    width, height, left, top = struct.unpack_from(_HEADER_FORMAT, data, 0)
    if width <= 0 or height <= 0:
        raise DoomWadError(f"Patch {name!r} has invalid dimensions {width}x{height}")

    columnofs_fmt = f"<{width}I"
    columnofs_size = struct.calcsize(columnofs_fmt)
    if _HEADER_SIZE + columnofs_size > len(data):
        raise DoomWadError(f"Patch {name!r} column table extends past end of lump")
    columnofs = struct.unpack_from(columnofs_fmt, data, _HEADER_SIZE)

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = image.load()

    for col in range(width):
        offset = columnofs[col]
        while True:
            if offset >= len(data):
                raise DoomWadError(f"Patch {name!r} column {col} runs off the end")
            topdelta = data[offset]
            if topdelta == 0xFF:
                break
            length = data[offset + 1]
            pixel_offset = offset + 3
            for i in range(length):
                index = data[pixel_offset + i]
                r, g, b = palette.rgb(index)
                y = topdelta + i
                if y < height:
                    pixels[col, y] = (r, g, b, 255)
            offset = pixel_offset + length + 1

    return DecodedPatch(name=name, image=image, left_offset=left, top_offset=top)


def encode_patch(
    image: Image.Image,
    left_offset: int,
    top_offset: int,
    palette: Palette,
    alpha_threshold: int = _ALPHA_OPAQUE_THRESHOLD,
) -> bytes:
    """Encode an RGBA Pillow image back into Doom picture-format lump bytes."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError(f"Cannot encode an image with size {width}x{height}")
    if height > _MAX_PATCH_HEIGHT:
        raise ValueError(
            f"Image height {height} exceeds the Doom picture format's limit "
            f"of {_MAX_PATCH_HEIGHT}px (single-byte post offsets)"
        )

    pixels = image.load()
    column_bytes: list[bytes] = []

    for x in range(width):
        col = bytearray()
        y = 0
        while y < height:
            if pixels[x, y][3] < alpha_threshold:
                y += 1
                continue
            run_start = y
            run = bytearray()
            while y < height and pixels[x, y][3] >= alpha_threshold:
                r, g, b, _a = pixels[x, y]
                run.append(palette.nearest_index((r, g, b)))
                y += 1
            col += bytes([run_start, len(run), 0]) + bytes(run) + bytes([0])
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
