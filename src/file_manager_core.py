class FileManagerCore:
    def __init__(self, settings_path):
        from settings_manager import SettingsManager
        from filesystem_manager import FileSystemManager
        from llm_client import LLMClient
        from history_manager import HistoryManager
        from context_builder import ContextBuilder
        from response_parser import ResponseParser
        from ui_manager import UIManager

        self.settings_manager = SettingsManager(settings_path)
        self.fs = FileSystemManager()
        self.history = HistoryManager()
        self.llm = LLMClient()
        self.context_builder = ContextBuilder(self.fs)
        self.response_interpreter = ResponseParser()
        self.ui = UIManager(self)

    def start(self):
        self.ui.display_main_window()

    def stop(self):
        print("앱 종료 및 리소스 정리")

    def handle_new_file(self, file_path: str):
        file_ctx = self.context_builder.get_file_context(file_path, detail_level="partial")
        root_dir = os.path.dirname(file_path)
        dir_structure = self.context_builder.get_directory_structure(root_dir)

        prompt = self.context_builder.format_move_prompt(file_ctx, dir_structure)

        response, err = self.llm.query(ContextBuilder.system_prompt_move, prompt)
        if not response:
            self.ui.display_results("LLM 응답 오류 발생")
            return

        suggestions = self.response_interpreter.parse_action_move(response)
        self.ui.display_path_suggestions(file_path, suggestions)

    def handle_natural_language_command(self, command: str):
        root_dir = os.getcwd()
        dir_structure = self.context_builder.get_directory_structure(root_dir)
        prompt = self.context_builder.format_command_prompt(command, dir_structure)

        response, err = self.llm.query(ContextBuilder.system_prompt_script, prompt)
        if not response:
            self.ui.display_results("LLM 명령 처리 실패")
            return

        plan = self.response_interpreter.parse_action_command(response)
        self.ui.display_action_plan(plan)

        confirmed = self.ui.prompt_for_confirmation("작업을 실행할까요?", ["예", "아니오"])
        if confirmed != "예":
            return

        if self.fs.execute_plan(plan):
            for action in plan:
                self.history.log_action(action)
            self.ui.display_results("작업 완료")
        else:
            self.ui.display_results("작업 실패")

    def execute_file_operation(self, operation: dict):
        if self.fs.execute_plan([operation]):
            self.history.log_action(operation)

    def undo_last_operation(self):
        last = self.history.pop_last_action()
        if last and self.fs.reverse_action(last):
            self.ui.display_results("작업이 실행 취소되었습니다.")
        else:
            self.ui.display_results("실행 취소 실패")