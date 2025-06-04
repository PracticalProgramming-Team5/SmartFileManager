import json
import os
from typing import Optional, List

class SettingsManager:
    def __init__(self, settings_path: str = "settings.json"):
        self.settings_path = settings_path
        self.settings = self.load_settings()

    def load_settings(self) -> dict:
        """
        설정 파일을 로드합니다. 없으면 빈 딕셔너리를 반환합니다.
        """
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("⚠️ settings.json 파일이 JSON 형식이 아닙니다.")
        return {}

    def save_settings(self) -> None:
        """
        설정을 settings.json 파일에 저장합니다.
        """
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    def set(self, key: str, value: str) -> None:
        """
        설정 값을 설정하고 저장합니다.
        """
        self.settings[key] = value
        self.save_settings()

    def delete(self, key: str) -> None:
        """
        설정 항목을 삭제합니다.
        """
        if key in self.settings:
            del self.settings[key]
            self.save_settings()

    def has(self, key: str) -> bool:
        """
        설정 항목이 존재하는지 확인합니다.
        """
        return key in self.settings

    def get_local(self, key: str) -> Optional[str]:
        """
        인스턴스에 로드된 settings에서 가져옵니다.
        (클래스가 관리 중인 settings 딕셔너리에서 검색)
        """
        return self.settings.get(key)

    @staticmethod
    def get(key: str) -> Optional[str]:
        """
        settings.json 파일에서 직접 key를 읽어옵니다.
        (정적 접근용: 인스턴스 없이 사용 가능)
        """
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            return settings.get(key)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def get_allowed_commands(self) -> List[str]:
        return self.settings.get("allow_commands", [])

    def get_blocked_commands(self) -> List[str]:
        return self.settings.get("block_commands", [])

    def get_interested_commands(self) -> List[str]:
        return self.settings.get("interest_commands", [])