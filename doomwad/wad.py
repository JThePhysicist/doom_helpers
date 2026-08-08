from __future__ import annotations

import struct
from pathlib import Path
from typing import Iterator

from .exceptions import InvalidWadError, LumpNotFoundError
from .lump import Lump

_HEADER_FORMAT = "<4sii"
_HEADER_SIZE = struct.calcsize(_HEADER_FORMAT)
_DIRENTRY_FORMAT = "<ii8s"
_DIRENTRY_SIZE = struct.calcsize(_DIRENTRY_FORMAT)


class Wad:
    """In-memory representation of a Doom WAD file's lump directory."""

    def __init__(self, wad_type: str = "PWAD"):
        if wad_type not in ("IWAD", "PWAD"):
            raise ValueError("wad_type must be 'IWAD' or 'PWAD'")
        self.wad_type = wad_type
        self.lumps: list[Lump] = []

    @classmethod
    def load(cls, path: str | Path) -> "Wad":
        data = Path(path).read_bytes()
        return cls.from_bytes(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Wad":
        if len(data) < _HEADER_SIZE:
            raise InvalidWadError("File is too small to contain a WAD header")

        identification, num_lumps, info_table_ofs = struct.unpack_from(
            _HEADER_FORMAT, data, 0
        )
        wad_type = identification.decode("ascii", errors="replace")
        if wad_type not in ("IWAD", "PWAD"):
            raise InvalidWadError(f"Unrecognized WAD identification: {wad_type!r}")

        wad = cls(wad_type=wad_type)

        dir_end = info_table_ofs + num_lumps * _DIRENTRY_SIZE
        if info_table_ofs < 0 or dir_end > len(data):
            raise InvalidWadError("WAD directory extends past end of file")

        for i in range(num_lumps):
            offset = info_table_ofs + i * _DIRENTRY_SIZE
            filepos, size, raw_name = struct.unpack_from(
                _DIRENTRY_FORMAT, data, offset
            )
            name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace")

            if size == 0:
                lump_data = b""
            else:
                if filepos < 0 or filepos + size > len(data):
                    raise InvalidWadError(
                        f"Lump {name!r} data extends past end of file"
                    )
                lump_data = data[filepos : filepos + size]

            wad.lumps.append(Lump(name=name, data=lump_data))

        return wad

    def to_bytes(self) -> bytes:
        body = bytearray()
        directory = bytearray()
        offset = _HEADER_SIZE

        for lump in self.lumps:
            body += lump.data
            name_bytes = lump.name.encode("ascii")[:8].ljust(8, b"\x00")
            directory += struct.pack(_DIRENTRY_FORMAT, offset, lump.size, name_bytes)
            offset += lump.size

        header = struct.pack(
            _HEADER_FORMAT,
            self.wad_type.encode("ascii"),
            len(self.lumps),
            _HEADER_SIZE + len(body),
        )
        return bytes(header) + bytes(body) + bytes(directory)

    def save(self, path: str | Path) -> None:
        Path(path).write_bytes(self.to_bytes())

    def find(self, name: str) -> Lump:
        for lump in self.lumps:
            if lump.name == name:
                return lump
        raise LumpNotFoundError(f"No lump named {name!r}")

    def find_all(self, name: str) -> list[Lump]:
        return [lump for lump in self.lumps if lump.name == name]

    def index_of(self, name: str) -> int:
        for i, lump in enumerate(self.lumps):
            if lump.name == name:
                return i
        raise LumpNotFoundError(f"No lump named {name!r}")

    def add(self, name: str, data: bytes) -> Lump:
        lump = Lump(name=name[:8], data=data)
        self.lumps.append(lump)
        return lump

    def insert(self, index: int, name: str, data: bytes) -> Lump:
        lump = Lump(name=name[:8], data=data)
        self.lumps.insert(index, lump)
        return lump

    def remove(self, name: str) -> None:
        self.lumps.pop(self.index_of(name))

    def replace(self, name: str, data: bytes) -> None:
        self.lumps[self.index_of(name)] = Lump(name=name, data=data)

    def __len__(self) -> int:
        return len(self.lumps)

    def __iter__(self) -> Iterator[Lump]:
        return iter(self.lumps)

    def __contains__(self, name: str) -> bool:
        return any(lump.name == name for lump in self.lumps)

    def __repr__(self) -> str:
        return f"Wad(type={self.wad_type!r}, lumps={len(self.lumps)})"
