from dataclasses import dataclass


@dataclass
class Lump:
    """A single named lump of raw data from a WAD directory."""

    name: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        return f"Lump(name={self.name!r}, size={self.size})"
