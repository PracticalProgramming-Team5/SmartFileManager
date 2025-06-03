import json
import os
from typing import Any

class SettingsManager:
    _settings = {}
    _settings_file_path = None

    def __init__(self, settings_file_path: str):
        SettingsManager._settings_file_path = settings_file_path
        if os.path.exists(settings_file_path):
            with open(settings_file_path, "r", encoding="utf-8") as f:
                SettingsManager._settings = json.load(f)
        else:
            SettingsManager._settings = {}

    def load(self) -> dict:
        return SettingsManager._settings

    def save(self, settings: dict):
        SettingsManager._settings = settings
        with open(SettingsManager._settings_file_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    @staticmethod
    def get(key: str, default=None) -> Any:
        return SettingsManager._settings.get(key, default)

    @staticmethod
    def set(key: str, value: Any):
        SettingsManager._settings[key] = value