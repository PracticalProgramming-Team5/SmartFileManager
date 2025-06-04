import json
import os
from typing import Optional, List

class SettingsManager:
    def __init__(self, settings_path: str = "settings.json"):
        self.settings_path = settings_path
        self.settings = self.load_settings()
        self._ensure_default_keys()
        self.save_settings()  # 설정 초기화 후 항상 저장

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

    def _ensure_default_keys(self):
        """
        필수 키들이 없으면 기본값으로 초기화합니다.
        - 명령어 분류용 리스트
        - OpenAI API key 및 모델 이름
        """
        self.settings.setdefault("allow_commands", [])
        self.settings.setdefault("block_commands", [])
        self.settings.setdefault("interest_commands", [])
        self.settings.setdefault("api_key", "YOUR_API_KEY_HERE")  # 기본 API 키 (사용자가 수정해야 함)
        self.settings.setdefault("model_name", "gpt-4")            # 기본 모델명
        self.settings.setdefault("available_dirs", ["./"])         # 감시할 기본 디렉토리

    def set(self, key: str, value: str) -> None:
        """
        키에 값을 설정하고 저장합니다.
        """
        self.settings[key] = value
        self.save_settings()

    def delete(self, key: str) -> None:
        """
        키를 설정에서 제거하고 저장합니다.
        """
        if key in self.settings:
            del self.settings[key]
            self.save_settings()

    def has(self, key: str) -> bool:
        """
        설정 키 존재 여부를 확인합니다.
        """
        return key in self.settings

    def get_local(self, key: str) -> Optional[str]:
        """
        인스턴스에 로드된 설정 딕셔너리에서 값을 조회합니다.
        """
        return self.settings.get(key)

    @staticmethod
    def get(key: str) -> Optional[str]:
        """
        settings.json 파일을 직접 열어 특정 키를 읽어옵니다.
        (인스턴스 없이 접근 가능)
        """
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            return settings.get(key)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def get_allowed_commands(self) -> List[str]:
        """
        허용된 명령어 목록 반환
        """
        return self.settings.get("allow_commands", [])

    def get_blocked_commands(self) -> List[str]:
        """
        차단된 명령어 목록 반환
        """
        return self.settings.get("block_commands", [])

    def get_interested_commands(self) -> List[str]:
        """
        관심 있는 명령어 목록 반환
        """
        return self.settings.get("interest_commands", [])