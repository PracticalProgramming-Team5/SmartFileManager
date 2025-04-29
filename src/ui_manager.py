class UIManager:
    """
    그래픽 사용자 인터페이스(GUI) 요소들을 관리하고 사용자와의 상호작용을 처리합니다.
    """

    def __init__(self):
        """
        GUI 구성 요소들을 초기화함.
        """
        pass

    def display_window_settings(self, settings_json: str) -> None:
        """
        설정을 보거나 편집할 수 있는 윈도우를 띄움.

        Args:
            settings_json: json 형식의 설정 파일
        """
        pass


    def display_window_suggestions(self, file_path: str, suggestions: list[str]) -> None:
        """
        특정 파일에 대해 LLM이 제안한 경로 목록을 보여줌.

        Args:
            file_path: 대상 파일 경로
            suggestions: 제안된 경로 목록
        """
        pass

    def display_window_command(self) -> None:
        """
        명령 입력 윈도우를 띄움
        """
        pass

    def display_window_notificaiton(self, message: str, message_type: int) -> None:
        """
        알림 창을 띄움

        Args:
            message: 표시할 메시지
            message_type: 메시지 유형 (성공, 알림, 경고, 실패 등.. 상의 필요)
        """
        pass
