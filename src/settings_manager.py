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
        pass

    def load(self) -> dict:
        """
        파일(예: JSON, YAML)에서 설정을 불러옵니다.

        Returns:
            불러온 설정 사전
        """
        pass

    def save(self, settings: dict):
        """
        현재 설정을 파일에 저장합니다.

        Args:
            settings: 저장할 설정 사전
        """
        pass

    def get(self, key: str, default=None):
        """
        특정 설정 값을 가져옵니다.

        Args:
            key: 가져올 설정 키
            default: 키가 없을 경우 반환할 기본값

        Returns:
            설정 값 또는 기본값
        """
        pass

    def set(self, key: str, value):
        """
        설정 값을 업데이트합니다 (메모리에서 변경되며, 영구 저장을 위해 save 호출 필요).

        Args:
            key: 설정할 설정 키
            value: 설정할 값
        """
        pass
