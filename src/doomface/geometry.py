"""Phase 2: Geometry Validator.

Validates that a source headshot matches a target :class:`FaceState`'s
required gaze direction and expression, and crops it to the face bounding
box (+20% margin) for downstream style transfer.

Landmark detection is behind the :class:`FaceLandmarker` protocol so the
geometry math is fully unit-testable without a MediaPipe model asset.
:class:`MediaPipeFaceLandmarker` is the real, local-inference
implementation, built on MediaPipe's Face Landmarker Task (the legacy
``mediapipe.solutions.face_mesh`` API has been removed from current
MediaPipe releases in favor of this Tasks API) -- it requires a
``face_landmarker.task`` model bundle downloaded once and cached locally;
no network access is used at inference time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

import numpy as np
from numpy.typing import NDArray

from .parser import Expression, FaceState, GazeDirection

# Standard MediaPipe face-mesh (468-point) canonical landmark indices.
_LEFT_EYE_OUTER = 33
_RIGHT_EYE_OUTER = 263
_NOSE_TIP = 1
_UPPER_INNER_LIP = 13
_LOWER_INNER_LIP = 14

_YAW_RATIO_THRESHOLD = 0.08
_MOUTH_OPEN_RATIO_THRESHOLD = 0.06
_CROP_MARGIN = 0.20


class Landmark(Protocol):
    """A single normalized (0..1) 3D face landmark."""

    @property
    def x(self) -> float: ...
    @property
    def y(self) -> float: ...
    @property
    def z(self) -> float: ...


class FaceLandmarker(Protocol):
    """Detects the dominant face's landmarks in an RGB image."""

    def detect(self, image: NDArray[np.uint8]) -> Sequence[Landmark] | None: ...


class GeometryValidationError(ValueError):
    """Raised when a source headshot does not match the target face state."""


def _estimate_gaze(landmarks: Sequence[Landmark]) -> GazeDirection:
    left_eye = landmarks[_LEFT_EYE_OUTER]
    right_eye = landmarks[_RIGHT_EYE_OUTER]
    nose = landmarks[_NOSE_TIP]

    inter_eye_dist = abs(right_eye.x - left_eye.x)
    if inter_eye_dist == 0:
        return GazeDirection.CENTER

    eye_mid_x = (left_eye.x + right_eye.x) / 2
    yaw_ratio = (nose.x - eye_mid_x) / inter_eye_dist

    if yaw_ratio > _YAW_RATIO_THRESHOLD:
        return GazeDirection.RIGHT
    if yaw_ratio < -_YAW_RATIO_THRESHOLD:
        return GazeDirection.LEFT
    return GazeDirection.CENTER


def _mouth_open_ratio(landmarks: Sequence[Landmark]) -> float:
    upper = landmarks[_UPPER_INNER_LIP]
    lower = landmarks[_LOWER_INNER_LIP]
    left_eye = landmarks[_LEFT_EYE_OUTER]
    right_eye = landmarks[_RIGHT_EYE_OUTER]

    inter_eye_dist = abs(right_eye.x - left_eye.x)
    if inter_eye_dist == 0:
        return 0.0
    return abs(lower.y - upper.y) / inter_eye_dist


def _face_bounding_box(
    landmarks: Sequence[Landmark], image_height: int, image_width: int
) -> tuple[int, int, int, int]:
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)

    margin_x = (x1 - x0) * _CROP_MARGIN
    margin_y = (y1 - y0) * _CROP_MARGIN

    px0 = max(0, int((x0 - margin_x) * image_width))
    py0 = max(0, int((y0 - margin_y) * image_height))
    px1 = min(image_width, int((x1 + margin_x) * image_width))
    py1 = min(image_height, int((y1 + margin_y) * image_height))
    return px0, py0, px1, py1


def _check_gaze(landmarks: Sequence[Landmark], target: FaceState) -> None:
    detected = _estimate_gaze(landmarks)
    if detected != target.gaze_direction:
        raise GeometryValidationError(
            f"gaze mismatch: detected {detected.name}, "
            f"target requires {target.gaze_direction.name}"
        )


def _check_mouth_open(landmarks: Sequence[Landmark], target: FaceState) -> None:
    if target.expression != Expression.OUCH:
        return
    if _mouth_open_ratio(landmarks) <= _MOUTH_OPEN_RATIO_THRESHOLD:
        raise GeometryValidationError(
            "OUCH target requires a visibly open mouth in the source headshot"
        )


def load_image(source_image_path: str) -> NDArray[np.uint8]:
    import cv2

    image = cv2.imread(source_image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise GeometryValidationError(f"could not read image: {source_image_path!r}")
    return np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def validate_and_align(
    source_image_path: str,
    target_state: FaceState,
    landmarker: FaceLandmarker,
) -> tuple[bool, NDArray[np.uint8]]:
    """Validate a headshot against ``target_state`` and crop it to the face.

    Returns ``(True, aligned_image)`` on success. Raises
    :class:`GeometryValidationError` (a ``ValueError``) if no face is
    found or the detected gaze/expression doesn't match ``target_state``.
    """
    image = load_image(source_image_path)
    landmarks = landmarker.detect(image)
    if not landmarks:
        raise GeometryValidationError(f"no face detected in {source_image_path!r}")

    _check_gaze(landmarks, target_state)
    _check_mouth_open(landmarks, target_state)

    height, width = image.shape[0], image.shape[1]
    x0, y0, x1, y1 = _face_bounding_box(landmarks, height, width)
    aligned_image: NDArray[np.uint8] = image[y0:y1, x0:x1]
    return True, aligned_image


class MediaPipeFaceLandmarker:
    """Real, local :class:`FaceLandmarker` backed by MediaPipe's Face Landmarker Task."""

    def __init__(self, model_asset_path: str | Path, num_faces: int = 1) -> None:
        model_path = Path(model_asset_path)
        if not model_path.is_file():
            raise FileNotFoundError(
                f"MediaPipe face landmarker model not found at {model_path!r}. "
                "Download 'face_landmarker.task' from the MediaPipe model zoo "
                "and place it there (see README) -- inference itself stays local."
            )

        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import (
            FaceLandmarker as _MpFaceLandmarker,
        )
        from mediapipe.tasks.python.vision import FaceLandmarkerOptions

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            num_faces=num_faces,
        )
        self._landmarker = _MpFaceLandmarker.create_from_options(options)

    def detect(self, image: NDArray[np.uint8]) -> Sequence[Landmark] | None:
        import mediapipe as mp

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        result = self._landmarker.detect(mp_image)
        faces: list[Sequence[Landmark]] = result.face_landmarks
        if not faces:
            return None
        return faces[0]
