import os
from typing import Callable, Dict, Optional, Set, Union  # Set 추가
from watchdog.observers.api import BaseObserver, ObservedWatch
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from file_manager_core import FileManagerCore


class DirectoryEventHandler(FileSystemEventHandler):
    """
    파일 시스템 이벤트를 처리하는 핸들러 클래스
    """

    def __init__(
        self, on_file_created_callback: Callable[[str], None], skip_hidden: bool = True
    ) -> None:
        """
        이벤트 핸들러 초기화

        Args:
            on_file_created_callback: 파일 생성 시 호출될 콜백 함수
            skip_hidden: 숨김 파일 무시 여부
        """
        self.on_file_created: Callable[[str], None] = on_file_created_callback
        self.skip_hidden: bool = skip_hidden

    def on_created(self, event: FileSystemEvent) -> None:
        """
        파일 생성 이벤트 처리

        Args:
            event: 파일 시스템 이벤트 객체
        """
        if event.is_directory:
            return

        if isinstance(event.src_path, bytes):
            file_path: str = event.src_path.decode()
        elif isinstance(event.src_path, str):
            file_path: str = event.src_path
        else:
            raise ValueError("src_path가 str도 byte도 아님.")

        if self.skip_hidden and os.path.basename(file_path).startswith("."):
            return

        self.on_file_created(file_path)
        print(f"파일 생성됨: {file_path}")


class DirectoryMonitor:
    """
    지정된 디렉토리에서 새 파일 생성이나 관련 변경 사항을 감시합니다.
    """

    def __init__(self, core_controller: FileManagerCore) -> None:
        """
        FileManagerCore에 대한 참조를 저장합니다.

        Args:
            core_controller: FileManagerCore의 인스턴스
        """
        self.core_controller: FileManagerCore = core_controller
        self.watched_directories: Set[str] = set()
        self.observer: Optional[BaseObserver] = None
        self.handlers: Dict[
            str, Dict[str, Union[DirectoryEventHandler, BaseObserver]]
        ] = {}
        self.running: bool = False
        self.skip_hidden_files: bool = True

    def add_directory(self, path: str) -> None:
        """
        감시 목록에 디렉토리를 추가합니다.

        Args:
            path: 감시할 디렉토리 경로
        """
        if not os.path.isdir(path):
            print(f"오류: '{path}'는 유효한 디렉토리가 아닙니다.")
            return

        abs_path: str = os.path.abspath(path)
        self.watched_directories.add(abs_path)

        if self.running and self.observer:
            self._start_watching_directory(abs_path)

    def remove_directory(self, path: str) -> None:
        """
        감시 목록에서 디렉토리를 제거합니다.

        Args:
            path: 감시 목록에서 제거할 디렉토리 경로
        """
        abs_path: str = os.path.abspath(path)

        if abs_path in self.watched_directories:
            self.watched_directories.remove(abs_path)

            if self.running and abs_path in self.handlers and self.observer:
                handler_entry = self.handlers.get(abs_path)
                if handler_entry:
                    watch = handler_entry.get("watch")

                    if isinstance(watch, ObservedWatch):
                        if watch:
                            self.observer.unschedule(watch)
                if abs_path in self.handlers:
                    del self.handlers[abs_path]

            print(f"감시 목록에서 '{path}' 디렉토리를 제거했습니다.")

    def start(self) -> None:
        if self.running:
            print("이미 디렉토리 감시가 실행 중입니다.")
            return

        self.observer = Observer()  # type: ignore
        if not isinstance(self.observer, BaseObserver):  # type: ignore
            print("오류: Observer가 BaseObserver의 인스턴스가 아닙니다.")
            return

        directory: str
        for directory in self.watched_directories:
            self._start_watching_directory(directory)

        self.observer.start()
        self.running = True

    def stop(self) -> None:
        """감시 루프를 중지합니다."""
        if not self.running or not self.observer:
            return

        self.observer.stop()
        self.observer.join()
        self.running = False
        self.handlers = {}

    def _on_file_created(self, file_path: str) -> None:
        """
        새 파일이 감지되었을 때 호출되는 내부 함수;
        FileManagerCore의 handle_new_file을 호출합니다.

        Args:
            file_path: 새로 생성된 파일 경로
        """

        self.core_controller.handle_new_file(file_path)

    def _start_watching_directory(self, directory: str) -> None:
        """
        지정된 디렉토리에 대한 감시를 시작합니다.

        Args:
            directory: 감시를 시작할 디렉토리 경로
        """
        if not self.observer:  # Observer가 초기화되었는지 확인
            print("오류: Observer가 초기화되지 않았습니다.")
            return

        # 지역 변수 타입 명시
        handler: DirectoryEventHandler = DirectoryEventHandler(
            self._on_file_created, self.skip_hidden_files
        )
        # schedule 메소드가 반환하는 watch 객체의 정확한 타입은 watchdog 라이브러리 확인 필요
        watch: object = self.observer.schedule(handler, directory, recursive=True)

        self.handlers[directory] = {"handler": handler, "watch": watch}

    def set_skip_hidden_files(self, skip: bool) -> None:
        """
        숨김 파일 처리 설정을 변경합니다.

        Args:
            skip: 숨김 파일 무시 여부
        """
        self.skip_hidden_files = skip

        # 지역 변수 타입 명시
        handler_info: Dict[str, object]
        for handler_info in self.handlers.values():
            # handler 객체의 타입을 Optional[DirectoryEventHandler]로 명시
            handler: Optional[DirectoryEventHandler] = handler_info.get("handler")  # type: ignore
            if handler:
                handler.skip_hidden = skip
