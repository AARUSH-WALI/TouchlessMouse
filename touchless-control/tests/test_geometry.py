import pytest
import math
from src.utils.geometry import Point, euclidean_distance, calculate_angle, normalize_landmarks, map_to_screen


class MockNormalizedLandmark:
    """Simulates MediaPipe's NormalizedLandmark (has .x, .y, .z but not subscriptable)."""
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def test_euclidean_distance_2d():
    p1 = Point(0.0, 0.0)
    p2 = Point(3.0, 4.0)
    assert math.isclose(euclidean_distance(p1, p2), 5.0)


def test_euclidean_distance_tuples():
    assert math.isclose(euclidean_distance((0.0, 0.0, 0.0), (1.0, 2.0, 2.0)), 3.0)


def test_euclidean_distance_mediapipe_landmarks():
    """Ensures NormalizedLandmark objects work without subscript errors."""
    lm1 = MockNormalizedLandmark(0.1, 0.2, 0.0)
    lm2 = MockNormalizedLandmark(0.4, 0.6, 0.0)
    assert math.isclose(euclidean_distance(lm1, lm2), 0.5)


def test_calculate_angle_right_angle():
    a = Point(0.0, 1.0)
    b = Point(0.0, 0.0)
    c = Point(1.0, 0.0)
    angle = calculate_angle(a, b, c)
    assert math.isclose(angle, 90.0, rel_tol=1e-3)


def test_calculate_angle_straight_line():
    a = Point(-1.0, 0.0)
    b = Point(0.0, 0.0)
    c = Point(1.0, 0.0)
    angle = calculate_angle(a, b, c)
    assert math.isclose(angle, 180.0, rel_tol=1e-3)


def test_normalize_landmarks_origin():
    # 21 synthetic landmarks where wrist is at (0.5, 0.5, 0.0) and middle MCP at (0.5, 0.7, 0.0)
    mock_lms = [MockNormalizedLandmark(0.5, 0.5, 0.0) for _ in range(21)]
    mock_lms[9] = MockNormalizedLandmark(0.5, 0.7, 0.0)  # palm size = 0.2

    features = normalize_landmarks(mock_lms)
    assert len(features) == 63
    # Wrist features (first 3) must be (0.0, 0.0, 0.0)
    assert math.isclose(features[0], 0.0)
    assert math.isclose(features[1], 0.0)
    assert math.isclose(features[2], 0.0)
    # Middle MCP normalized features should be (0.0, 1.0, 0.0)
    assert math.isclose(features[9 * 3], 0.0)
    assert math.isclose(features[9 * 3 + 1], 1.0, abs_tol=1e-5)
    assert math.isclose(features[9 * 3 + 2], 0.0)


def test_map_to_screen():
    active_region = {"left": 0.2, "right": 0.8, "top": 0.2, "bottom": 0.8}
    screen_w, screen_h = 1920, 1080

    # Center of active region should map to center of screen
    sx, sy = map_to_screen(0.5, 0.5, active_region, screen_w, screen_h)
    assert math.isclose(sx, 960, abs_tol=1.0)
    assert math.isclose(sy, 540, abs_tol=1.0)

    # Left-top edge of active region
    sx, sy = map_to_screen(0.2, 0.2, active_region, screen_w, screen_h)
    assert math.isclose(sx, 3.0, abs_tol=1.0)
    assert math.isclose(sy, 3.0, abs_tol=1.0)

    # Clamping outside active region (safeguarded away from 0,0 failsafe corner)
    sx, sy = map_to_screen(0.0, 1.0, active_region, screen_w, screen_h)
    assert sx == 3.0
    assert sy == screen_h - 4
