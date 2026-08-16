from hudface.geometry import compute_crop_box, estimate_gaze_direction, is_mouth_open
from hudface.parser import GAZE_CENTER, GAZE_LEFT, GAZE_RIGHT

LEFT_EYE = (80.0, 100.0)
RIGHT_EYE = (120.0, 100.0)


def test_centered_nose_is_center_gaze():
    nose = ((LEFT_EYE[0] + RIGHT_EYE[0]) / 2, 120.0)
    assert estimate_gaze_direction(nose, LEFT_EYE, RIGHT_EYE) == GAZE_CENTER


def test_nose_shifted_right_of_midpoint_is_right_gaze():
    nose = (115.0, 120.0)
    assert estimate_gaze_direction(nose, LEFT_EYE, RIGHT_EYE) == GAZE_RIGHT


def test_nose_shifted_left_of_midpoint_is_left_gaze():
    nose = (85.0, 120.0)
    assert estimate_gaze_direction(nose, LEFT_EYE, RIGHT_EYE) == GAZE_LEFT


def test_gaze_threshold_boundary_stays_center():
    # exactly at the threshold ratio should not tip into Right/Left
    eye_span = RIGHT_EYE[0] - LEFT_EYE[0]
    midpoint_x = (LEFT_EYE[0] + RIGHT_EYE[0]) / 2
    nose = (midpoint_x + 0.15 * eye_span, 120.0)
    assert estimate_gaze_direction(nose, LEFT_EYE, RIGHT_EYE) == GAZE_CENTER


def test_zero_eye_span_defaults_to_center():
    same_point = (100.0, 100.0)
    assert estimate_gaze_direction((100.0, 120.0), same_point, same_point) == GAZE_CENTER


def test_wide_lip_gap_is_mouth_open():
    upper_lip = (100.0, 140.0)
    lower_lip = (100.0, 150.0)
    assert is_mouth_open(upper_lip, lower_lip, LEFT_EYE, RIGHT_EYE) is True


def test_closed_lips_is_not_mouth_open():
    upper_lip = (100.0, 140.0)
    lower_lip = (100.0, 140.5)
    assert is_mouth_open(upper_lip, lower_lip, LEFT_EYE, RIGHT_EYE) is False


def test_zero_eye_span_mouth_check_defaults_to_closed():
    same_point = (100.0, 100.0)
    assert is_mouth_open((100.0, 140.0), (100.0, 160.0), same_point, same_point) is False


def test_compute_crop_box_adds_margin_and_clamps_to_image():
    landmarks = [(50.0, 50.0), (150.0, 150.0)]
    left, top, right, bottom = compute_crop_box(
        landmarks, image_width=1000, image_height=1000, margin=0.2
    )
    assert (left, top, right, bottom) == (30, 30, 170, 170)


def test_compute_crop_box_clamps_negative_and_oversized_bounds():
    landmarks = [(5.0, 5.0), (95.0, 95.0)]
    left, top, right, bottom = compute_crop_box(
        landmarks, image_width=100, image_height=100, margin=0.5
    )
    assert left == 0
    assert top == 0
    assert right == 100
    assert bottom == 100
