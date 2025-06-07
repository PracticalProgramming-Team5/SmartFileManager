import json
import os
from typing import Any, Optional, List
from  filesystem_manager import FileSystemManager

class SettingsManager:
    """
    get(key): key에 대한 value를 반환

    set(key, value): key의 item을 value로 변경

    add(key, item): key의 value에 item 추가
    
    delete(key, item): key의 value에 item 제거
    """
    _settings_file = "settings.json"

    @classmethod
    def _load(cls) -> dict:
        if os.path.exists(cls._settings_file):
            try:
                with open(cls._settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("settings.json 파일이 JSON 형식이 아닙니다.")
        return {
            "api_key": "",
            "model_name": "",
            "available_dirs": [],
            "monitoring_dirs": [],
            "available_commands": [],
            "interest_commands": []
        }

    @classmethod
    def _save(cls, settings: dict) -> None:
        with open(cls._settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        if key == "command_list":
            return FileSystemManager.get_actions().keys()
        
        settings = cls._load()
        return settings.get(key)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        settings = cls._load()
        settings[key] = value
        cls._save(settings)

    @classmethod
    def add(cls, key: str, item: str) -> None:
        settings = cls._load()
        temp_set = set(settings[key])
        temp_set.add(item)
        settings[key] = list(temp_set)
        cls._save(settings)

    @classmethod
    def delete(cls, key: str, item:str) -> None:
        settings = cls._load()
        temp_set = set(settings[key])
        temp_set.discard(item)
        settings[key] = list(temp_set)
        cls._save(settings)