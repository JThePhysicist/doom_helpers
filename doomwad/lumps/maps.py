from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import ClassVar

# Standard (non-Hexen/UDMF) Doom map lump names, in the order they follow
# a ExMy/MAPxx marker lump within a WAD directory.
MAP_LUMP_NAMES = (
    "THINGS",
    "LINEDEFS",
    "SIDEDEFS",
    "VERTEXES",
    "SEGS",
    "SSECTORS",
    "NODES",
    "SECTORS",
    "REJECT",
    "BLOCKMAP",
)


def is_map_marker(name: str) -> bool:
    """Return True if `name` looks like a map marker lump (ExMy or MAPxx)."""
    if len(name) == 4 and name[0] == "E" and name[2] == "M":
        return name[1].isdigit() and name[3].isdigit()
    if len(name) == 5 and name.startswith("MAP"):
        return name[3:].isdigit()
    return False


@dataclass
class Thing:
    _FORMAT: ClassVar[str] = "<hhhhh"
    _SIZE: ClassVar[int] = struct.calcsize(_FORMAT)

    x: int
    y: int
    angle: int
    type: int
    flags: int

    @classmethod
    def list_from_bytes(cls, data: bytes) -> list["Thing"]:
        return [cls(*rec) for rec in struct.iter_unpack(cls._FORMAT, data)]

    @classmethod
    def list_to_bytes(cls, things: list["Thing"]) -> bytes:
        buf = bytearray()
        for t in things:
            buf += struct.pack(cls._FORMAT, t.x, t.y, t.angle, t.type, t.flags)
        return bytes(buf)


@dataclass
class Linedef:
    _FORMAT: ClassVar[str] = "<hhhhhhh"
    _SIZE: ClassVar[int] = struct.calcsize(_FORMAT)

    start_vertex: int
    end_vertex: int
    flags: int
    special: int
    tag: int
    front_sidedef: int
    back_sidedef: int

    @classmethod
    def list_from_bytes(cls, data: bytes) -> list["Linedef"]:
        return [cls(*rec) for rec in struct.iter_unpack(cls._FORMAT, data)]

    @classmethod
    def list_to_bytes(cls, linedefs: list["Linedef"]) -> bytes:
        buf = bytearray()
        for ld in linedefs:
            buf += struct.pack(
                cls._FORMAT,
                ld.start_vertex,
                ld.end_vertex,
                ld.flags,
                ld.special,
                ld.tag,
                ld.front_sidedef,
                ld.back_sidedef,
            )
        return bytes(buf)


@dataclass
class Sidedef:
    _FORMAT: ClassVar[str] = "<hh8s8s8sh"
    _SIZE: ClassVar[int] = struct.calcsize(_FORMAT)

    x_offset: int
    y_offset: int
    upper_texture: str
    lower_texture: str
    middle_texture: str
    sector: int

    @classmethod
    def list_from_bytes(cls, data: bytes) -> list["Sidedef"]:
        result = []
        for rec in struct.iter_unpack(cls._FORMAT, data):
            xo, yo, upper, lower, middle, sector = rec
            result.append(
                cls(
                    x_offset=xo,
                    y_offset=yo,
                    upper_texture=_decode_name(upper),
                    lower_texture=_decode_name(lower),
                    middle_texture=_decode_name(middle),
                    sector=sector,
                )
            )
        return result

    @classmethod
    def list_to_bytes(cls, sidedefs: list["Sidedef"]) -> bytes:
        buf = bytearray()
        for sd in sidedefs:
            buf += struct.pack(
                cls._FORMAT,
                sd.x_offset,
                sd.y_offset,
                _encode_name(sd.upper_texture),
                _encode_name(sd.lower_texture),
                _encode_name(sd.middle_texture),
                sd.sector,
            )
        return bytes(buf)


@dataclass
class Vertex:
    _FORMAT: ClassVar[str] = "<hh"
    _SIZE: ClassVar[int] = struct.calcsize(_FORMAT)

    x: int
    y: int

    @classmethod
    def list_from_bytes(cls, data: bytes) -> list["Vertex"]:
        return [cls(*rec) for rec in struct.iter_unpack(cls._FORMAT, data)]

    @classmethod
    def list_to_bytes(cls, vertexes: list["Vertex"]) -> bytes:
        buf = bytearray()
        for v in vertexes:
            buf += struct.pack(cls._FORMAT, v.x, v.y)
        return bytes(buf)


@dataclass
class Sector:
    _FORMAT: ClassVar[str] = "<hh8s8shhh"
    _SIZE: ClassVar[int] = struct.calcsize(_FORMAT)

    floor_height: int
    ceiling_height: int
    floor_texture: str
    ceiling_texture: str
    light_level: int
    special: int
    tag: int

    @classmethod
    def list_from_bytes(cls, data: bytes) -> list["Sector"]:
        result = []
        for rec in struct.iter_unpack(cls._FORMAT, data):
            fh, ch, floor, ceil, light, special, tag = rec
            result.append(
                cls(
                    floor_height=fh,
                    ceiling_height=ch,
                    floor_texture=_decode_name(floor),
                    ceiling_texture=_decode_name(ceil),
                    light_level=light,
                    special=special,
                    tag=tag,
                )
            )
        return result

    @classmethod
    def list_to_bytes(cls, sectors: list["Sector"]) -> bytes:
        buf = bytearray()
        for s in sectors:
            buf += struct.pack(
                cls._FORMAT,
                s.floor_height,
                s.ceiling_height,
                _encode_name(s.floor_texture),
                _encode_name(s.ceiling_texture),
                s.light_level,
                s.special,
                s.tag,
            )
        return bytes(buf)


def _decode_name(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def _encode_name(name: str) -> bytes:
    return name.encode("ascii")[:8].ljust(8, b"\x00")
