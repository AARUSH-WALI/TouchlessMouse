import pytest
from src.core.config import Config


def test_default_config_loading():
    config = Config()
    assert config.get("camera.width") == 640
    assert config.get("camera.height") == 480
    assert config.get("camera.fps_cap") == 30
    assert config.get("camera.mirror") is True
    assert config.get("failsafe.hotkey") == "F8"


def test_profile_override():
    config = Config(profile_name="gaming")
    assert config.get("camera.width") == 320
    assert config.get("camera.height") == 240
    assert config.get("camera.fps_cap") == 60


def test_dot_notation_access():
    config = Config()
    assert config.get("cursor.active_region.left") == 0.15
    config.set("cursor.active_region.left", 0.25)
    assert config.get("cursor.active_region.left") == 0.25
