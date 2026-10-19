import pytest
from src.core.gesture_engine import GestureEngine


def test_pinch_hysteresis():
    """Pinch should not flicker when distance oscillates between on and off thresholds."""
    engine = GestureEngine({
        "gestures": {
            "pinch_on_threshold": 0.04,
            "pinch_off_threshold": 0.06
        }
    })

    # Initially above both -> no pinch
    assert engine.detect_pinch(0.08) is None

    # Drops below on-threshold -> pinch_start
    assert engine.detect_pinch(0.035) == "pinch_start"

    # Moves between 0.04 and 0.06 -> remains in pinch_hold!
    assert engine.detect_pinch(0.045) == "pinch_hold"
    assert engine.detect_pinch(0.055) == "pinch_hold"

    # Rises above off-threshold -> pinch_end
    assert engine.detect_pinch(0.065) == "pinch_end"

    # Moves back between 0.04 and 0.06 -> still released (no pinch)!
    assert engine.detect_pinch(0.055) is None


def test_click_cooldown():
    engine = GestureEngine({
        "gestures": {
            "click_cooldown_ms": 300
        }
    })

    # First click allowed
    assert engine.can_click() is True

    # Immediate second click blocked
    assert engine.can_click() is False


class DummyPt:
    def __init__(self, x=0.5, y=0.5, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def make_landmarks(index_y=0.2, thumb_x=0.3, thumb_y=0.5, middle_y=0.7, ring_y=0.7, pinky_y=0.7, wrist_x=0.5):
    lms = [DummyPt(0.5, 0.7) for _ in range(21)]
    lms[0] = DummyPt(wrist_x, 0.7)  # WRIST
    lms[1] = DummyPt(0.45, 0.65)   # THUMB_CMC
    lms[2] = DummyPt(0.42, 0.6)    # THUMB_MCP
    lms[4] = DummyPt(thumb_x, thumb_y)  # THUMB_TIP
    lms[5] = DummyPt(0.5, 0.45)    # INDEX_MCP
    lms[6] = DummyPt(0.5, 0.35)    # INDEX_PIP
    lms[8] = DummyPt(0.5, index_y) # INDEX_TIP
    lms[9] = DummyPt(0.55, 0.45)   # MIDDLE_MCP
    lms[10] = DummyPt(0.55, 0.55)  # MIDDLE_PIP
    lms[12] = DummyPt(0.55, middle_y) # MIDDLE_TIP
    lms[13] = DummyPt(0.6, 0.45)   # RING_MCP
    lms[14] = DummyPt(0.6, 0.55)   # RING_PIP
    lms[16] = DummyPt(0.6, ring_y) # RING_TIP
    lms[17] = DummyPt(0.65, 0.45)  # PINKY_MCP
    lms[18] = DummyPt(0.65, 0.55)  # PINKY_PIP
    lms[20] = DummyPt(0.65, pinky_y) # PINKY_TIP
    return lms


def test_swipe_detection():
    """Rapid horizontal wrist displacement triggers swipe."""
    engine = GestureEngine({})
    
    # Frame 1: Hand on left side
    lms1 = make_landmarks(wrist_x=0.3)
    engine.detect(lms1, timestamp=1.0)
    
    # Frame 2: 100ms later, hand moved significantly to right (dx = +0.15, dt = 0.1s -> vx = +1.5)
    lms2 = make_landmarks(wrist_x=0.45)
    gesture, meta = engine.detect(lms2, timestamp=1.1)
    assert gesture == "swipe_right"
    assert meta["action"] == "next_page"


def test_open_palm_hold_required():
    """Showing hand with all fingers extended must NOT pause immediately; requires deliberate hold."""
    engine = GestureEngine({})
    
    # Open palm landmarks (all extended, stationary)
    lms = make_landmarks(index_y=0.2, middle_y=0.2, ring_y=0.2, pinky_y=0.2, thumb_x=0.2, thumb_y=0.4)
    
    # Frame 1: Hand enters frame (timestamp = 0.0)
    gesture1, _ = engine.detect(lms, timestamp=0.0)
    assert gesture1 == "idle"  # MUST NOT pause on arrival!
    
    # Frame 2: 300ms later, still held
    gesture2, _ = engine.detect(lms, timestamp=0.3)
    assert gesture2 == "idle"
    
    # Frame 3: After 900ms (> 850ms hold duration), candidate becomes open_palm
    engine.detect(lms, timestamp=0.9)
    
    # Frame 4: Second frame confirms stable open_palm gesture
    gesture4, _ = engine.detect(lms, timestamp=0.95)
    assert gesture4 == "open_palm"


def test_l_shape_zoom():
    """L-shape gesture moving UP triggers zoom_in; moving DOWN triggers zoom_out."""
    engine = GestureEngine({})
    
    # L-Shape: Index UP (< 0.35 PIP), Thumb OUT, Middle/Ring/Pinky CURLED (> 0.55 PIP)
    # Step 1: establish baseline L-shape at index_y = 0.25
    lms1 = make_landmarks(index_y=0.25, thumb_x=0.2, thumb_y=0.5, middle_y=0.7, ring_y=0.7, pinky_y=0.7)
    g1, _ = engine.detect(lms1, timestamp=1.0)
    assert g1 == "zoom_ready"
    
    # Step 2: Hand moves UP (index_y drops from 0.25 to 0.18, dy = +0.07 > 0.018) after cooldown
    lms2 = make_landmarks(index_y=0.18, thumb_x=0.2, thumb_y=0.43, middle_y=0.63, ring_y=0.63, pinky_y=0.63)
    g2, _ = engine.detect(lms2, timestamp=1.25)
    assert g2 == "zoom_in"
    
    # Step 3: Hand moves DOWN (index_y rises from 0.18 to 0.27) after cooldown
    lms3 = make_landmarks(index_y=0.27, thumb_x=0.2, thumb_y=0.51, middle_y=0.71, ring_y=0.71, pinky_y=0.71)
    g3, _ = engine.detect(lms3, timestamp=1.55)
    assert g3 == "zoom_out"
