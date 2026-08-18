from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pytest
from PIL import Image

from doomface.geometry import Landmark
from doomface.main import (
    NoMatchingHeadshotError,
    find_aligned_match,
    iter_source_images,
    load_reference_sprite,
    process_target,
    run_pipeline,
)
from doomface.parser import Expression, FaceState, GazeDirection
from doomwad import Lump, Palette, Wad, encode_patch


def _palette() -> Palette:
    return Palette([(i, i, i) for i in range(255)] + [(0, 255, 255)])


def _write_image(path: Path) -> Path:
    Image.new("RGB", (20, 24), color=(5, 5, 5)).save(path)
    return path


class _ScriptedLandmarker:
    """Returns landmark results in call order, ignoring the input image."""

    def __init__(self, results: Sequence[Sequence[Landmark] | None]) -> None:
        self._results = list(results)
        self.calls = 0

    def detect(self, image: np.ndarray) -> Sequence[Landmark] | None:
        result = self._results[self.calls]
        self.calls += 1
        return result


class _AlwaysNoFaceLandmarker:
    def detect(self, image: np.ndarray) -> Sequence[Landmark] | None:
        return None


class _StubGenerator:
    def generate(
        self, aligned_image: np.ndarray, reference_sprite: np.ndarray, health_tier: int
    ) -> Image.Image:
        return Image.new("RGB", (24, 29), color=(health_tier * 10, 0, 0))


class _AllForegroundSegmenter:
    def segment(self, image: np.ndarray) -> np.ndarray:
        return np.ones(image.shape[:2], dtype=bool)


def _reference_wad_with_lump(lump_name: str, palette: Palette) -> Wad:
    wad = Wad()
    sprite = Image.new("RGBA", (4, 4), color=(0, 0, 0, 255))
    data = encode_patch(sprite, left_offset=0, top_offset=0, palette=palette)
    wad.lumps.append(Lump(lump_name, data))
    return wad


def test_iter_source_images_filters_and_sorts(tmp_path: Path) -> None:
    (tmp_path / "b.png").write_bytes(b"")
    (tmp_path / "a.jpg").write_bytes(b"")
    (tmp_path / "notes.txt").write_bytes(b"")

    images = iter_source_images(tmp_path)

    assert [p.name for p in images] == ["a.jpg", "b.png"]


def test_find_aligned_match_returns_first_geometric_success(tmp_path: Path) -> None:
    paths = [_write_image(tmp_path / f"{i}.png") for i in range(3)]
    # first candidate rejected (no face detected), second candidate accepted
    scripted = _ScriptedLandmarker(
        [None, _center_gaze_landmarks(), _center_gaze_landmarks()]
    )
    target = FaceState(Expression.STRAIGHT, 0, GazeDirection.CENTER)

    aligned = find_aligned_match(target, paths, scripted)

    assert aligned.size > 0
    assert scripted.calls == 2


def test_find_aligned_match_raises_when_no_candidate_matches(tmp_path: Path) -> None:
    paths = [_write_image(tmp_path / "only.png")]
    target = FaceState(Expression.STRAIGHT, 0, GazeDirection.CENTER)

    with pytest.raises(NoMatchingHeadshotError):
        find_aligned_match(target, paths, _AlwaysNoFaceLandmarker())


def test_load_reference_sprite_decodes_real_wad_lump() -> None:
    palette = _palette()
    wad = _reference_wad_with_lump("STFST00", palette)

    sprite = load_reference_sprite(wad, palette, "STFST00.png")

    assert sprite.shape == (4, 4, 3)
    assert tuple(sprite[0, 0]) == (0, 0, 0)


def test_process_target_success(tmp_path: Path) -> None:
    palette = _palette()
    _write_image(tmp_path / "headshot.png")
    reference_wad = _reference_wad_with_lump("STFST00", palette)

    result = process_target(
        "STFST00.png",
        iter_source_images(tmp_path),
        palette,
        reference_wad,
        _ScriptedLandmarker([_center_gaze_landmarks()]),
        _StubGenerator(),
        _AllForegroundSegmenter(),
        tmp_path / "out",
    )

    assert result.succeeded
    assert result.output_path is not None
    assert result.output_path.name == "STFST00.png"
    assert result.output_path.is_file()


def test_process_target_reports_error_without_raising(tmp_path: Path) -> None:
    palette = _palette()
    _write_image(tmp_path / "headshot.png")
    reference_wad = _reference_wad_with_lump("STFST00", palette)

    result = process_target(
        "STFST00.png",
        iter_source_images(tmp_path),
        palette,
        reference_wad,
        _AlwaysNoFaceLandmarker(),
        _StubGenerator(),
        _AllForegroundSegmenter(),
        tmp_path / "out",
    )

    assert not result.succeeded
    assert result.output_path is None
    assert result.error is not None


def test_run_pipeline_processes_every_target_independently(tmp_path: Path) -> None:
    palette = _palette()
    _write_image(tmp_path / "headshot.png")
    reference_wad = _reference_wad_with_lump("STFST00", palette)
    reference_wad.lumps.append(
        _reference_wad_with_lump("STFOUCH0", palette).lumps[0]
    )

    landmarker = _ScriptedLandmarker(
        [_center_gaze_landmarks(), None]
    )  # STFST00 matches, STFOUCH0 has no face detected

    results = run_pipeline(
        ["STFST00.png", "STFOUCH0.png"],
        tmp_path,
        palette,
        reference_wad,
        landmarker,
        _StubGenerator(),
        _AllForegroundSegmenter(),
        tmp_path / "out",
    )

    assert len(results) == 2
    assert results[0].succeeded
    assert not results[1].succeeded


def _center_gaze_landmarks() -> list[Landmark]:
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _L:
        x: float
        y: float
        z: float = 0.0

    base = [_L(0.5, 0.5) for _ in range(468)]
    base[33] = _L(0.3, 0.5)
    base[263] = _L(0.7, 0.5)
    base[1] = _L(0.5, 0.5)
    base[13] = _L(0.5, 0.45)
    base[14] = _L(0.5, 0.55)
    return base
