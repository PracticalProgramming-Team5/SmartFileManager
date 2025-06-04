import os
from typing import List

class FileManagerCore:
    def __init__(self, settings_path):
        from settings_manager import SettingsManager
        from filesystem_manager import FileSystemManager
        from llm_client import LLMClient
        from history_manager import HistoryManager
        from context_builder import ContextBuilder
        from response_parser import ResponseParser
        from ui_manager import UIManager

        #self.settings_manager = SettingsManager(settings_path)
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

        response, err = self.llm.query(self.context_builder.system_prompt_move, prompt)
        if not response:
            self.ui.display_results("LLM 응답 오류 발생")
            return

        suggestions = self.response_interpreter.parse_action_move(response)
        self.ui.display_path_suggestions(file_path, suggestions)

    def handle_natural_language_command(self, command: str):
        root_dir = os.getcwd()
        dir_structure = self.context_builder.get_directory_structure(root_dir)
        prompt = self.context_builder.format_command_prompt(command, dir_structure)

        response, err = self.llm.query(self.context_builder.system_prompt_script, prompt)
        if not response:
            self.ui.display_results("LLM 명령 처리 실패")
            return

        plan = self.response_interpreter.parse_action_command(response)
        if not plan:
            self.ui.display_results("LLM 응답 해석 실패")
            return

        # 명령어 필터링 로직 적용
        allowed = self.settings_manager.get_allowed_commands()
        blocked = self.settings_manager.get_blocked_commands()
        interested = self.settings_manager.get_interested_commands()

        filtered_plan = []
        for cmd in plan['plan']:
            action = cmd.get('action')
            if action in blocked:
                self.ui.display_results(f"⛔ 차단된 명령어: {action} (수행하지 않음)")
                continue
            if action in interested:
                print(f"⭐ 관심 명령어 감지됨: {action}")  # 또는 UI에서 강조
            if allowed and action not in allowed:
                self.ui.display_results(f"⚠️ 허용되지 않은 명령어: {action} (수행하지 않음)")
                continue
            filtered_plan.append(cmd)

        if not filtered_plan:
            self.ui.display_results("실행 가능한 명령어가 없습니다.")
            return

        self.ui.display_action_plan({'plan': filtered_plan, 'explanation': plan['explanation']})

        confirmed = self.ui.prompt_for_confirmation("작업을 실행할까요?", ["예", "아니오"])
        if confirmed != "예":
            return

        if self.fs.execute_plan(filtered_plan):
            for action in filtered_plan:
                self.history.log_action(action)
            self.ui.display_results("작업 완료")
        else:
            self.ui.display_results("작업 실패")