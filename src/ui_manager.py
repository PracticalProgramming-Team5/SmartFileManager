from typing import Callable

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
        명령 입력 윈도우를 띄움.
        """
        pass

    def display_window_notificaiton(self, message: str, message_type: int) -> None:
        """
        알림 창을 띄움.

        Args:
            message: 표시할 메시지
            message_type: 메시지 유형 (성공, 알림, 경고, 실패 등.. 상의 필요)
        """
        pass

    def register_on_command_submit(self, callback: Callable[[str], None]):
        """
        명령어 입력 이벤트를 처리하는 콜백 함수 등록.
        
        Args:
            callback(command: str) -> None: command 문자열을 받아 처리하는 콜백 함수
                - command: 사용자가 입력한 명령어
                
        """
        pass

    def register_on_suggestion_accepted(self, callback: Callable[[str, str], None]):
        """
        파일 이동 요청 이벤트를 처리하는 콜백 함수 등록
        
        Args:
            callback(src_pth: str, dst_pth: str) -> None: 파일 이동을 처리하는 콜백 함수
                - src_pth: 원래 파일 경로
                - dst_pth: 옮길 파일 경로

        """
        pass

    def register_on_undo_clicked(self, callback: Callable[[], None]):
        """
        명령 취소 이벤트를 처리하는 콜백 함수 등록
        
        Args:
            callback() -> None: 최근 명령을 취소하는 콜백 함수
        """
        pass

    def register_on_settings_applied(self, callback: Callable[[str], None]):
        """
        설정 적용 이벤트를 처리하는 콜백 함수 등록
        
        Args:
            callback(settings_json: str) -> None: settings 변경 사항을 적용하는 콜백 함수
                setting_json: 설정 파일 내용
        """
        pass
    