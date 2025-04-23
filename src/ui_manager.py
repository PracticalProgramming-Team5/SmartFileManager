class UIManager:
    """
    그래픽 사용자 인터페이스(GUI) 요소들을 관리하고 사용자와의 상호작용을 처리합니다.
    """

    def __init__(self, core_controller):
        """
        GUI 구성 요소들을 초기화하고 FileManagerCore에 대한 참조를 저장합니다.

        Args:
            core_controller: FileManagerCore의 인스턴스
        """
        pass

    def display_main_window(self):
        """메인 애플리케이션 창을 표시합니다."""
        pass

    def prompt_for_confirmation(self, action_description: str, options: list) -> str:
        """
        제안된 작업(예: 파일 이동 제안)을 표시하고 사용자의 선택을 반환합니다.

        Args:
            action_description: 사용자에게 보여줄 작업 설명
            options: 사용자에게 제공할 선택 옵션들

        Returns:
            사용자가 선택한 옵션
        """
        pass

    def display_results(self, message: str):
        """
        성공 또는 오류 메시지를 보여줍니다.

        Args:
            message: 표시할 메시지
        """
        pass

    def get_nl_input(self) -> str:
        """
        자연어 명령을 입력받는 필드를 제공합니다.

        Returns:
            사용자가 입력한 자연어 명령
        """
        pass

    def display_settings_dialog(self, current_settings: dict) -> dict:
        """
        설정을 보거나 편집할 수 있는 대화 상자를 표시합니다.

        Args:
            current_settings: 현재 설정값

        Returns:
            업데이트된 설정값
        """
        pass

    def display_path_suggestions(self, file_path: str, suggestions: list[str]):
        """
        특정 파일에 대해 LLM이 제안한 경로 목록을 보여줍니다.

        Args:
            file_path: 대상 파일 경로
            suggestions: 제안된 경로 목록
        """
        pass

    def display_action_plan(self, plan: list[dict]):
        """
        복잡한 작업의 단계들을 보여줍니다.

        Args:
            plan: 실행할 작업 단계
        """
        pass

    # 이벤트 핸들러/콜백 함수들
    def on_submit_command(self):
        """사용자가 자연어 명령을 제출했을 때 호출됩니다."""
        pass

    def on_accept_suggestion(self):
        """사용자가 제안을 수락했을 때 호출됩니다."""
        pass

    def on_undo_click(self):
        """사용자가 실행 취소 버튼을 클릭했을 때 호출됩니다."""
        pass
