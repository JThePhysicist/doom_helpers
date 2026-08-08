from __future__ import annotations

from .exceptions import DoomWadError
from .wad import Wad

PALETTE_SIZE = 256
_PLAYPAL_ENTRY_SIZE = PALETTE_SIZE * 3


class Palette:
    """A single 256-color Doom palette (RGB), with reverse-lookup for encoding."""

    def __init__(self, colors: list[tuple[int, int, int]]):
        if len(colors) != PALETTE_SIZE:
            raise ValueError(f"Palette must have exactly {PALETTE_SIZE} colors")
        self.colors = colors
        self._exact_index: dict[tuple[int, int, int], int] = {
            c: i for i, c in enumerate(colors)
        }
        self._nearest_cache: dict[tuple[int, int, int], int] = {}

    @classmethod
    def from_playpal_bytes(cls, data: bytes, palette_index: int = 0) -> "Palette":
        start = palette_index * _PLAYPAL_ENTRY_SIZE
        end = start + _PLAYPAL_ENTRY_SIZE
        if end > len(data):
            raise DoomWadError(
                f"PLAYPAL lump too small for palette index {palette_index}"
            )
        chunk = data[start:end]
        colors = [
            (chunk[i], chunk[i + 1], chunk[i + 2]) for i in range(0, len(chunk), 3)
        ]
        return cls(colors)

    @classmethod
    def from_wad(cls, wad: Wad, palette_index: int = 0) -> "Palette":
        playpal = wad.find("PLAYPAL")
        return cls.from_playpal_bytes(playpal.data, palette_index=palette_index)

    def rgb(self, index: int) -> tuple[int, int, int]:
        return self.colors[index]

    def nearest_index(self, rgb: tuple[int, int, int]) -> int:
        exact = self._exact_index.get(rgb)
        if exact is not None:
            return exact

        cached = self._nearest_cache.get(rgb)
        if cached is not None:
            return cached

        r, g, b = rgb
        best_index = 0
        best_dist = None
        for i, (cr, cg, cb) in enumerate(self.colors):
            dist = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_index = i
                if dist == 0:
                    break
        self._nearest_cache[rgb] = best_index
        return best_index

    def to_manifest(self) -> list[list[int]]:
        return [[r, g, b] for (r, g, b) in self.colors]

    @classmethod
    def from_manifest(cls, data: list[list[int]]) -> "Palette":
        return cls([tuple(c) for c in data])
