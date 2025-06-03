from typing import Callable
import json

class UIManager:
    """
    그래픽 사용자 인터페이스(GUI) 요소들을 관리하고 사용자와의 상호작용을 처리합니다.
    """

    def __init__(self, core_controller):
        self.core_controller = core_controller
        self._on_settings_applied_callback = None
        self._on_command_submit_callback = None
        self._on_suggestion_accepted_callback = None
        self._on_undo_clicked_callback = None

    def display_main_window(self):
        print("✅ 메인 창이 표시됩니다.")

    def display_window_settings(self, settings_json: str) -> None:
        """
        설정을 보거나 편집할 수 있는 윈도우를 띄움.
        여기서는 allowed_dirs 설정 편집 기능을 콘솔 기반으로 간단 구현.
        """
        settings = json.loads(settings_json)

        allowed_dirs = settings.get("allowed_dirs", [])
        print("현재 허용된 관심 디렉토리:")
        for d in allowed_dirs:
            print(f"- {d}")

        # 사용자 입력으로 관심 디렉토리 리스트를 새로 받음 (콤마 구분)
        new_dirs_input = input("새 허용 관심 디렉토리들을 콤마로 구분하여 입력하세요:\n")
        new_allowed_dirs = [d.strip() for d in new_dirs_input.split(",") if d.strip()]
        settings["allowed_dirs"] = new_allowed_dirs

        # 콜백 호출하여 변경 사항 전달
        if self._on_settings_applied_callback:
            self._on_settings_applied_callback(json.dumps(settings))

    def display_window_suggestions(self, file_path: str, suggestions: list[str]) -> None:
        pass

    def display_window_command(self) -> None:
        pass

    def display_window_notificaiton(self, message: str, message_type: int) -> None:
        pass

    def register_on_command_submit(self, callback: Callable[[str], None]):
        self._on_command_submit_callback = callback

    def register_on_suggestion_accepted(self, callback: Callable[[str, str], None]):
        self._on_suggestion_accepted_callback = callback

    def register_on_undo_clicked(self, callback: Callable[[], None]):
        self._on_undo_clicked_callback = callback

    def register_on_settings_applied(self, callback: Callable[[str], None]):
        self._on_settings_applied_callback = callback

    def _hide_window_settings(self) -> None:
        pass

    def _hide_window_suggestions(self) -> None:
        pass

    def _hide_window_command(self) -> None:
        pass

    def _hide_window_notificaiton(self) -> None:
        pass