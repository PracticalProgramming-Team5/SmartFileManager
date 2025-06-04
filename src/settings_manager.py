import json
import os
from typing import Any, Optional, List

class SettingsManager:
    _settings_file = "settings.json"

    @classmethod
    def _load(cls) -> dict:
        if os.path.exists(cls._settings_file):
            try:
                with open(cls._settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ settings.json 파일이 JSON 형식이 아닙니다.")
        return {
            "allow_commands": [],
            "block_commands": [],
            "interest_commands": []
        }

    @classmethod
    def _save(cls, settings: dict) -> None:
        with open(cls._settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        settings = cls._load()
        return settings.get(key)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        settings = cls._load()
        settings[key] = value
        cls._save(settings)

    @classmethod
    def delete(cls, key: str) -> None:
        settings = cls._load()
        if key in settings:
            del settings[key]
            cls._save(settings)

    @classmethod
    def get_allowed_commands(cls) -> List[str]:
        return cls.get("allow_commands") or []

    @classmethod
    def get_blocked_commands(cls) -> List[str]:
        return cls.get("block_commands") or []

    @classmethod
    def get_interested_commands(cls) -> List[str]:
        return cls.get("interest_commands") or []

