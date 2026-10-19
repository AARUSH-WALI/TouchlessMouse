"""Touchless Computer Control System - Geometry and Math Utilities."""

import math
from dataclasses import dataclass
from typing import List, Tuple, Union, Any
import numpy as np


@dataclass
class Point:
    x: float
    y: float
    z: float = 0.0


def _extract_xyz(p: Any) -> Tuple[float, float, float]:
    """
    Extracts (x, y, z) from Point dataclass, MediaPipe NormalizedLandmark,
    or tuple/list coordinate.
    """
    if hasattr(p, "x"):
        return float(p.x), float(p.y), float(getattr(p, "z", 0.0))
    elif isinstance(p, (tuple, list)):
        z = float(p[2]) if len(p) > 2 else 0.0
        return float(p[0]), float(p[1]), z
    raise TypeError(f"Unsupported point coordinate type: {type(p)}")


def _extract_xy(p: Any) -> Tuple[float, float]:
    """Extracts (x, y) from Point, NormalizedLandmark, or sequence."""
    if hasattr(p, "x"):
        return float(p.x), float(p.y)
    elif isinstance(p, (tuple, list)):
        return float(p[0]), float(p[1])
    raise TypeError(f"Unsupported point coordinate type: {type(p)}")


def euclidean_distance(p1: Any, p2: Any) -> float:
    """Calculates Euclidean distance between two 2D or 3D points."""
    x1, y1, z1 = _extract_xyz(p1)
    x2, y2, z2 = _extract_xyz(p2)
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def calculate_angle(a: Any, b: Any, c: Any) -> float:
    """
    Calculates angle at vertex b between vectors ba and bc in degrees (0 to 180).
    """
    ax, ay = _extract_xy(a)
    bx, by = _extract_xy(b)
    cx, cy = _extract_xy(c)

    ba = (ax - bx, ay - by)
    bc = (cx - bx, cy - by)

    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)

    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


def normalize_landmarks(landmarks) -> List[float]:
    """
    Normalizes 21 landmarks:
    1. Translates wrist (index 0) to origin (0, 0, 0).
    2. Scales by palm size (distance from wrist to middle finger MCP, index 9).
    3. Flattens into a 1D feature vector of length 63.
    """
    wrist_x, wrist_y, wrist_z = _extract_xyz(landmarks[0])
    mm_x, mm_y, mm_z = _extract_xyz(landmarks[9])

    palm_size = math.sqrt((mm_x - wrist_x) ** 2 + (mm_y - wrist_y) ** 2 + (mm_z - wrist_z) ** 2)
    scale = palm_size if palm_size > 1e-6 else 1.0

    features = []
    for lm in landmarks:
        lx, ly, lz = _extract_xyz(lm)
        features.append((lx - wrist_x) / scale)
        features.append((ly - wrist_y) / scale)
        features.append((lz - wrist_z) / scale)

    return features


def map_to_screen(landmark_x: float, landmark_y: float,
                  active_region: dict, screen_w: int, screen_h: int) -> Tuple[float, float]:
    """
    Maps normalized camera landmark (0.0 to 1.0) into screen pixel coordinates
    using the active region bounding box.
    """
    left = active_region.get("left", 0.15)
    right = active_region.get("right", 0.85)
    top = active_region.get("top", 0.15)
    bottom = active_region.get("bottom", 0.85)

    screen_x = np.interp(landmark_x, [left, right], [0, screen_w])
    screen_y = np.interp(landmark_y, [top, bottom], [0, screen_h])

    screen_x = float(np.clip(screen_x, 3, screen_w - 4))
    screen_y = float(np.clip(screen_y, 3, screen_h - 4))

    return screen_x, screen_y
