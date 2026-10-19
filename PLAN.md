# Touchless Computer Control System — Master Build Plan

> **Purpose of this document**: This is a deeply-analyzed, self-contained build plan derived from the original `Touchless_Control_Build_Plan.pdf`. It contains every detail, algorithm, data structure, API call, file path, threshold value, and implementation note needed to build the entire product from scratch. **Any developer or AI coding agent reading only this document should be able to implement the full system without any additional context.**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Deep Dive](#2-architecture-deep-dive)
3. [Technology Stack — Exact Versions & Rationale](#3-technology-stack)
4. [Repository Structure — Annotated](#4-repository-structure)
5. [Data Structures & Configuration Schemas](#5-data-structures--configuration-schemas)
6. [Phase 1: Setup & Camera](#6-phase-1-setup--camera)
7. [Phase 2: Hand Tracking](#7-phase-2-hand-tracking)
8. [Phase 3: Cursor Movement](#8-phase-3-cursor-movement)
9. [Phase 4: Click & Scroll Gestures](#9-phase-4-click--scroll-gestures)
10. [Phase 5: Polish & Demo](#10-phase-5-polish--demo)
11. [Phase 6: Refactor & Settings Foundation](#11-phase-6-refactor--settings-foundation)
12. [Phase 7: Custom Gesture Training](#12-phase-7-custom-gesture-training)
13. [Phase 8: Voice Commands](#13-phase-8-voice-commands)
14. [Phase 9: Presentation Mode](#14-phase-9-presentation-mode)
15. [Phase 10: Gaming Mode](#15-phase-10-gaming-mode)
16. [Phase 11: Accessibility Settings](#16-phase-11-accessibility-settings)
17. [Phase 12: Packaging & Release](#17-phase-12-packaging--release)
18. [Algorithm Details & Pseudocode](#18-algorithm-details--pseudocode)
19. [Testing Strategy](#19-testing-strategy)
20. [Risk Matrix & Mitigations](#20-risk-matrix--mitigations)
21. [Performance Optimization Guide](#21-performance-optimization-guide)
22. [Licensing & Monetisation](#22-licensing--monetisation)
23. [Future Roadmap](#23-future-roadmap)
24. [Build Commands Reference](#24-build-commands-reference)
25. [Phase-by-Phase Prompts for AI Agents](#25-phase-by-phase-prompts-for-ai-agents)

---

## 1. Project Overview

### What We're Building
A **desktop application** that lets users control their computer entirely through **hand gestures** and **voice commands** — no mouse or keyboard needed. The system uses a standard webcam for hand tracking via MediaPipe, and a microphone for offline voice recognition via Vosk.

### Two-Stage Delivery

| Stage | Scope | Timeline | Deliverable |
|-------|-------|----------|-------------|
| **Minor Project** | Webcam hand tracking → cursor control, pinch clicks, scroll, drag | ~2 weeks (Phases 1-5) | Working demo: control browser, click links, scroll, drag windows |
| **Major Project** | Custom gestures, voice commands, presentation mode, gaming mode, accessibility, installable app | ~8 weeks (Phases 1-12) | Full touchless control suite packaged as .exe |

### Target Platform
- **Primary**: Windows 10/11
- **Stretch**: macOS, Linux (different cursor control permissions)

### Core Value Propositions
1. **Accessibility**: Users with motor disabilities can control their computer
2. **Presentation**: Touch-free slide control with laser pointer overlay
3. **Gaming**: Map gestures to game inputs
4. **Hygiene/Convenience**: Touchless control in labs, kitchens, etc.
5. **Privacy**: Everything runs locally — no cloud, no data upload

---

## 2. Architecture Deep Dive

### System Pipeline (Data Flow)

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Webcam      │────>│  Camera      │────>│  Hand Tracker  │────>│  Gesture     │────>│  Mode       │
│  (30 FPS)    │     │  Thread      │     │  (MediaPipe)   │     │  Engine      │     │  Manager    │
└─────────────┘     │  (Queue)     │     │  21 landmarks  │     │  Rule-based  │     │  Normal/    │
                    └──────────────┘     └────────────────┘     │  or ML       │     │  Present/   │
                                                                 └──────────────┘     │  Gaming     │
                                                                                      └──────┬──────┘
                                                                                             │
┌─────────────┐     ┌──────────────┐                                                         │
│  Microphone  │────>│  Voice       │────────────────────────────────────────────────────────>│
│              │     │  Thread      │                                                         v
└─────────────┘     │  (Vosk)      │                                                  ┌──────────────┐
                    └──────────────┘                                                  │  Action      │
                                                                                      │  Layer       │
┌─────────────┐                                                                       │  (PyAutoGUI) │
│  CustomTk    │<──── Shared State Object + Event Queue ─────────────────────────────>└──────────────┘
│  UI Thread   │
└─────────────┘
```

### Threading Model

| Thread | Responsibility | Communication |
|--------|---------------|---------------|
| **Main Thread** | CustomTkinter UI, event loop | Reads shared state, processes event queue |
| **Camera Thread** | Captures frames at 30 FPS | Pushes frames to `queue.Queue(maxsize=2)` |
| **Processing Thread** | Runs MediaPipe, gesture engine, action dispatch | Pulls from camera queue, updates shared state |
| **Voice Thread** | Listens via Vosk with restricted grammar | Sends recognized commands to event queue |

### Critical Design Rules
1. **Never block the UI thread** — all heavy work in background threads
2. **Shared state** via a thread-safe object (use `threading.Lock`)
3. **Event queue** for inter-thread communication (`queue.Queue`)
4. **All thresholds in JSON config** — no magic numbers in code
5. **Core logic separate from UI** — testable without a camera

---

## 3. Technology Stack

### Exact Dependencies (pin these in `requirements.txt`)

```
mediapipe>=0.10.9
opencv-python>=4.8.0
pyautogui>=0.9.54
pynput>=1.7.6
numpy>=1.24.0
scikit-learn>=1.3.0
joblib>=1.3.0
vosk>=0.3.45
customtkinter>=5.2.0
Pillow>=10.0.0
pytest>=7.4.0
sounddevice>=0.4.6
```

### Why Each Tool

| Tool | Purpose | Why This One |
|------|---------|-------------|
| **MediaPipe Tasks API (HandLandmarker)** | Hand detection + 21 landmarks per hand | State-of-art accuracy, runs on CPU, Apache 2.0. Use `hand_landmarker.task` model file — NOT the legacy `mp.solutions.hands` |
| **OpenCV** | Camera capture, frame processing, drawing | Industry standard, fast, Apache 2.0 |
| **PyAutoGUI** | Mouse movement, clicks, keyboard simulation | Simple API, has FAILSAFE feature. Set `pyautogui.PAUSE = 0` and use `moveTo(..., _pause=False)` for low latency |
| **pynput** | Keyboard listener (hotkeys), fallback mouse control | Better for keyboard listening than PyAutoGUI |
| **scikit-learn** | Custom gesture classifier (RandomForest or MLP) | Easy, no GPU needed, BSD license |
| **Vosk** | Offline speech recognition | Fully offline, restricted grammar support, Apache 2.0 |
| **CustomTkinter** | Modern settings UI | MIT license, looks modern unlike vanilla tkinter. NOT PyQt (GPL/paid) |
| **PyInstaller** | Package as .exe | GPL with bootloader exception — safe for distribution |

### Tools to AVOID
- **PyQt** — GPL or paid commercial license
- **Google Web Speech API** — rate-limited, not for commercial use
- **`mp.solutions.hands`** — Legacy MediaPipe API, use Tasks API instead
- **Copied code from random GitHub repos** — license issues

---

## 4. Repository Structure

```
touchless-control/
├── README.md                          # Install steps, demo video link, usage guide
├── requirements.txt                   # Pinned dependency versions
├── pyproject.toml                     # Project metadata, build config
├── THIRD_PARTY_LICENSES               # License text for all dependencies
│
├── config/
│   ├── default_config.json            # All thresholds, regions, smoothing params
│   ├── gestures.json                  # Gesture name -> action mapping
│   └── profiles/
│       ├── normal.json                # Default mode settings
│       ├── presentation.json          # Presentation mode overrides
│       ├── gaming.json                # Gaming mode (lower latency settings)
│       └── accessibility.json         # High sensitivity, dwell click, etc.
│
├── models/
│   ├── hand_landmarker.task           # Downloaded from MediaPipe model hub
│   ├── vosk-model-small-en-us/        # Downloaded from Vosk website
│   └── custom_gestures.joblib         # Trained by user in-app
│
├── src/
│   ├── main.py                        # Entry point — initializes everything
│   ├── core/
│   │   ├── __init__.py
│   │   ├── camera.py                  # Webcam capture thread
│   │   ├── hand_tracker.py            # MediaPipe Tasks API wrapper
│   │   ├── smoothing.py               # One Euro Filter + exponential smoothing
│   │   ├── gesture_engine.py          # Rule-based gesture detection (Minor)
│   │   ├── ml_gesture.py              # ML-based custom gesture classifier (Major)
│   │   ├── actions.py                 # Mouse/keyboard/scroll action execution
│   │   ├── mode_manager.py            # Normal / Presentation / Gaming mode switching
│   │   ├── voice.py                   # Vosk voice command listener thread
│   │   └── config.py                  # Load/save JSON config, merge defaults
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py                     # CustomTkinter main window
│   │   ├── settings_panel.py          # Sliders for sensitivity, smoothing, etc.
│   │   ├── gesture_trainer.py         # UI for recording + training custom gestures
│   │   └── overlay.py                 # Transparent topmost window (status, laser pointer)
│   └── utils/
│       ├── __init__.py
│       ├── geometry.py                # Euclidean distance, angles, landmark normalization
│       └── logger.py                  # File-based logging setup
│
├── tests/
│   ├── __init__.py
│   ├── test_geometry.py               # Unit tests for distance/angle calculations
│   ├── test_smoothing.py              # Unit tests for filter algorithms
│   ├── test_gesture_engine.py         # Tests with recorded landmark samples
│   └── fixtures/                      # Saved landmark data for testing without camera
│       └── sample_landmarks.json
│
├── scripts/
│   ├── collect_data.py                # Standalone gesture data collection
│   ├── train_model.py                 # Standalone model training script
│   └── download_models.py            # Download MediaPipe + Vosk models
│
└── docs/
    ├── architecture.md                # System design documentation
    └── user_guide.md                  # End-user guide with screenshots
```

---

## 5. Data Structures & Configuration Schemas

### 5.1 `default_config.json` — Complete Schema

```json
{
  "camera": {
    "device_index": 0,
    "width": 640,
    "height": 480,
    "fps_cap": 30,
    "mirror": true,
    "process_every_n_frames": 1
  },
  "hand_tracker": {
    "model_path": "models/hand_landmarker.task",
    "num_hands": 1,
    "min_detection_confidence": 0.7,
    "min_tracking_confidence": 0.5,
    "running_mode": "VIDEO"
  },
  "cursor": {
    "active_region": {
      "left": 0.15,
      "right": 0.85,
      "top": 0.15,
      "bottom": 0.85
    },
    "smoothing_type": "one_euro",
    "smoothing_factor": 5,
    "one_euro": {
      "min_cutoff": 1.0,
      "beta": 0.007,
      "d_cutoff": 1.0
    },
    "pointer_landmark": 8
  },
  "gestures": {
    "pinch_on_threshold": 0.04,
    "pinch_off_threshold": 0.06,
    "scroll_sensitivity": 5,
    "click_cooldown_ms": 300,
    "consecutive_frames_required": 3,
    "drag_hold_frames": 5,
    "fist_threshold": 0.15,
    "open_palm_threshold": 0.25
  },
  "ml_gesture": {
    "model_path": "models/custom_gestures.joblib",
    "confidence_threshold": 0.85,
    "stability_frames": 5,
    "samples_per_gesture": 250
  },
  "voice": {
    "enabled": false,
    "model_path": "models/vosk-model-small-en-us",
    "sample_rate": 16000,
    "push_to_talk": false,
    "push_to_talk_key": "ctrl"
  },
  "modes": {
    "default": "normal",
    "available": ["normal", "presentation", "gaming"]
  },
  "accessibility": {
    "dwell_click_enabled": false,
    "dwell_time_ms": 1500,
    "one_hand_mode": "right",
    "left_handed": false,
    "tremor_filter": false,
    "tremor_dead_zone": 0.02,
    "high_contrast_ui": false,
    "large_text": false,
    "gesture_hold_time_ms": 500,
    "gesture_cooldown_ms": 1000,
    "voice_only_mode": false,
    "gesture_only_mode": false
  },
  "ui": {
    "show_preview": true,
    "show_landmarks": true,
    "show_fps": true,
    "show_gesture_label": true,
    "overlay_enabled": true,
    "overlay_opacity": 0.7
  },
  "failsafe": {
    "enabled": true,
    "hotkey": "F8",
    "pyautogui_failsafe": true
  },
  "logging": {
    "level": "INFO",
    "file": "touchless_control.log",
    "max_bytes": 5242880,
    "backup_count": 3
  }
}
```

### 5.2 `gestures.json` — Gesture-to-Action Mapping

```json
{
  "built_in": {
    "index_up": {
      "action": "move_cursor",
      "description": "Move cursor with index finger"
    },
    "thumb_index_pinch": {
      "action": "left_click",
      "description": "Left click (hold for drag)"
    },
    "thumb_middle_pinch": {
      "action": "right_click",
      "description": "Right click"
    },
    "index_middle_up": {
      "action": "scroll",
      "description": "Scroll up/down with hand movement"
    },
    "open_palm": {
      "action": "pause_tracking",
      "description": "Pause tracking (safety)"
    },
    "fist": {
      "action": "idle",
      "description": "No action"
    }
  },
  "custom": {
    "thumbs_up": {
      "action": "key_press",
      "action_params": {"key": "space"},
      "description": "User-trained: play/pause"
    }
  }
}
```

### 5.3 Action Types Schema

```json
{
  "action_types": {
    "move_cursor": {},
    "left_click": {},
    "right_click": {},
    "double_click": {},
    "scroll": {"direction": "up|down", "amount": 3},
    "drag": {},
    "key_press": {"key": "string", "modifiers": ["ctrl", "shift", "alt"]},
    "hotkey": {"keys": ["ctrl", "c"]},
    "open_app": {"path": "C:\\...\\app.exe"},
    "run_shortcut": {"command": "string"},
    "pause_tracking": {},
    "resume_tracking": {},
    "switch_mode": {"mode": "normal|presentation|gaming"},
    "idle": {}
  }
}
```

### 5.4 Gaming Profile Schema (`profiles/gaming.json`)

```json
{
  "name": "Gaming",
  "description": "Low-latency gaming controls",
  "camera_overrides": {
    "width": 320,
    "height": 240,
    "fps_cap": 60,
    "process_every_n_frames": 1
  },
  "cursor_overrides": {
    "smoothing_factor": 2,
    "one_euro": {
      "min_cutoff": 2.0,
      "beta": 0.01
    }
  },
  "gesture_map": {
    "hand_left": {"action": "key_press", "action_params": {"key": "a"}},
    "hand_right": {"action": "key_press", "action_params": {"key": "d"}},
    "hand_up": {"action": "key_press", "action_params": {"key": "w"}},
    "hand_down": {"action": "key_press", "action_params": {"key": "s"}},
    "thumb_index_pinch": {"action": "key_press", "action_params": {"key": "space"}, "description": "Jump"},
    "fist": {"action": "left_click", "description": "Attack"}
  },
  "demo_games": ["browser_dino_runner", "simple_racing"]
}
```

### 5.5 Presentation Profile Schema (`profiles/presentation.json`)

```json
{
  "name": "Presentation",
  "description": "Touch-free presentation control",
  "gesture_map": {
    "swipe_right": {"action": "key_press", "action_params": {"key": "right"}, "description": "Next slide"},
    "swipe_left": {"action": "key_press", "action_params": {"key": "left"}, "description": "Previous slide"},
    "index_up": {"action": "laser_pointer", "description": "On-screen laser dot"},
    "open_palm_hold": {"action": "key_press", "action_params": {"key": "b"}, "description": "Black screen"},
    "fist": {"action": "key_press", "action_params": {"key": "escape"}, "description": "End show"},
    "pinch_zoom": {"action": "zoom", "description": "Zoom in/out (optional)"}
  },
  "overlay": {
    "laser_color": [255, 0, 0],
    "laser_radius": 10,
    "laser_glow": true
  }
}
```

### 5.6 MediaPipe Landmark Reference

The 21 hand landmarks returned by MediaPipe, referenced throughout the code:

```
Landmark Index | Name                 | Used For
0              | WRIST                | Origin for normalization, hand size reference
1              | THUMB_CMC            | Thumb base
2              | THUMB_MCP            | Thumb joint
3              | THUMB_IP             | Thumb joint
4              | THUMB_TIP            | Pinch detection (distance to index tip)
5              | INDEX_FINGER_MCP     | Finger-up detection base
6              | INDEX_FINGER_PIP     | Finger curl detection
7              | INDEX_FINGER_DIP     | Finger curl detection
8              | INDEX_FINGER_TIP     | ***PRIMARY POINTER*** for cursor movement
9              | MIDDLE_FINGER_MCP    | Hand size reference (distance from wrist)
10             | MIDDLE_FINGER_PIP    | Finger curl detection
11             | MIDDLE_FINGER_DIP    | Finger curl detection
12             | MIDDLE_FINGER_TIP    | Right-click pinch detection
13             | RING_FINGER_MCP      | Fist/palm detection
14             | RING_FINGER_PIP      | Finger curl detection
15             | RING_FINGER_DIP      | Finger curl detection
16             | RING_FINGER_TIP      | Fist/palm detection
17             | PINKY_MCP            | Fist/palm detection
18             | PINKY_PIP            | Finger curl detection
19             | PINKY_DIP            | Finger curl detection
20             | PINKY_TIP            | Fist/palm detection
```

---

## 6. Phase 1: Setup & Camera

### Duration: Day 1-2

### Tasks
1. Create the repository with the folder structure from Section 4
2. Set up Python virtual environment (3.10-3.12)
3. Create `requirements.txt` with pinned versions
4. Implement `src/core/camera.py` — webcam capture thread
5. Implement `src/main.py` — basic entry point showing preview

### `camera.py` Implementation Details

```python
# Key implementation points:

# 1. Use threading for non-blocking capture
import threading
import queue
import cv2

class CameraThread(threading.Thread):
    def __init__(self, device_index=0, width=640, height=480, fps_cap=30, mirror=True):
        super().__init__(daemon=True)  # Daemon so it dies with main thread
        self.cap = cv2.VideoCapture(device_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps_cap)
        self.frame_queue = queue.Queue(maxsize=2)  # Drop old frames
        self.mirror = mirror
        self.running = True

    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            if self.mirror:
                frame = cv2.flip(frame, 1)  # Mirror horizontally
            # Drop old frames to avoid lag
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(frame)

    def get_frame(self):
        """Non-blocking frame retrieval"""
        try:
            return self.frame_queue.get(timeout=0.03)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        self.cap.release()
```

### Error Handling
- Check `self.cap.isOpened()` — show error if no camera
- Handle `camera in use by another app` gracefully
- Log camera properties (actual resolution, FPS) on startup

### Done When
- A mirrored live preview runs at **25+ FPS**
- Press Q to quit
- FPS counter displayed on frame

---

## 7. Phase 2: Hand Tracking

### Duration: Day 3-4

### Tasks
1. Download `hand_landmarker.task` from MediaPipe model hub
2. Create `scripts/download_models.py` to automate model downloads
3. Implement `src/core/hand_tracker.py` — MediaPipe Tasks API wrapper
4. Draw 21 landmarks on preview

### `hand_tracker.py` — Critical Implementation

```python
# USE the Tasks API, NOT the legacy mp.solutions.hands!
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HandTracker:
    def __init__(self, model_path, num_hands=1,
                 min_detection_confidence=0.7,
                 min_tracking_confidence=0.5):
        
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,  # or LIVE_STREAM
            num_hands=num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame, timestamp_ms):
        """
        Args:
            frame: BGR numpy array from OpenCV
            timestamp_ms: monotonically increasing timestamp

        Returns:
            List of hand results, each containing 21 NormalizedLandmarks
            Landmarks are normalized 0-1 relative to image dimensions
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self.detector.detect_for_video(mp_image, timestamp_ms)
        return result.hand_landmarks  # List[List[NormalizedLandmark]]
```

### Landmark Drawing

```python
# Draw connections and landmarks on frame
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),    # Thumb
    (0,5),(5,6),(6,7),(7,8),    # Index
    (0,9),(9,10),(10,11),(11,12), # Middle
    (0,13),(13,14),(14,15),(15,16), # Ring
    (0,17),(17,18),(18,19),(19,20), # Pinky
    (5,9),(9,13),(13,17)        # Palm
]

def draw_landmarks(frame, landmarks, width, height):
    for connection in HAND_CONNECTIONS:
        start = landmarks[connection[0]]
        end = landmarks[connection[1]]
        cv2.line(frame,
                 (int(start.x * width), int(start.y * height)),
                 (int(end.x * width), int(end.y * height)),
                 (0, 255, 0), 2)
    for lm in landmarks:
        cv2.circle(frame,
                   (int(lm.x * width), int(lm.y * height)),
                   5, (0, 0, 255), -1)
```

### Done When
- Landmarks follow one hand reliably in normal indoor light
- Landmarks visible on the preview window

---

## 8. Phase 3: Cursor Movement

### Duration: Day 5-7

### Tasks
1. Implement `src/utils/geometry.py` — distance/angle utilities
2. Implement `src/core/smoothing.py` — One Euro Filter
3. Map index fingertip (landmark 8) to screen coordinates
4. Implement active region mapping

### Screen Mapping Algorithm

```python
import numpy as np

def map_to_screen(landmark_x, landmark_y, config, screen_w, screen_h):
    """
    Map normalized landmark coordinates to screen pixels.
    
    Active region defines a rectangle in normalized camera space.
    Only hand movement within this region maps to the full screen.
    This prevents users from needing to reach frame edges.
    """
    region = config['cursor']['active_region']

    # Interpolate from active region to screen coordinates
    screen_x = np.interp(landmark_x,
                          [region['left'], region['right']],
                          [0, screen_w])
    screen_y = np.interp(landmark_y,
                          [region['top'], region['bottom']],
                          [0, screen_h])

    # Clamp to screen bounds
    screen_x = np.clip(screen_x, 0, screen_w - 1)
    screen_y = np.clip(screen_y, 0, screen_h - 1)

    return screen_x, screen_y
```

### One Euro Filter (Critical for Smooth Cursor)

```python
import math
import time

class OneEuroFilter:
    """
    Attempt to minimize jitter while keeping low latency.
    - At low speed: heavy smoothing (removes jitter)
    - At high speed: light smoothing (reduces lag)

    Parameters:
        min_cutoff: Minimum cutoff frequency (lower = more smoothing at rest)
                    Start with 1.0, decrease for more smoothing
        beta:       Speed coefficient (higher = less lag during fast movement)
                    Start with 0.007, increase if cursor feels laggy
        d_cutoff:   Cutoff for derivative estimation
                    Usually leave at 1.0
    """
    def __init__(self, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _smoothing_factor(self, t_e, cutoff):
        r = 2 * math.pi * cutoff * t_e
        return r / (r + 1)

    def __call__(self, x, t=None):
        if t is None:
            t = time.monotonic()

        if self.t_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x

        t_e = t - self.t_prev  # Time elapsed
        if t_e <= 0:
            return self.x_prev

        # Estimate derivative
        a_d = self._smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev

        # Adaptive cutoff
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        # Filter
        a = self._smoothing_factor(t_e, cutoff)
        x_hat = a * x + (1 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat
```

### Exponential Moving Average (Simpler Fallback)

```python
def exponential_smooth(new_val, prev_val, factor):
    """
    smoothed = prev + (new - prev) / factor
    Higher factor = more smoothing (but more lag)
    Start with factor=5, adjust based on feel
    """
    return prev_val + (new_val - prev_val) / factor
```

### PyAutoGUI Setup

```python
import pyautogui

# CRITICAL performance settings
pyautogui.PAUSE = 0              # Remove default 0.1s pause between actions
pyautogui.FAILSAFE = True        # Moving cursor to corner (0,0) aborts — KEEP THIS

# Move cursor without pause
pyautogui.moveTo(screen_x, screen_y, _pause=False)
```

### Done When
- Cursor moves smoothly with **no visible shaking** while hand is still
- Cursor follows hand movement naturally (mirrored)
- Active region makes it comfortable (no need to reach frame edges)

---

## 9. Phase 4: Click & Scroll Gestures

### Duration: Day 8-11

### Tasks
1. Implement `src/utils/geometry.py` — full utility functions
2. Implement `src/core/gesture_engine.py` — rule-based detection
3. Implement `src/core/actions.py` — action execution
4. Add hysteresis, cooldown, and consecutive-frame checks

### Gesture Detection — Rule-Based

```python
# All distances are NORMALIZED by hand size
# Hand size = distance from WRIST (0) to MIDDLE_FINGER_MCP (9)

def get_hand_size(landmarks):
    """Reference distance for normalization."""
    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    return euclidean_distance(wrist, middle_mcp)

def normalized_distance(landmarks, idx_a, idx_b):
    """Distance between two landmarks, normalized by hand size."""
    raw = euclidean_distance(landmarks[idx_a], landmarks[idx_b])
    return raw / get_hand_size(landmarks)

def is_finger_up(landmarks, finger_tip, finger_pip):
    """A finger is 'up' if the tip is above (lower y) the PIP joint."""
    return landmarks[finger_tip].y < landmarks[finger_pip].y
```

### Gesture Rules Table

| Gesture | Detection Rule | Action |
|---------|---------------|--------|
| **Index finger up only** | Index tip (8) above PIP (6), other fingers curled (tips below their PIPs) | `move_cursor` |
| **Thumb-index pinch** | `normalized_distance(4, 8) < pinch_on_threshold` (0.04) | `left_click` |
| **Thumb-index pinch release** | `normalized_distance(4, 8) > pinch_off_threshold` (0.06) | Release drag |
| **Thumb-middle pinch** | `normalized_distance(4, 12) < pinch_on_threshold` | `right_click` |
| **Index+middle up** | Both index (8) and middle (12) tips above PIPs, others curled | `scroll` (direction from hand y-movement) |
| **Open palm** | All 5 fingertips above their PIPs, fingers spread > `open_palm_threshold` | `pause_tracking` |
| **Fist** | All fingertips below their PIPs, all close to palm center < `fist_threshold` | `idle` |

### Hysteresis (Prevent Accidental Double Clicks)

```python
class GestureEngine:
    def __init__(self, config):
        self.pinch_on = config['gestures']['pinch_on_threshold']   # 0.04
        self.pinch_off = config['gestures']['pinch_off_threshold'] # 0.06
        self.is_pinching = False
        self.cooldown_ms = config['gestures']['click_cooldown_ms'] # 300
        self.last_click_time = 0
        self.consecutive_frames = {}  # gesture_name -> frame_count
        self.required_frames = config['gestures']['consecutive_frames_required']  # 3

    def detect_pinch(self, normalized_dist):
        """
        Hysteresis: different on/off thresholds prevent bouncing.
        - Pinch ON when distance drops below 0.04
        - Pinch OFF when distance rises above 0.06
        - This 0.02 gap prevents rapid on/off/on/off flickering
        """
        if not self.is_pinching and normalized_dist < self.pinch_on:
            self.is_pinching = True
            return "pinch_start"
        elif self.is_pinching and normalized_dist > self.pinch_off:
            self.is_pinching = False
            return "pinch_end"
        return "pinch_hold" if self.is_pinching else None

    def check_stability(self, gesture_name):
        """Require N consecutive frames with same gesture before firing."""
        if gesture_name not in self.consecutive_frames:
            self.consecutive_frames = {gesture_name: 1}
            return False
        self.consecutive_frames[gesture_name] += 1
        return self.consecutive_frames[gesture_name] >= self.required_frames

    def check_cooldown(self):
        """Prevent clicks firing too rapidly."""
        now = time.time() * 1000
        if now - self.last_click_time < self.cooldown_ms:
            return False
        self.last_click_time = now
        return True
```

### Scroll Implementation

```python
def handle_scroll(self, landmarks, prev_y):
    """
    When index + middle fingers are up:
    Track the vertical hand movement and convert to scroll events.
    """
    current_y = (landmarks[8].y + landmarks[12].y) / 2  # Average of tips
    if prev_y is not None:
        delta = (prev_y - current_y) * self.scroll_sensitivity
        if abs(delta) > 0.5:  # Dead zone
            pyautogui.scroll(int(delta))
    return current_y
```

### Drag Implementation

```python
def handle_drag(self, pinch_state, screen_x, screen_y):
    """
    Pinch and hold = drag.
    - pinch_start: mouseDown
    - pinch_hold: moveTo (drag)
    - pinch_end: mouseUp
    """
    if pinch_state == "pinch_start":
        pyautogui.mouseDown()
    elif pinch_state == "pinch_hold":
        pyautogui.moveTo(screen_x, screen_y, _pause=False)
    elif pinch_state == "pinch_end":
        pyautogui.mouseUp()
```

### Done When
- User can **open a browser**, **click links**, **scroll a page**, and **drag a window** using only gestures
- No accidental double-clicks
- Smooth transitions between gesture states

---

## 10. Phase 5: Polish & Demo

### Duration: Day 12-14

### Tasks
1. Add on-screen status text (current gesture name, FPS)
2. Move all magic numbers to `config/default_config.json`
3. Implement `src/core/config.py` for config loading/saving
4. Add failsafe hotkey (F8 to pause/quit)
5. Create README with install steps + demo video
6. Basic error handling throughout

### Config Manager

```python
import json
import os
import copy

class ConfigManager:
    def __init__(self, config_path='config/default_config.json'):
        self.config_path = config_path
        self.defaults = self._load_defaults()
        self.config = copy.deepcopy(self.defaults)

    def _load_defaults(self):
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def get(self, key_path, default=None):
        """Get nested config value: 'cursor.smoothing_factor'"""
        keys = key_path.split('.')
        val = self.config
        for key in keys:
            val = val.get(key, default)
            if val is default:
                break
        return val

    def set(self, key_path, value):
        """Set nested config value and save."""
        keys = key_path.split('.')
        d = self.config
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def save(self, path=None):
        with open(path or self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def load_profile(self, profile_path):
        """Load a profile and merge overrides into config."""
        with open(profile_path, 'r') as f:
            profile = json.load(f)
        # Deep merge overrides
        for key in ['camera_overrides', 'cursor_overrides']:
            if key in profile:
                base_key = key.replace('_overrides', '')
                self._deep_merge(self.config[base_key], profile[key])
        if 'gesture_map' in profile:
            self.config['active_gesture_map'] = profile['gesture_map']
```

### Failsafe Implementation

```python
from pynput import keyboard

class FailsafeManager:
    def __init__(self, hotkey='F8', callback=None):
        self.hotkey = hotkey
        self.callback = callback
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.daemon = True
        self.listener.start()

    def _on_press(self, key):
        try:
            if key == keyboard.Key.f8:
                if self.callback:
                    self.callback()
        except AttributeError:
            pass
```

### Done When
- A **3-minute demo works without crashing**
- FPS and gesture labels visible on screen
- Config file controls all behavior
- F8 pauses/quits cleanly

---

## 11. Phase 6: Refactor & Settings Foundation

### Duration: Week 3

### Tasks
1. Move ALL hard-coded thresholds into config JSON
2. Build CustomTkinter main window with:
   - Start/Stop tracking button
   - Camera preview embedded in window
   - Status bar (FPS, active gesture, mode)
3. Implement mode manager skeleton (Normal mode only for now)
4. Wire up shared state between UI and core threads

### CustomTkinter Main Window Structure

```python
import customtkinter as ctk
from PIL import Image, ImageTk

class TouchlessApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Touchless Control")
        self.geometry("1000x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Layout: sidebar + main area
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y", padx=5, pady=5)

        self.main_area = ctk.CTkFrame(self)
        self.main_area.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Sidebar buttons
        self.btn_start = ctk.CTkButton(self.sidebar, text="Start", command=self.toggle_tracking)
        self.btn_settings = ctk.CTkButton(self.sidebar, text="Settings", command=self.open_settings)
        self.btn_train = ctk.CTkButton(self.sidebar, text="Train Gesture", command=self.open_trainer)

        # Mode selector
        self.mode_var = ctk.StringVar(value="Normal")
        self.mode_menu = ctk.CTkOptionMenu(self.sidebar, values=["Normal", "Presentation", "Gaming"],
                                            variable=self.mode_var, command=self.switch_mode)

        # Camera preview (Label with updating image)
        self.preview_label = ctk.CTkLabel(self.main_area, text="")

        # Status bar
        self.status_frame = ctk.CTkFrame(self.main_area)
        self.fps_label = ctk.CTkLabel(self.status_frame, text="FPS: --")
        self.gesture_label = ctk.CTkLabel(self.status_frame, text="Gesture: --")
        self.mode_label = ctk.CTkLabel(self.status_frame, text="Mode: Normal")

    def update_preview(self, frame):
        """Called from processing thread via after() to update preview."""
        # Convert OpenCV frame to PhotoImage
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img_tk = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=img_tk)
        self.preview_label._image = img_tk  # Keep reference
```

### Mode Manager

```python
class ModeManager:
    def __init__(self, config_manager):
        self.config = config_manager
        self.current_mode = "normal"
        self.modes = {
            "normal": NormalMode(config_manager),
            "presentation": PresentationMode(config_manager),
            "gaming": GamingMode(config_manager),
        }

    def switch_mode(self, mode_name):
        if mode_name in self.modes:
            self.current_mode = mode_name
            profile_path = f"config/profiles/{mode_name}.json"
            self.config.load_profile(profile_path)

    def process_gesture(self, gesture_name, landmarks, context):
        return self.modes[self.current_mode].handle(gesture_name, landmarks, context)
```

---

## 12. Phase 7: Custom Gesture Training

### Duration: Week 3-4

### Tasks
1. Build gesture data collection UI
2. Implement landmark normalization for ML
3. Train classifier (RandomForest -> MLP)
4. Real-time prediction with confidence + stability check
5. Build gesture-to-action mapping UI

### Landmark Normalization for ML

```python
import numpy as np

def normalize_landmarks(landmarks):
    """
    Normalize 21 landmarks for ML:
    1. Translate so wrist (landmark 0) is origin
    2. Scale by hand size (wrist to middle MCP distance)
    3. Flatten to 63 features (21 landmarks x 3 coords: x, y, z)

    This makes the model invariant to:
    - Hand position in frame
    - Distance from camera
    """
    # Convert to numpy array: shape (21, 3)
    coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])

    # Step 1: Translate (wrist = origin)
    wrist = coords[0].copy()
    coords -= wrist

    # Step 2: Scale by hand size
    hand_size = np.linalg.norm(coords[9])  # Distance from wrist to middle MCP
    if hand_size > 0:
        coords /= hand_size

    # Step 3: Flatten to 63 features
    return coords.flatten()  # Shape: (63,)

def mirror_landmarks(features):
    """
    Mirror landmarks for left-hand augmentation.
    Flip x-coordinates (every 3rd value starting from index 0).
    """
    mirrored = features.copy()
    mirrored[0::3] *= -1  # Negate x values
    return mirrored
```

### Data Collection

```python
class GestureDataCollector:
    """
    Collects ~200-300 samples per gesture.
    Each sample = 63 features (normalized, flattened landmarks).
    """
    def __init__(self, samples_per_gesture=250):
        self.target_samples = samples_per_gesture
        self.data = {}  # gesture_name -> list of feature vectors

    def start_collection(self, gesture_name):
        self.data[gesture_name] = []
        self.current_gesture = gesture_name
        self.collecting = True

    def add_sample(self, landmarks):
        if not self.collecting:
            return
        features = normalize_landmarks(landmarks)
        self.data[self.current_gesture].append(features)

        # Optional: also add mirrored version
        mirrored = mirror_landmarks(features)
        self.data[self.current_gesture].append(mirrored)

        if len(self.data[self.current_gesture]) >= self.target_samples:
            self.collecting = False

    def get_dataset(self):
        X, y = [], []
        for gesture_name, samples in self.data.items():
            X.extend(samples)
            y.extend([gesture_name] * len(samples))
        return np.array(X), np.array(y)
```

### Model Training

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
import joblib

def train_gesture_model(X, y, model_type='random_forest'):
    """
    Train and evaluate gesture classifier.

    Args:
        X: Feature matrix, shape (n_samples, 63)
        y: Labels, shape (n_samples,)
        model_type: 'random_forest' or 'mlp'

    Returns:
        model, accuracy, confusion_matrix
    """
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                          random_state=42, stratify=y)

    if model_type == 'random_forest':
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == 'mlp':
        model = MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500,
                               random_state=42, early_stopping=True)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)

    return model, accuracy, cm

def save_model(model, path='models/custom_gestures.joblib'):
    joblib.dump(model, path)

def load_model(path='models/custom_gestures.joblib'):
    return joblib.load(path)
```

### Real-Time Prediction with Confidence + Stability

```python
class MLGesturePredictor:
    def __init__(self, model_path, confidence_threshold=0.85, stability_frames=5):
        self.model = load_model(model_path)
        self.confidence_threshold = confidence_threshold
        self.stability_frames = stability_frames
        self.prediction_history = []

    def predict(self, landmarks):
        features = normalize_landmarks(landmarks).reshape(1, -1)
        probabilities = self.model.predict_proba(features)[0]
        max_prob = np.max(probabilities)
        predicted_class = self.model.classes_[np.argmax(probabilities)]

        # Confidence check
        if max_prob < self.confidence_threshold:
            return None, max_prob

        # Stability check (N consecutive same predictions)
        self.prediction_history.append(predicted_class)
        if len(self.prediction_history) > self.stability_frames:
            self.prediction_history.pop(0)

        if (len(self.prediction_history) == self.stability_frames and
            all(p == predicted_class for p in self.prediction_history)):
            return predicted_class, max_prob

        return None, max_prob  # Not stable enough yet
```

### Gesture Trainer UI

```python
class GestureTrainerUI(ctk.CTkToplevel):
    """
    UI Flow:
    1. User enters gesture name
    2. Clicks "Start Recording"
    3. Holds the gesture for ~10 seconds (200-300 samples auto-captured)
    4. Progress bar shows collection status
    5. Repeat for each gesture
    6. Click "Train Model" -- shows accuracy + confusion matrix
    7. Click "Map Actions" -- assign each gesture to an action
    """
    pass  # Full implementation in code
```

### Done When
- User can train a new gesture in **under 2 minutes**
- Trained gesture triggers mapped action reliably
- Accuracy shown after training
- Gesture mapping saved to `gestures.json`

---

## 13. Phase 8: Voice Commands

### Duration: Week 5

### Tasks
1. Download Vosk small English model
2. Implement `src/core/voice.py` — Vosk listener thread
3. Restricted grammar for command accuracy
4. Combined gesture + voice usage
5. Optional push-to-talk

### Vosk Voice Command Implementation

```python
import vosk
import sounddevice as sd
import json
import queue
import threading

class VoiceCommandListener(threading.Thread):
    """
    Offline voice recognition using Vosk with restricted grammar.
    Restricted grammar MASSIVELY improves accuracy vs free dictation.
    """
    def __init__(self, model_path, command_callback, sample_rate=16000):
        super().__init__(daemon=True)
        self.model = vosk.Model(model_path)
        self.sample_rate = sample_rate
        self.callback = command_callback
        self.audio_queue = queue.Queue()
        self.running = True
        self.push_to_talk = False
        self.is_listening = True

        # Restricted grammar — fixed command list
        self.commands = [
            "click", "double click", "right click",
            "scroll up", "scroll down",
            "volume up", "volume down",
            "next slide", "previous slide",
            "start presentation", "stop presentation",
            "pause tracking", "resume tracking",
            "switch to gaming mode", "switch to normal mode",
            "open", "close", "minimize", "maximize",
            "zoom in", "zoom out",
            "select all", "copy", "paste", "undo", "redo"
        ]

        # Create recognizer with grammar
        grammar = json.dumps(self.commands)
        self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate, grammar)

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio chunk."""
        if self.is_listening:
            self.audio_queue.put(bytes(indata))

    def run(self):
        with sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=8000,
            dtype='int16',
            channels=1,
            callback=self._audio_callback
        ):
            while self.running:
                try:
                    data = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip()
                    if text and text in self.commands:
                        self.callback(text)

    def set_push_to_talk(self, active):
        self.is_listening = active

    def stop(self):
        self.running = False
```

### Voice-to-Action Mapping

```python
VOICE_ACTION_MAP = {
    "click": {"action": "left_click"},
    "double click": {"action": "double_click"},
    "right click": {"action": "right_click"},
    "scroll up": {"action": "scroll", "params": {"direction": "up", "amount": 3}},
    "scroll down": {"action": "scroll", "params": {"direction": "down", "amount": 3}},
    "volume up": {"action": "hotkey", "params": {"keys": ["volumeup"]}},
    "volume down": {"action": "hotkey", "params": {"keys": ["volumedown"]}},
    "next slide": {"action": "key_press", "params": {"key": "right"}},
    "previous slide": {"action": "key_press", "params": {"key": "left"}},
    "start presentation": {"action": "key_press", "params": {"key": "f5"}},
    "pause tracking": {"action": "pause_tracking"},
    "resume tracking": {"action": "resume_tracking"},
    "switch to gaming mode": {"action": "switch_mode", "params": {"mode": "gaming"}},
    "switch to normal mode": {"action": "switch_mode", "params": {"mode": "normal"}},
    "open": {"action": "context_action"},
    "copy": {"action": "hotkey", "params": {"keys": ["ctrl", "c"]}},
    "paste": {"action": "hotkey", "params": {"keys": ["ctrl", "v"]}},
    "undo": {"action": "hotkey", "params": {"keys": ["ctrl", "z"]}},
    "redo": {"action": "hotkey", "params": {"keys": ["ctrl", "y"]}},
    "select all": {"action": "hotkey", "params": {"keys": ["ctrl", "a"]}},
}
```

### Combined Gesture + Voice

```
User Flow:
1. Point at an icon with index finger (gesture moves cursor)
2. Say "open" (voice triggers click at current position)
3. Or: Point and say "right click" for context menu
```

### Done When
- **90% of spoken test commands** in a quiet room trigger the right action
- Voice commands work alongside gesture control
- Push-to-talk option available

---

## 14. Phase 9: Presentation Mode

### Duration: Week 6

### Tasks
1. Implement swipe detection (directional gesture)
2. Create transparent overlay window for laser pointer
3. Map presentation gestures
4. Test with PowerPoint and PDF presentations

### Swipe Detection

```python
class SwipeDetector:
    """
    Detect horizontal swipe gestures for slide navigation.
    Track hand position over time, detect rapid horizontal movement.
    """
    def __init__(self, threshold=0.15, time_window_ms=500):
        self.threshold = threshold  # Minimum x-distance for swipe
        self.time_window = time_window_ms / 1000.0
        self.positions = []  # (x, y, timestamp)

    def add_position(self, x, y, t):
        self.positions.append((x, y, t))
        # Remove old positions
        self.positions = [(px, py, pt) for px, py, pt in self.positions
                          if t - pt < self.time_window]

    def detect(self):
        if len(self.positions) < 5:
            return None

        start_x = self.positions[0][0]
        end_x = self.positions[-1][0]
        delta_x = end_x - start_x

        if abs(delta_x) > self.threshold:
            self.positions.clear()  # Reset after detection
            return "swipe_right" if delta_x > 0 else "swipe_left"
        return None
```

### Laser Pointer Overlay

```python
import tkinter as tk

class LaserOverlay:
    """
    Transparent, always-on-top window that draws a laser pointer dot.
    Covers the entire screen but is click-through.
    """
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.7)
        self.root.configure(bg='black')
        self.root.wm_attributes('-transparentcolor', 'black')
        # Make window click-through on Windows
        self.root.overrideredirect(True)

        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        self.dot = None
        self.visible = False

    def update_position(self, screen_x, screen_y):
        if self.dot:
            self.canvas.delete(self.dot)
        if self.visible:
            # Red dot with glow effect
            r = 10
            # Outer glow
            self.canvas.create_oval(screen_x-r*2, screen_y-r*2,
                                     screen_x+r*2, screen_y+r*2,
                                     fill='#ff000044', outline='')
            # Inner dot
            self.dot = self.canvas.create_oval(screen_x-r, screen_y-r,
                                                screen_x+r, screen_y+r,
                                                fill='red', outline='white', width=2)

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False
        if self.dot:
            self.canvas.delete(self.dot)
```

### Presentation Gesture Map

| Gesture | Action | Key Sent |
|---------|--------|----------|
| Swipe right | Next slide | Right arrow |
| Swipe left | Previous slide | Left arrow |
| Index finger point | Laser pointer (overlay dot) | — |
| Open palm hold (2s) | Black screen | B key |
| Fist | End show | Esc key |
| Pinch zoom (optional) | Zoom in/out | Ctrl+Mouse wheel |

### Done When
- A PowerPoint or PDF presentation can be run **end-to-end touch-free**
- Laser pointer dot visible and responsive
- Slide navigation with swipes works reliably

---

## 15. Phase 10: Gaming Mode

### Duration: Week 6-7

### Tasks
1. Implement profile system for key mappings
2. Create gaming-specific gesture detection
3. Optimize for lower latency
4. Build demo profiles for browser games

### Gaming-Specific Optimizations

```python
GAMING_OPTIMIZATIONS = {
    # Lower resolution for faster processing
    "camera": {"width": 320, "height": 240},

    # Higher FPS cap
    "fps_cap": 60,

    # Lighter smoothing (less lag)
    "one_euro": {"min_cutoff": 2.0, "beta": 0.01},

    # Lower smoothing factor
    "smoothing_factor": 2,

    # Process every frame (no skipping)
    "process_every_n_frames": 1,
}
```

### Directional Input (WASD Mapping)

```python
class DirectionalInput:
    """
    Map hand position relative to center into directional keys.
    Like a virtual joystick.
    """
    def __init__(self, dead_zone=0.08, center_x=0.5, center_y=0.5):
        self.dead_zone = dead_zone
        self.center = (center_x, center_y)
        self.active_keys = set()

    def get_directions(self, hand_x, hand_y):
        """Returns set of active directions based on hand position."""
        dx = hand_x - self.center[0]
        dy = hand_y - self.center[1]

        directions = set()
        if abs(dx) > self.dead_zone:
            directions.add("left" if dx < 0 else "right")
        if abs(dy) > self.dead_zone:
            directions.add("up" if dy < 0 else "down")

        return directions

    def update(self, hand_x, hand_y, key_map):
        """
        Press/release keys based on hand position.
        key_map example: {"left": "a", "right": "d", "up": "w", "down": "s"}
        """
        new_directions = self.get_directions(hand_x, hand_y)

        # Release keys no longer active
        for direction in self.active_keys - new_directions:
            pyautogui.keyUp(key_map[direction])

        # Press newly active keys
        for direction in new_directions - self.active_keys:
            pyautogui.keyDown(key_map[direction])

        self.active_keys = new_directions
```

### Demo Profiles

| Profile | Gesture | Mapped Key | Game Use |
|---------|---------|-----------|----------|
| **Dino Runner** | Hand up | Space (jump) | Jump over obstacles |
| **Dino Runner** | Hand down | Down arrow (duck) | Duck under obstacles |
| **Racing** | Hand left/right | A/D or Left/Right | Steering |
| **Racing** | Pinch | Space | Brake/boost |

### Important Note
> Some online games block simulated input (anti-cheat). Test with **offline or browser games** only. Document this limitation.

### Done When
- Demo profiles work with Chrome Dino game and a simple racing game
- Key presses respond with low latency
- Profile switching works from UI

---

## 16. Phase 11: Accessibility Settings

### Duration: Week 7

### Tasks
Build a comprehensive accessibility settings panel with all these controls:

### Settings Panel Controls

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| Sensitivity | Slider (1-10) | 5 | Cursor movement speed multiplier |
| Smoothing | Slider (1-20) | 5 | Higher = smoother but laggier |
| Active Region Size | Slider (40-90%) | 70% | How much of the frame maps to screen |
| Dwell Click | Toggle | Off | Hover for N seconds to click |
| Dwell Time | Slider (0.5-5s) | 1.5s | How long to hover before click |
| One-hand mode | Dropdown | Right | Right, Left, Either |
| Left-handed mode | Toggle | Off | Mirror gesture mapping |
| Click threshold | Slider | 0.04 | Larger for users with tremors |
| High-contrast UI | Toggle | Off | High-contrast color scheme |
| Large text | Toggle | Off | Increase all UI font sizes |
| Gesture hold time | Slider (100-2000ms) | 500ms | Min time to hold gesture |
| Gesture cooldown | Slider (100-3000ms) | 1000ms | Min time between same gesture triggers |
| Voice-only mode | Toggle | Off | Disable gesture control |
| Gesture-only mode | Toggle | Off | Disable voice control |
| Save Profile | Button | — | Save current settings to file |
| Load Profile | Button | — | Load settings from file |

### Dwell Click Implementation

```python
class DwellClicker:
    """
    For users who cannot pinch:
    If cursor stays within a small radius for dwell_time, trigger a click.
    Visual feedback: circular progress indicator on overlay.
    """
    def __init__(self, dwell_time_ms=1500, dwell_radius=20):
        self.dwell_time = dwell_time_ms / 1000.0
        self.dwell_radius = dwell_radius
        self.dwell_start = None
        self.dwell_pos = None
        self.progress = 0.0

    def update(self, screen_x, screen_y):
        if self.dwell_pos is None:
            self.dwell_pos = (screen_x, screen_y)
            self.dwell_start = time.time()
            return False

        dist = math.hypot(screen_x - self.dwell_pos[0],
                          screen_y - self.dwell_pos[1])

        if dist > self.dwell_radius:
            # Moved too far, reset
            self.dwell_pos = (screen_x, screen_y)
            self.dwell_start = time.time()
            self.progress = 0.0
            return False

        elapsed = time.time() - self.dwell_start
        self.progress = min(elapsed / self.dwell_time, 1.0)

        if elapsed >= self.dwell_time:
            self.dwell_pos = None
            self.dwell_start = None
            self.progress = 0.0
            return True  # Trigger click!

        return False
```

### Tremor Filter

```python
class TremorFilter:
    """
    Extra dead zone + stronger smoothing for users with hand tremors.
    Only pass through movement if it exceeds the dead zone threshold.
    """
    def __init__(self, dead_zone=0.02):
        self.dead_zone = dead_zone
        self.last_position = None

    def filter(self, x, y):
        if self.last_position is None:
            self.last_position = (x, y)
            return x, y

        dx = x - self.last_position[0]
        dy = y - self.last_position[1]

        if abs(dx) < self.dead_zone and abs(dy) < self.dead_zone:
            return self.last_position  # Ignore small movements

        self.last_position = (x, y)
        return x, y
```

---

## 17. Phase 12: Packaging & Release

### Duration: Week 8

### Tasks
1. Comprehensive error handling throughout
2. File-based logging
3. PyInstaller packaging to single .exe
4. User guide with screenshots
5. Demo video
6. Project report

### Error Handling Checklist

| Error | Detection | User Message |
|-------|-----------|-------------|
| No camera found | `cap.isOpened() == False` | "No camera detected. Please connect a webcam." |
| Camera in use | OpenCV error on capture | "Camera is in use by another app. Please close it." |
| Model file missing | `os.path.exists()` check | "Model file not found. Run 'python scripts/download_models.py'" |
| Vosk model missing | FileNotFoundError | "Voice model not found. Download from vosk.ai" |
| Low FPS warning | FPS < 15 for 30 frames | "Performance warning: Try lowering resolution in Settings" |
| Permission error | PyAutoGUI exception | "Cannot control mouse. Try running as administrator." |

### Logging Setup

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(log_file='touchless_control.log', level='INFO'):
    logger = logging.getLogger('touchless')
    logger.setLevel(getattr(logging, level))

    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
```

### PyInstaller Build

```bash
# Build command
pyinstaller --onefile --windowed --name "TouchlessControl" \
    --add-data "config;config" \
    --add-data "models;models" \
    --icon "assets/icon.ico" \
    src/main.py

# The --windowed flag suppresses the console window
# --add-data includes config and model files in the bundle
```

### Done When
- .exe runs on a clean Windows 10/11 machine
- All errors handled gracefully with user-friendly messages
- Log file captures debug info
- README + user guide complete
- Demo video recorded

---

## 18. Algorithm Details & Pseudocode

### 18.1 Main Processing Loop

```python
def processing_loop(camera, tracker, gesture_engine, action_layer,
                    mode_manager, config, shared_state):
    """
    Main processing pipeline -- runs in background thread.
    NEVER block the UI thread.
    """
    smoother_x = OneEuroFilter(**config.get('cursor.one_euro'))
    smoother_y = OneEuroFilter(**config.get('cursor.one_euro'))
    screen_w, screen_h = pyautogui.size()
    frame_count = 0
    fps_timer = time.time()

    while shared_state.running:
        frame = camera.get_frame()
        if frame is None:
            continue

        frame_count += 1
        skip_n = config.get('camera.process_every_n_frames', 1)
        if frame_count % skip_n != 0:
            continue

        # 1. Track hand
        timestamp_ms = int(time.monotonic() * 1000)
        hands = tracker.detect(frame, timestamp_ms)

        if not hands:
            shared_state.gesture = "no_hand"
            continue

        landmarks = hands[0]  # First hand

        # 2. Get pointer position (landmark 8 = index fingertip)
        pointer = landmarks[8]
        raw_x, raw_y = pointer.x, pointer.y

        # 3. Map to screen
        screen_x, screen_y = map_to_screen(raw_x, raw_y, config, screen_w, screen_h)

        # 4. Smooth
        screen_x = smoother_x(screen_x)
        screen_y = smoother_y(screen_y)

        # 5. Detect gesture
        gesture = gesture_engine.detect(landmarks)

        # 6. Process through mode manager
        action = mode_manager.process_gesture(gesture, landmarks,
                                                {'screen_x': screen_x, 'screen_y': screen_y})

        # 7. Execute action
        if action:
            action_layer.execute(action)

        # 8. Update shared state for UI
        shared_state.gesture = gesture
        shared_state.screen_pos = (screen_x, screen_y)
        shared_state.landmarks = landmarks
        shared_state.frame = frame

        # Calculate FPS
        if frame_count % 30 == 0:
            elapsed = time.time() - fps_timer
            shared_state.fps = 30 / elapsed
            fps_timer = time.time()
```

### 18.2 Finger-Up Detection (Detailed)

```python
def detect_fingers_up(landmarks):
    """
    Returns list of booleans [thumb, index, middle, ring, pinky]
    indicating which fingers are extended.
    """
    fingers = []

    # Thumb: special case -- compare x-position (not y) because thumb moves laterally
    # For right hand: thumb tip should be to the LEFT of the thumb IP joint
    # (This changes with handedness -- handle via config)
    if landmarks[4].x < landmarks[3].x:  # Right hand
        fingers.append(True)
    else:
        fingers.append(False)

    # Other 4 fingers: tip should be ABOVE (lower y) the PIP joint
    tip_ids = [8, 12, 16, 20]
    pip_ids = [6, 10, 14, 18]

    for tip, pip in zip(tip_ids, pip_ids):
        fingers.append(landmarks[tip].y < landmarks[pip].y)

    return fingers  # [thumb, index, middle, ring, pinky]
```

### 18.3 Complete Gesture State Machine

```
States: IDLE, MOVING, CLICKING, DRAGGING, SCROLLING, PAUSED

Transitions:
  IDLE -> MOVING:     index_up detected for N frames
  MOVING -> CLICKING: pinch_start detected, cooldown passed
  CLICKING -> IDLE:   pinch_end detected (single click)
  CLICKING -> DRAGGING: pinch_hold for drag_hold_frames
  DRAGGING -> IDLE:   pinch_end detected (release drag)
  MOVING -> SCROLLING: index_middle_up detected
  SCROLLING -> MOVING: only index_up detected
  ANY -> PAUSED:      open_palm detected OR F8 pressed
  PAUSED -> IDLE:     closed palm then open again / F8 pressed again
  ANY -> IDLE:        fist detected
```

---

## 19. Testing Strategy

### 19.1 Unit Tests (No Camera Needed)

```python
# tests/test_geometry.py
def test_euclidean_distance():
    """Test with known values."""
    assert euclidean_distance(Point(0,0,0), Point(3,4,0)) == 5.0

def test_normalize_landmarks():
    """Test normalization with synthetic landmarks."""
    # Create fake landmarks where wrist is at (0.5, 0.5)
    # After normalization, wrist should be at origin
    landmarks = create_fake_landmarks(wrist=(0.5, 0.5, 0.0))
    features = normalize_landmarks(landmarks)
    assert features[0] == 0.0  # Wrist x
    assert features[1] == 0.0  # Wrist y

# tests/test_smoothing.py
def test_one_euro_filter_reduces_jitter():
    """High-frequency noise should be smoothed out."""
    f = OneEuroFilter(min_cutoff=1.0, beta=0.007)
    noisy_signal = [100 + random.gauss(0, 5) for _ in range(100)]
    smoothed = [f(v, t=i*0.033) for i, v in enumerate(noisy_signal)]
    assert np.std(smoothed[10:]) < np.std(noisy_signal[10:])

# tests/test_gesture_engine.py
def test_pinch_hysteresis():
    """Pinch should not flicker when distance oscillates near threshold."""
    engine = GestureEngine(test_config)
    # Distance oscillating between 0.035 and 0.045 (between on=0.04 and off=0.06)
    # Should trigger pinch once, not oscillate
    result1 = engine.detect_pinch(0.035)  # Below on threshold
    assert result1 == "pinch_start"
    result2 = engine.detect_pinch(0.045)  # Above on but below off
    assert result2 == "pinch_hold"  # Should STAY pinched
    result3 = engine.detect_pinch(0.065)  # Above off threshold
    assert result3 == "pinch_end"
```

### 19.2 Manual Testing Checklist

| Test | How | Pass Criteria |
|------|-----|---------------|
| **Bright lighting** | Desk lamp directly on hand | Tracking doesn't drop |
| **Dim lighting** | Room lights off, screen light only | Tracking maintains (may reduce confidence) |
| **Backlit** | Window behind user | Hand still detected |
| **Distance: 40cm** | Hand close to camera | Landmarks accurate, no distortion |
| **Distance: 1.2m** | Hand far from camera | Still tracks, gestures work |
| **Left hand** | Use left hand only | All gestures work (with left-hand mode) |
| **Right hand** | Use right hand only | All gestures work |
| **Different skin tones** | Test with multiple people | No accuracy degradation |
| **640x480 camera** | Standard webcam | Runs at 25+ FPS |
| **1280x720 camera** | HD webcam | Runs at 20+ FPS |
| **30-minute session** | Leave running | No memory leak, stable CPU |
| **Accidental triggers** | Type on keyboard, talk | Minimal false gesture triggers |

### 19.3 Performance Benchmarks

| Metric | Target | How to Measure |
|--------|--------|---------------|
| FPS | >=25 (normal), >=40 (gaming) | Frame counter |
| Cursor latency | <100ms perceived | Visual comparison |
| Click accuracy | >95% intentional clicks land | Manual test session |
| Voice recognition | >90% in quiet room | Test each command 10 times |
| Memory usage | <500MB after 30 min | Task Manager |
| CPU usage | <30% on modern i5 | Task Manager |

---

## 20. Risk Matrix & Mitigations

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Jittery cursor** | High | High | One Euro Filter, active region, dead zone, higher smoothing. Tune `min_cutoff` and `beta` |
| **Accidental clicks** | High | Medium | Hysteresis (different on/off thresholds), cooldown timer, consecutive-frame check |
| **Poor lighting** | Medium | High | Show brightness hint in UI, lower `min_detection_confidence` to 0.5 |
| **High CPU usage** | Medium | Medium | Lower resolution (320x240), `process_every_n_frames=2`, cap FPS, use GPU if available |
| **Voice false triggers** | Medium | Medium | Restricted grammar (NOT free dictation), push-to-talk option |
| **Gaming input blocked** | Low | Medium | Document limitation, support only offline/browser games |
| **Webcam privacy concerns** | Medium | Low | Process everything locally, never record/upload, show camera-on indicator |
| **Multiple hands confusion** | Low | Medium | Set `num_hands=1` by default, use dominant hand setting |
| **Model file missing** | Low | High | Auto-download script, clear error messages, check on startup |
| **Memory leak over time** | Medium | Low | Profile with 30+ minute runs, use generators where possible, clear frame queues |

---

## 21. Performance Optimization Guide

### Priority Order (Biggest Impact First)

1. **Lower camera resolution**: 640x480 -> 320x240 = ~4x fewer pixels to process
2. **Skip frames**: `process_every_n_frames=2` = halves processing load
3. **FPS cap**: Don't process faster than needed (30 FPS normal, 60 gaming)
4. **Queue management**: `maxsize=2`, drop old frames immediately
5. **One Euro Filter**: Less computation than heavy smoothing, better results
6. **Daemon threads**: Ensure threads die with main process
7. **PyAutoGUI PAUSE=0**: Remove 100ms default pause between actions
8. **Lazy imports**: Don't import Vosk/sklearn until needed

### Memory Management

```python
# Drop old frames to prevent queue buildup
if frame_queue.full():
    frame_queue.get_nowait()  # Discard oldest frame

# Release camera properly on exit
def cleanup():
    camera.stop()
    camera.cap.release()
    cv2.destroyAllWindows()
```

### CPU Profiling

```python
# Use cProfile to find bottlenecks
import cProfile
cProfile.run('processing_loop()', 'profile_output')

# Or time individual operations
import time
t0 = time.perf_counter()
hands = tracker.detect(frame, timestamp_ms)
tracking_time = time.perf_counter() - t0  # Usually 15-30ms
```

---

## 22. Licensing & Monetisation

### License Compliance

| Dependency | License | Commercial Use | Action Needed |
|-----------|---------|---------------|---------------|
| MediaPipe | Apache 2.0 | Yes | Include license, check model card |
| OpenCV | Apache 2.0 | Yes | Include license |
| PyAutoGUI | BSD | Yes | Include license |
| pynput | LGPL | Yes | Include license, don't modify library |
| scikit-learn | BSD | Yes | Include license |
| Vosk | Apache 2.0 | Yes | Check specific model license |
| CustomTkinter | MIT | Yes | Include license |
| PyInstaller | GPL + bootloader exception | Yes (for distributing apps) | Include license |

**Action**: Create `THIRD_PARTY_LICENSES` file listing all dependencies and their license texts.

### Monetisation Ideas
- **Free core** + paid Pro (unlimited custom gestures, profiles, voice mode)
- **One-time license** for accessibility users or institutions
- **B2B version** for classrooms and presentations
- **Educational license** for universities

---

## 23. Future Roadmap

| Feature | Complexity | Priority |
|---------|-----------|----------|
| Two-hand gestures (zoom, rotate) | Medium | High |
| Head/eye tracking alternative input | High | Medium |
| macOS support | Medium | Medium |
| Linux support | Low | Medium |
| Cloud-synced profiles (opt-in) | Medium | Low |
| Gesture packs for specific apps | Low | Medium |
| Mobile/Raspberry Pi for smart TV | High | Low |
| Plugin system for third-party actions | High | Low |

---

## 24. Build Commands Reference

```bash
# Setup
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

# Download models
python scripts/download_models.py

# Run the application
python src/main.py

# Run tests
pytest tests/ -v

# Run with profiling
python -m cProfile -o profile.out src/main.py

# Build executable
pyinstaller --onefile --windowed --name "TouchlessControl" \
    --add-data "config;config" \
    --add-data "models;models" \
    src/main.py

# Generate requirements from environment
pip freeze > requirements.txt
```

---

## 25. Phase-by-Phase Prompts for AI Agents

Use these prompts to instruct any AI coding agent to build each phase. Each prompt is self-contained.

### Kickoff Prompt
> Read PLAN.md in full. Create the repository structure from Section 4, a requirements.txt with pinned versions, and a README. Do not write feature code yet. Show me the folder tree and wait for approval.

### Phase N Prompt (replace N with 1-12)
> Implement Phase N from PLAN.md exactly as specified. Keep core logic separate from UI, put thresholds in config, add unit tests where a camera is not needed, and run the tests. Tell me how to run and manually verify the "Done when" criteria. Do not start the next phase.

### Debug Prompt
> The cursor is jittery / clicks fire twice / FPS is low. Profile the pipeline, identify the cause, and fix it using the techniques in section 18 and section 20 of PLAN.md. Explain the change in two sentences.

### Review Prompt
> Review the whole codebase for bugs, unhandled errors, hard-coded values, and license issues. Produce a short list of fixes ordered by risk.

---

## Appendix A: Model Download URLs

```
MediaPipe Hand Landmarker:
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task

Vosk Small English Model:
https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
```

## Appendix B: Key Constants Quick Reference

```
LANDMARK_INDEX_TIP = 8          # Primary pointer
LANDMARK_THUMB_TIP = 4          # Pinch detection
LANDMARK_MIDDLE_TIP = 12        # Right-click pinch
LANDMARK_WRIST = 0              # Normalization origin
LANDMARK_MIDDLE_MCP = 9         # Hand size reference

PINCH_ON_THRESHOLD = 0.04       # Normalized distance
PINCH_OFF_THRESHOLD = 0.06      # Hysteresis gap = 0.02
CLICK_COOLDOWN_MS = 300
CONSECUTIVE_FRAMES = 3          # Rule-based stability
ML_CONFIDENCE = 0.85            # ML gesture threshold
ML_STABILITY_FRAMES = 5         # ML stability window
SCROLL_DEAD_ZONE = 0.5
ACTIVE_REGION = 0.15 to 0.85    # 70% of frame
DEFAULT_SMOOTHING_FACTOR = 5
ONE_EURO_MIN_CUTOFF = 1.0
ONE_EURO_BETA = 0.007
```

---

> **This document is the single source of truth for building the Touchless Computer Control System. Any developer or AI agent with access to this file should be able to implement the complete product without additional context.**
