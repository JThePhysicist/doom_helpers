from __future__ import annotations

from typing import TYPE_CHECKING

from .parser import GAZE_CENTER, GAZE_LEFT, GAZE_RIGHT, FaceState

if TYPE_CHECKING:
    import numpy as np

# MediaPipe FaceMesh landmark indices used by the checks below.
_LANDMARK_NOSE_TIP = 1
_LANDMARK_LEFT_EYE_OUTER = 33
_LANDMARK_RIGHT_EYE_OUTER = 263
_LANDMARK_UPPER_LIP = 13
_LANDMARK_LOWER_LIP = 14

_GAZE_YAW_THRESHOLD = 0.15
_MOUTH_OPEN_RATIO_THRESHOLD = 0.03

Point = tuple[float, float]


def estimate_gaze_direction(
    nose_tip: Point,
    left_eye_outer: Point,
    right_eye_outer: Point,
    threshold: float = _GAZE_YAW_THRESHOLD,
) -> int:
    """Estimate Center/Right/Left gaze from nose position relative to the eyes.

    The nose tip's horizontal offset from the inter-eye midpoint, normalized
    by inter-eye distance, is a stand-in for yaw: a centered face keeps the
    nose roughly between the eyes, while turning the head shifts it toward
    one side.
    """
    eye_span = right_eye_outer[0] - left_eye_outer[0]
    if eye_span == 0:
        return GAZE_CENTER
    midpoint_x = (left_eye_outer[0] + right_eye_outer[0]) / 2
    offset_ratio = (nose_tip[0] - midpoint_x) / eye_span
    if offset_ratio > threshold:
        return GAZE_RIGHT
    if offset_ratio < -threshold:
        return GAZE_LEFT
    return GAZE_CENTER


def is_mouth_open(
    upper_lip: Point,
    lower_lip: Point,
    left_eye_outer: Point,
    right_eye_outer: Point,
    threshold_ratio: float = _MOUTH_OPEN_RATIO_THRESHOLD,
) -> bool:
    """True if the vertical lip gap is large relative to inter-eye distance."""
    eye_span = right_eye_outer[0] - left_eye_outer[0]
    if eye_span == 0:
        return False
    lip_gap = abs(lower_lip[1] - upper_lip[1])
    return (lip_gap / abs(eye_span)) > threshold_ratio


def compute_crop_box(
    landmarks: list[Point],
    image_width: int,
    image_height: int,
    margin: float = 0.2,
) -> tuple[int, int, int, int]:
    """Bounding box of `landmarks` expanded by `margin` on each side, clamped
    to the image bounds. Returns (left, top, right, bottom)."""
    xs = [p[0] for p in landmarks]
    ys = [p[1] for p in landmarks]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    width, height = right - left, bottom - top
    left -= width * margin
    right += width * margin
    top -= height * margin
    bottom += height * margin
    return (
        max(0, int(left)),
        max(0, int(top)),
        min(image_width, int(right)),
        min(image_height, int(bottom)),
    )


def validate_and_align(source_image_path: str, target_state: FaceState) -> "np.ndarray":
    """Validate that the photo at `source_image_path` matches `target_state`'s
    gaze/expression requirements and return it cropped to the face.

    Raises ValueError if no face is found or the geometry doesn't match.
    """
    import cv2
    import mediapipe as mp
    import numpy as np

    image = cv2.imread(source_image_path)
    if image is None:
        raise ValueError(f"Could not read image: {source_image_path!r}")
    height, width = image.shape[:2]
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1) as face_mesh:
        result = face_mesh.process(rgb)

    if not result.multi_face_landmarks:
        raise ValueError(f"No face detected in {source_image_path!r}")
    landmarks = result.multi_face_landmarks[0].landmark
    points = [(lm.x * width, lm.y * height) for lm in landmarks]

    nose_tip = points[_LANDMARK_NOSE_TIP]
    left_eye = points[_LANDMARK_LEFT_EYE_OUTER]
    right_eye = points[_LANDMARK_RIGHT_EYE_OUTER]

    gaze = estimate_gaze_direction(nose_tip, left_eye, right_eye)
    if gaze != target_state.gaze_direction:
        raise ValueError(
            f"{source_image_path!r} gaze {gaze} does not match required "
            f"{target_state.gaze_direction}"
        )

    if target_state.expression == "OUCH":
        upper_lip = points[_LANDMARK_UPPER_LIP]
        lower_lip = points[_LANDMARK_LOWER_LIP]
        if not is_mouth_open(upper_lip, lower_lip, left_eye, right_eye):
            raise ValueError(f"{source_image_path!r} mouth is not open, required for OUCH")

    left, top, right, bottom = compute_crop_box(points, width, height)
    aligned: np.ndarray = rgb[top:bottom, left:right]
    return aligned
