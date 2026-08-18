from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pytest
from PIL import Image

from doomface.geometry import (
    GeometryValidationError,
    MediaPipeFaceLandmarker,
    _check_gaze,
    _check_mouth_open,
    _estimate_gaze,
    _face_bounding_box,
    _mouth_open_ratio,
    load_image,
    validate_and_align,
)
from doomface.parser import Expression, FaceState, GazeDirection

_NUM_LANDMARKS = 468


@dataclass(frozen=True)
class _FakeLandmark:
    x: float
    y: float
    z: float = 0.0


def _landmarks(overrides: dict[int, tuple[float, float]]) -> list[_FakeLandmark]:
    base = [_FakeLandmark(0.5, 0.5) for _ in range(_NUM_LANDMARKS)]
    for index, (x, y) in overrides.items():
        base[index] = _FakeLandmark(x, y)
    return base


def _center_gaze_open_mouth_landmarks() -> list[_FakeLandmark]:
    return _landmarks(
        {
            33: (0.3, 0.5),
            263: (0.7, 0.5),
            1: (0.5, 0.5),
            13: (0.5, 0.45),
            14: (0.5, 0.55),
        }
    )


class _FakeLandmarker:
    def __init__(self, landmarks: Sequence[_FakeLandmark] | None) -> None:
        self._landmarks = landmarks

    def detect(self, image: np.ndarray) -> Sequence[_FakeLandmark] | None:
        return self._landmarks


def _write_test_image(path: Path, width: int = 100, height: int = 120) -> str:
    Image.new("RGB", (width, height), color=(10, 20, 30)).save(path)
    return str(path)


def test_estimate_gaze_center() -> None:
    landmarks = _landmarks({33: (0.3, 0.5), 263: (0.7, 0.5), 1: (0.5, 0.5)})
    assert _estimate_gaze(landmarks) is GazeDirection.CENTER


def test_estimate_gaze_right() -> None:
    landmarks = _landmarks({33: (0.3, 0.5), 263: (0.7, 0.5), 1: (0.55, 0.5)})
    assert _estimate_gaze(landmarks) is GazeDirection.RIGHT


def test_estimate_gaze_left() -> None:
    landmarks = _landmarks({33: (0.3, 0.5), 263: (0.7, 0.5), 1: (0.45, 0.5)})
    assert _estimate_gaze(landmarks) is GazeDirection.LEFT


def test_estimate_gaze_degenerate_eye_distance_is_center() -> None:
    landmarks = _landmarks({33: (0.5, 0.5), 263: (0.5, 0.5), 1: (0.9, 0.9)})
    assert _estimate_gaze(landmarks) is GazeDirection.CENTER


def test_mouth_open_ratio_open() -> None:
    landmarks = _landmarks(
        {33: (0.3, 0.5), 263: (0.7, 0.5), 13: (0.5, 0.45), 14: (0.5, 0.55)}
    )
    assert _mouth_open_ratio(landmarks) == pytest.approx(0.25)


def test_mouth_open_ratio_closed() -> None:
    landmarks = _landmarks(
        {33: (0.3, 0.5), 263: (0.7, 0.5), 13: (0.5, 0.500), 14: (0.5, 0.505)}
    )
    assert _mouth_open_ratio(landmarks) == pytest.approx(0.0125)


def test_face_bounding_box_applies_margin_and_clamps() -> None:
    minimal = [_FakeLandmark(0.4, 0.4), _FakeLandmark(0.6, 0.6)]
    box = _face_bounding_box(minimal, image_height=100, image_width=200)
    # x range [0.4, 0.6] * 200 = [80, 120], width 40, 20% margin = 8px each side
    # y range [0.4, 0.6] * 100 = [40, 60], height 20, 20% margin = 4px each side
    assert box == (72, 36, 128, 64)


def test_face_bounding_box_clamps_to_image_edges() -> None:
    near_origin = [_FakeLandmark(0.0, 0.0), _FakeLandmark(0.2, 0.2)]
    x0, y0, _, _ = _face_bounding_box(near_origin, image_height=50, image_width=50)
    assert (x0, y0) == (0, 0)

    near_far_edge = [_FakeLandmark(0.8, 0.8), _FakeLandmark(1.0, 1.0)]
    _, _, x1, y1 = _face_bounding_box(near_far_edge, image_height=50, image_width=50)
    assert (x1, y1) == (50, 50)


def test_check_gaze_raises_on_mismatch() -> None:
    landmarks = _landmarks({33: (0.3, 0.5), 263: (0.7, 0.5), 1: (0.5, 0.5)})
    target = FaceState(Expression.STRAIGHT, 0, GazeDirection.RIGHT)
    with pytest.raises(GeometryValidationError):
        _check_gaze(landmarks, target)


def test_check_mouth_open_skips_non_ouch_expressions() -> None:
    landmarks = _landmarks({33: (0.3, 0.5), 263: (0.7, 0.5), 13: (0.5, 0.5), 14: (0.5, 0.5)})
    target = FaceState(Expression.STRAIGHT, 0, GazeDirection.CENTER)
    _check_mouth_open(landmarks, target)  # must not raise


def test_check_mouth_open_raises_when_ouch_and_mouth_closed() -> None:
    landmarks = _landmarks({33: (0.3, 0.5), 263: (0.7, 0.5), 13: (0.5, 0.5), 14: (0.5, 0.5)})
    target = FaceState(Expression.OUCH, 0, GazeDirection.CENTER)
    with pytest.raises(GeometryValidationError):
        _check_mouth_open(landmarks, target)


def test_load_image_missing_file_raises() -> None:
    with pytest.raises(GeometryValidationError):
        load_image("/nonexistent/path/to/headshot.png")


def test_validate_and_align_success(tmp_path: Path) -> None:
    image_path = _write_test_image(tmp_path / "face.png")
    landmarker = _FakeLandmarker(_center_gaze_open_mouth_landmarks())
    target = FaceState(Expression.STRAIGHT, 0, GazeDirection.CENTER)

    valid, aligned = validate_and_align(image_path, target, landmarker)

    assert valid is True
    assert aligned.size > 0


def test_validate_and_align_no_face_raises(tmp_path: Path) -> None:
    image_path = _write_test_image(tmp_path / "face.png")
    landmarker = _FakeLandmarker(None)
    target = FaceState(Expression.STRAIGHT, 0, GazeDirection.CENTER)

    with pytest.raises(GeometryValidationError):
        validate_and_align(image_path, target, landmarker)


def test_validate_and_align_gaze_mismatch_raises(tmp_path: Path) -> None:
    image_path = _write_test_image(tmp_path / "face.png")
    landmarker = _FakeLandmarker(_center_gaze_open_mouth_landmarks())
    target = FaceState(Expression.STRAIGHT, 0, GazeDirection.RIGHT)

    with pytest.raises(GeometryValidationError):
        validate_and_align(image_path, target, landmarker)


def test_validate_and_align_ouch_requires_open_mouth(tmp_path: Path) -> None:
    image_path = _write_test_image(tmp_path / "face.png")
    closed_mouth = _landmarks(
        {33: (0.3, 0.5), 263: (0.7, 0.5), 1: (0.5, 0.5), 13: (0.5, 0.5), 14: (0.5, 0.5)}
    )
    landmarker = _FakeLandmarker(closed_mouth)
    target = FaceState(Expression.OUCH, 2, GazeDirection.CENTER)

    with pytest.raises(GeometryValidationError):
        validate_and_align(image_path, target, landmarker)


def test_media_pipe_landmarker_missing_model_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        MediaPipeFaceLandmarker(tmp_path / "does_not_exist.task")
