import os
import threading
from typing import Dict, List, Any, Optional, Union, TypedDict, cast

from settings_manager import SettingsManager
from directory_monitor import DirectoryMonitor
from ui_manager import UIManager
from filesystem_manager import FileSystemManager
from context_builder import ContextBuilder
from llm_client import LLMClient
from response_interpreter import ResponseInterpreter, PathSuggestion, ActionPlan
from history_manager import HistoryManager


class FileOperation(TypedDict, total=False):
    """파일 작업을 위한 타입 정의"""

    action: str
    source: str
    destination: str
    path: str
    new_name: str
    plan: List[ActionPlan]


class FileManagerCore:
    """
    전체 애플리케이션 흐름을 조정하고 다른 모듈들을 초기화 및 관리하는 메인 컨트롤러
    """

    def __init__(self, settings_path: str) -> None:
        """
        핵심 구성 요소들을 초기화하고 설정을 불러옵니다.

        Args:
            settings_path: 설정 파일의 경로
        """
        # 각 모듈 순서대로 초기화
        self.settings_manager: SettingsManager = SettingsManager(settings_path)
        self.settings: Dict[str, Any] = self.settings_manager.load()

        self.filesystem_manager: FileSystemManager = FileSystemManager()
        self.context_builder: ContextBuilder = ContextBuilder(self.filesystem_manager)

        # LLM 클라이언트 초기화
        api_key: str = self.settings.get("llm", {}).get("api_key", "")
        model_name: str = self.settings.get("llm", {}).get("model_name", "gpt-4")
        self.llm_client: LLMClient = LLMClient(api_key, model_name)

        # 응답 해석기 초기화
        self.response_interpreter: ResponseInterpreter = ResponseInterpreter()

        # 작업 기록 관리자 초기화
        max_history: int = self.settings.get("file_operations", {}).get(
            "max_history", 20
        )
        self.history_manager: HistoryManager = HistoryManager(max_history)

        # 디렉토리 모니터 초기화 (마지막에 초기화해야 함)
        self.directory_monitor: DirectoryMonitor = DirectoryMonitor(self)

        # UI 관리자는 마지막에 초기화 (다른 모듈들이 먼저 준비되어야 함)
        self.ui_manager: UIManager = UIManager(self)

        # 초기화 플래그
        self._initialized: bool = True
        self._running: bool = False

    def start(self) -> None:
        """디렉토리 모니터링 및 GUI를 시작합니다."""
        if self._running:
            return

        # 감시할 디렉토리 설정
        watched_dirs: List[str] = self.settings.get("watched_directories", [])
        for directory in watched_dirs:
            self.directory_monitor.add_directory(directory)

        # 디렉토리 모니터링 시작
        self.directory_monitor.start()

        # UI 감시 디렉토리 목록 업데이트
        self.ui_manager.update_watched_directories(watched_dirs)

        # 기록 목록 UI 업데이트
        self.ui_manager.update_history(self.history_manager.get_history())

        # UI 표시
        self._running = True
        self.ui_manager.display_main_window()

    def stop(self) -> None:
        """모니터링을 중지하고 자원을 정리합니다."""
        if not self._running:
            return

        # 디렉토리 모니터링 중지
        self.directory_monitor.stop()

        # 설정 저장
        self.settings_manager.save(self.settings)

        self._running = False

    def handle_new_file(self, file_path: str) -> None:
        """
        DirectoryMonitor에 의해 호출됩니다.
        컨텍스트(맥락 정보)를 가져오고, LLM에 질의하고,
        GUI를 통해 제안을 표시하고, 선택된 작업을 실행하는 전체 과정을 조율합니다.

        Args:
            file_path: 새로 생성된 파일 경로
        """
        try:
            # 파일 컨텍스트 가져오기
            file_context: Dict[str, Any] = self.context_builder.get_file_context(
                file_path, "partial"
            )

            # 디렉토리 구조 가져오기
            parent_dir: str = os.path.dirname(file_path)
            dir_structure: str = self.context_builder.get_directory_structure(
                parent_dir
            )

            # LLM에 프롬프트 생성
            prompt: str = self.context_builder.format_move_prompt(
                file_context, dir_structure
            )

            # LLM에 질의
            llm_response: str = self.llm_client.query(prompt)

            # 응답 파싱하여 제안된 경로 추출
            suggestions: List[PathSuggestion] = (
                self.response_interpreter.parse_move_suggestions(llm_response)
            )

            # UI를 통해 사용자에게 제안 표시 (GUI 스레드에서 실행)
            if suggestions:
                # UI 스레드에서 안전하게 대화상자 표시
                self.ui_manager.display_path_suggestions(file_path, suggestions)
            else:
                # 제안이 없을 경우 메시지 표시
                self.ui_manager.display_results(
                    "파일 분류를 위한 제안을 생성할 수 없습니다."
                )

        except Exception as e:
            error_msg: str = f"파일 처리 중 오류 발생: {str(e)}"
            print(error_msg)
            self.ui_manager.display_results(error_msg)

    def handle_natural_language_command(self, command: str) -> None:
        """
        UIManager에 의해 호출됩니다.
        명령어를 분석하고, 필요한 경우 LLM에 작업 계획을 질의하고,
        GUI를 통해 사용자에게 확인받은 후, 계획을 실행하는 과정을 조율합니다.

        Args:
            command: 사용자의 자연어 명령
        """
        try:
            # 디렉토리 구조 가져오기
            watch_dirs: List[str] = self.settings.get("watched_directories", [])
            dir_structure: str = ""

            # 감시 중인 디렉토리가 있으면 첫 번째 디렉토리의 구조를 사용
            if watch_dirs:
                dir_structure = self.context_builder.get_directory_structure(
                    watch_dirs[0]
                )
            else:
                # 기본 디렉토리 사용
                default_dir: str = os.path.expanduser("~")
                dir_structure = self.context_builder.get_directory_structure(
                    default_dir
                )

            # LLM에 프롬프트 생성
            prompt: str = self.context_builder.format_command_prompt(
                command, dir_structure
            )

            # LLM에 질의
            llm_response: str = self.llm_client.query(prompt)

            # 응답 파싱하여 작업 계획 추출
            action_plan: List[ActionPlan] = self.response_interpreter.parse_action_plan(
                llm_response
            )

            if action_plan:
                # UI를 통해 작업 계획 확인 요청
                self.ui_manager.display_action_plan(action_plan)
            else:
                self.ui_manager.display_results(
                    f"'{command}' 명령을 처리할 수 없습니다. 다른 표현으로 시도해 보세요."
                )

        except Exception as e:
            error_msg: str = f"명령 처리 중 오류 발생: {str(e)}"
            print(error_msg)
            self.ui_manager.display_results(error_msg)

    def execute_file_operation(self, operation: FileOperation) -> bool:
        """
        확인된 작업(이동, 이름 변경 등)을 수행하기 위해 FileSystemManager를 호출하고,
        실행 취소(undo)를 위해 작업 내용을 기록합니다.

        Args:
            operation: 실행할 파일 작업에 대한 상세 정보를 담은 사전

        Returns:
            작업 성공 여부
        """
        try:
            # 단일 작업 처리
            if "action" in operation:
                action_type: str = operation["action"]
                result: bool = False

                if action_type == "move":
                    result = self.filesystem_manager.move_file(
                        cast(str, operation.get("source", "")),
                        cast(str, operation.get("destination", "")),
                    )

                elif action_type == "rename":
                    result = self.filesystem_manager.rename_item(
                        cast(str, operation.get("path", "")),
                        cast(str, operation.get("new_name", "")),
                    )

                elif action_type == "delete":
                    result = self.filesystem_manager.delete_item(
                        cast(str, operation.get("path", ""))
                    )

                elif action_type == "create_directory":
                    result = self.filesystem_manager.create_directory(
                        cast(str, operation.get("path", ""))
                    )

                # 작업이 성공하면 기록에 추가
                if result:
                    self.history_manager.log_action(operation)
                    # UI 업데이트
                    self.ui_manager.update_history(self.history_manager.get_history())

                return result

            # 여러 작업 처리 (plan 키가 있는 경우)
            elif "plan" in operation and isinstance(operation["plan"], list):
                result = self.filesystem_manager.execute_plan(
                    cast(List[Dict[str, Any]], operation["plan"])
                )

                # 작업이 성공하면 기록에 모든 작업 추가
                if result:
                    for action in cast(List[Dict[str, Any]], operation["plan"]):
                        self.history_manager.log_action(action)
                    # UI 업데이트
                    self.ui_manager.update_history(self.history_manager.get_history())

                return result

            return False

        except Exception as e:
            error_msg: str = f"파일 작업 실행 중 오류 발생: {str(e)}"
            print(error_msg)
            return False

    def undo_last_operation(self) -> bool:
        """
        HistoryManager에서 마지막 작업을 가져와
        FileSystemManager에게 해당 작업을 되돌리도록 요청합니다.

        Returns:
            작업 취소 성공 여부
        """
        # 마지막 작업 가져오기
        last_action: Optional[Dict[str, Any]] = self.history_manager.pop_last_action()
        if not last_action:
            return False

        # 작업 되돌리기
        result: bool = self.filesystem_manager.reverse_action(last_action)

        # UI 업데이트
        self.ui_manager.update_history(self.history_manager.get_history())

        return result

    def add_watch_directory(self, directory: str) -> None:
        """
        감시 목록에 디렉토리를 추가합니다.

        Args:
            directory: 감시할 디렉토리 경로
        """
        # 디렉토리 모니터에 추가
        self.directory_monitor.add_directory(directory)

        # 설정에도 추가
        if "watched_directories" not in self.settings:
            self.settings["watched_directories"] = []

        # 중복 확인
        if directory not in self.settings["watched_directories"]:
            self.settings["watched_directories"].append(directory)
            self.settings_manager.save(self.settings)

        # UI 업데이트
        self.ui_manager.update_watched_directories(self.settings["watched_directories"])

    def remove_watch_directory(self, directory: str) -> None:
        """
        감시 목록에서 디렉토리를 제거합니다.

        Args:
            directory: 제거할 디렉토리 경로
        """
        # 디렉토리 모니터에서 제거
        self.directory_monitor.remove_directory(directory)

        # 설정에서도 제거
        if (
            "watched_directories" in self.settings
            and directory in self.settings["watched_directories"]
        ):
            self.settings["watched_directories"].remove(directory)
            self.settings_manager.save(self.settings)

        # UI 업데이트
        self.ui_manager.update_watched_directories(self.settings["watched_directories"])

    def get_settings(self) -> Dict[str, Any]:
        """
        현재 설정을 반환합니다.

        Returns:
            현재 설정 사전
        """
        return self.settings

    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """
        설정을 업데이트하고 관련 모듈에 변경 사항을 알립니다.

        Args:
            new_settings: 새로운 설정 사전
        """
        # 설정 업데이트
        self.settings = new_settings
        self.settings_manager.save(self.settings)

        # LLM 클라이언트 설정 업데이트
        llm_settings: Dict[str, Any] = new_settings.get("llm", {})
        self.llm_client.update_settings(
            api_key=llm_settings.get("api_key"),
            model_name=llm_settings.get("model_name"),
        )

        # 디렉토리 모니터 설정 업데이트
        skip_hidden: bool = new_settings.get("file_operations", {}).get(
            "skip_hidden_files", True
        )
        self.directory_monitor.set_skip_hidden_files(skip_hidden)

        # 작업 기록 관리자 설정 업데이트
        max_history: int = new_settings.get("file_operations", {}).get(
            "max_history", 20
        )
        # HistoryManager의 max_history 속성 변경
        self.history_manager.max_history = max_history
