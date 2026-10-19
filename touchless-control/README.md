# Touchless Computer Control System

> Control your computer with hand gestures and voice commands — no mouse or keyboard needed.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-green)
![License](https://img.shields.io/badge/License-Apache%202.0-orange)

## Features

- **Hand Tracking**: Real-time 21-landmark hand detection via MediaPipe
- **Cursor Control**: Move your cursor with your index finger
- **Gesture Clicks**: Pinch to click, scroll, drag — all touch-free
- **Custom Gestures**: Train your own gestures with a simple ML pipeline
- **Voice Commands**: Offline voice control via Vosk
- **Presentation Mode**: Swipe for slides, laser pointer overlay
- **Gaming Mode**: Map gestures to WASD and game keys
- **Accessibility**: Dwell click, tremor filter, high-contrast UI

## Quick Start

### Prerequisites
- Python 3.10 - 3.12
- Webcam
- Windows 10/11

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd touchless-control

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download required models
python scripts/download_models.py

# Run the application
python src/main.py
```

### Controls

| Gesture | Action |
|---------|--------|
| **Index finger up** | Move cursor |
| **Thumb + index pinch** | Left click (hold = drag) |
| **Thumb + middle pinch** | Right click |
| **Index + middle up (Peace sign)** | Scroll (move hand up/down) |
| **Wave / Swipe hand Right** | Next Page / Slide (`Right Arrow`) |
| **Wave / Swipe hand Left** | Previous Page / Slide (`Left Arrow`) |
| **L-Shape (Move Up / Down)** | Zoom In / Zoom Out (`Ctrl + =` / `Ctrl + -`) |
| **Open palm (Hold still 0.8s)** | Pause tracking |
| **Fist or Point Index** | Resume tracking |
| **Key 'H'** | Toggle on-screen interactive gesture guide |
| **Key 'P'** | Toggle pause / resume |
| **Key 'Q' / F8** | Emergency quit / pause |

## Project Structure

```
touchless-control/
├── config/              # JSON configuration files
├── models/              # ML models (MediaPipe, Vosk, custom)
├── src/
│   ├── core/            # Camera, tracking, gestures, actions
│   ├── ui/              # CustomTkinter interface
│   └── utils/           # Geometry, logging utilities
├── tests/               # Unit tests
├── scripts/             # Model download, data collection
└── docs/                # Architecture & user guide
```

## Development

See [PLAN.md](../PLAN.md) for the complete build plan with all 12 phases.

```bash
# Run tests
pytest tests/ -v

# Run with verbose logging
python src/main.py --log-level DEBUG
```

## Tech Stack

| Component | Tool | License |
|-----------|------|---------|
| Hand Tracking | MediaPipe Tasks API | Apache 2.0 |
| Camera | OpenCV | Apache 2.0 |
| Mouse/Keyboard | PyAutoGUI + pynput | BSD / LGPL |
| Custom Gestures | scikit-learn | BSD |
| Voice | Vosk | Apache 2.0 |
| UI | CustomTkinter | MIT |

## Privacy

Everything runs **100% locally**. No data is sent to any server. No video is recorded or stored.

## License

This project uses open-source tools. See [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES) for details.
