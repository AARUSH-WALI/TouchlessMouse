"""Touchless Computer Control System - Configuration Manager."""

import os
import json
import copy
from pathlib import Path


class Config:
    """
    Manages loading, merging, and accessing configuration with profile support.
    Supports nested dot-notation (e.g., config.get('camera.width', 640)).
    """

    def __init__(self, config_path=None, profile_name=None):
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.config_dir = self.root_dir / "config"
        
        default_file = Path(config_path) if config_path else (self.config_dir / "default_config.json")
        self.config_path = default_file
        self.current_profile = profile_name or "normal"
        self._data = {}
        self.load()

    def load(self):
        """Loads default configuration and active profile overrides."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

        if self.current_profile:
            self.load_profile(self.current_profile)

    def load_profile(self, profile_name):
        """Applies profile-specific overrides if available."""
        profile_file = self.config_dir / "profiles" / f"{profile_name}.json"
        if profile_file.exists():
            try:
                with open(profile_file, "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
                
                # Apply camera overrides
                if "camera_overrides" in profile_data:
                    self._deep_merge(self._data.setdefault("camera", {}), profile_data["camera_overrides"])
                
                # Apply cursor overrides
                if "cursor_overrides" in profile_data:
                    self._deep_merge(self._data.setdefault("cursor", {}), profile_data["cursor_overrides"])
                
                # Apply accessibility overrides
                if "accessibility_overrides" in profile_data:
                    self._deep_merge(self._data.setdefault("accessibility", {}), profile_data["accessibility_overrides"])
                
                self.current_profile = profile_name
            except Exception as e:
                print(f"[Config] Error loading profile {profile_name}: {e}")

    def _deep_merge(self, base_dict, override_dict):
        for key, value in override_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = copy.deepcopy(value)

    def get(self, key_path, default=None):
        """
        Retrieves a nested value using dot notation, e.g. 'camera.width'
        """
        keys = key_path.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set(self, key_path, value):
        """Sets a nested value using dot notation."""
        keys = key_path.split(".")
        current = self._data
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def __getitem__(self, item):
        return self._data[item]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, item):
        return item in self._data

    def as_dict(self):
        return copy.deepcopy(self._data)

    def save(self, target_path=None):
        """Saves current configuration to file."""
        path = Path(target_path) if target_path else self.config_path
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
