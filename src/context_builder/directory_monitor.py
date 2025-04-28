import os
import threading
from typing import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class DirectoryEventHandler(FileSystemEventHandler):
    """
    파일 시스템 이벤트를 처리하는 핸들러 클래스
    """

    def __init__(
        self, on_file_created_callback: Callable[[str], None], skip_hidden: bool = True
    ):
        """
        이벤트 핸들러 초기화

        Args:
            on_file_created_callback: 파일 생성 시 호출될 콜백 함수
            skip_hidden: 숨김 파일 무시 여부
        """
        self.on_file_created = on_file_created_callback
        self.skip_hidden = skip_hidden

    def on_created(self, event):
        """
        파일 생성 이벤트 처리

        Args:
            event: 파일 시스템 이벤트 객체
        """
        if not event.is_directory:
            file_path = event.src_path

            # 숨김 파일 건너뛰기 설정이 활성화되어 있고, 파일명이 '.'으로 시작하면 무시
            if self.skip_hidden and os.path.basename(file_path).startswith("."):
                return

            self.on_file_created(file_path)


class DirectoryMonitor:
    """
    지정된 디렉토리에서 새 파일 생성이나 관련 변경 사항을 감시합니다.
    """

    def __init__(self, core_controller):
        """
        FileManagerCore에 대한 참조를 저장합니다.

        Args:
            core_controller: FileManagerCore의 인스턴스
        """
        self.core_controller = core_controller
        self.watched_directories = set()
        self.observer = None
        self.handlers = {}  # 경로별 핸들러 저장
        self.running = False
        self.skip_hidden_files = True

    def add_directory(self, path: str):
        """
        감시 목록에 디렉토리를 추가합니다.

        Args:
            path: 감시할 디렉토리 경로
        """
        if not os.path.isdir(path):
            print(f"오류: '{path}'는 유효한 디렉토리가 아닙니다.")
            return

        abs_path = os.path.abspath(path)
        self.watched_directories.add(abs_path)

        # 이미 실행 중이면 새 디렉토리 감시 시작
        if self.running and self.observer:
            self._start_watching_directory(abs_path)

    def remove_directory(self, path: str):
        """
        감시 목록에서 디렉토리를 제거합니다.

        Args:
            path: 감시 목록에서 제거할 디렉토리 경로
        """
        abs_path = os.path.abspath(path)

        if abs_path in self.watched_directories:
            self.watched_directories.remove(abs_path)

            # 감시 중인 디렉토리였다면 감시 중지
            if self.running and abs_path in self.handlers:
                watch = self.handlers[abs_path].get("watch")
                if watch:
                    self.observer.unschedule(watch)
                del self.handlers[abs_path]

    def start(self):
        """감시 루프를 시작합니다 (별도의 스레드/프로세스에서 실행될 수 있음)."""
        if self.running:
            print("이미 디렉토리 감시가 실행 중입니다.")
            return

        self.observer = Observer()

        # 모든 등록된 디렉토리 감시 시작
        for directory in self.watched_directories:
            self._start_watching_directory(directory)

        self.observer.start()
        self.running = True

    def stop(self):
        """감시 루프를 중지합니다."""
        if not self.running or not self.observer:
            return

        self.observer.stop()
        self.observer.join()
        self.running = False
        self.handlers = {}

    def _on_file_created(self, file_path: str):
        """
        새 파일이 감지되었을 때 호출되는 내부 함수;
        FileManagerCore의 handle_new_file을 호출합니다.

        Args:
            file_path: 새로 생성된 파일 경로
        """
        # UI 스레드가 아닌 별도 스레드에서 콜백이 실행될 수 있으므로 주의
        # 필요하다면 이벤트 큐나 스레드 세이프한 방식으로 구현해야 함
        try:
            self.core_controller.handle_new_file(file_path)
        except Exception as e:
            print(f"파일 생성 이벤트 처리 중 오류 발생: {e}")

    def _start_watching_directory(self, directory: str):
        """
        지정된 디렉토리에 대한 감시를 시작합니다.

        Args:
            directory: 감시를 시작할 디렉토리 경로
        """
        handler = DirectoryEventHandler(self._on_file_created, self.skip_hidden_files)
        watch = self.observer.schedule(handler, directory, recursive=True)

        self.handlers[directory] = {"handler": handler, "watch": watch}

    def set_skip_hidden_files(self, skip: bool):
        """
        숨김 파일 처리 설정을 변경합니다.

        Args:
            skip: 숨김 파일 무시 여부
        """
        self.skip_hidden_files = skip

        # 이미 실행 중이면 모든 핸들러의 설정 업데이트
        for handler_info in self.handlers.values():
            handler = handler_info.get("handler")
            if handler:
                handler.skip_hidden = skip
