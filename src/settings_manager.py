import json
import os


class SettingsManager:
    """
    애플리케이션 설정을 불러오고, 저장하고, 접근을 제공합니다.
    """

    def __init__(self, settings_file_path: str):
        """
        설정 파일의 위치를 지정합니다.

        Args:
            settings_file_path: 설정 파일 경로
        """
        self.settings_file_path = settings_file_path
        self.settings = {}

        # 설정 파일이 없으면 기본 설정으로 초기화
        if os.path.exists(settings_file_path):
            self.settings = self.load()
        else:
            self.settings = self._get_default_settings()
            self.save(self.settings)

    def load(self) -> dict:
        """
        파일(예: JSON, YAML)에서 설정을 불러옵니다.

        Returns:
            불러온 설정 사전
        """
        try:
            with open(self.settings_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"설정을 불러오는 중 오류 발생: {e}")
            return self._get_default_settings()

    def save(self, settings: dict):
        """
        현재 설정을 파일에 저장합니다.

        Args:
            settings: 저장할 설정 사전
        """
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(self.settings_file_path), exist_ok=True)

            with open(self.settings_file_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)

            # 메모리 내의 설정 업데이트
            self.settings = settings
        except Exception as e:
            print(f"설정을 저장하는 중 오류 발생: {e}")

    def get(self, key: str, default=None):
        """
        특정 설정 값을 가져옵니다.

        Args:
            key: 가져올 설정 키
            default: 키가 없을 경우 반환할 기본값

        Returns:
            설정 값 또는 기본값
        """
        return self.settings.get(key, default)

    def set(self, key: str, value):
        """
        설정 값을 업데이트합니다 (메모리에서 변경되며, 영구 저장을 위해 save 호출 필요).

        Args:
            key: 설정할 설정 키
            value: 설정할 값
        """
        self.settings[key] = value

    def _get_default_settings(self) -> dict:
        """
        기본 설정 값을 반환합니다.

        Returns:
            기본 설정 사전
        """
        return {
            "watched_directories": [],
            "llm": {"api_key": "", "model_name": "gpt-4", "temperature": 0.7},
            "ui": {"theme": "system", "language": "ko", "show_notifications": True},
            "file_operations": {
                "max_history": 20,
                "create_backup_before_move": True,
                "skip_hidden_files": True,
            },
        }
