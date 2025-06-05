import os

from typing import Callable, Dict, Optional, Set, Union  # Set 추가
from watchdog.observers.api import BaseObserver, ObservedWatch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from file_manager_core import FileManagerCore


class DirectoryEventHandler(FileSystemEventHandler):
    """
    파일 시스템 이벤트를 처리하는 핸들러 클래스
    """

    def __init__(self, core_controller):
        """
        이벤트 핸들러 초기화

        Args:
            on_file_created_callback: 파일 생성 시 호출될 콜백 함수
            skip_hidden: 숨김 파일 무시 여부
        """
        self.core = core_controller

    def _check_valid(self, event: FileSystemEvent, flag = True):
        if event.is_directory: return None

        path = event.src_path if flag else event.dest_path
        if isinstance(path, bytes):
            file_path = path.decode()
        elif isinstance(path, str):
            file_path = path
        else: return None

        if os.path.basename(file_path).startswith("."):
            return None
        return file_path
                
    def on_created(self, event: FileSystemEvent) -> None:
        """
        파일 생성 이벤트 처리

        Args:
            event: 파일 시스템 이벤트 객체
        """
        file_path = self._check_valid(event)
        if file_path: self.core.handle_new_file(file_path)

        print(f"파일 생성됨: {file_path}")

    def on_deleted(self, event) -> None:
        file_path = self._check_valid(event)
        if file_path: self.core.handle_delete_file(file_path)

        print(f"파일 삭제됨: {file_path}")

    def on_moved(self, event) -> None:
        src_file_path = self._check_valid(event)
        dest_file_path = self._check_valid(event, False)
        if src_file_path and dest_file_path: self.core.handle_move_file(src_file_path, dest_file_path)

        print(f"파일 이동됨: {src_file_path} -> {dest_file_path}")


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
        self.handler = DirectoryEventHandler(self.core_controller)
        self.running: bool = False

    def add_directory(self, path: str) -> None:
        if not os.path.isdir(path):
            print(f"오류: '{path}'는 유효한 디렉토리가 아닙니다.")
            return

        abs_path: str = os.path.abspath(path)
        self.watched_directories.add(abs_path)

        if self.running:
            self.start()

    def remove_directory(self, path: str) -> None:
        """
        감시 목록에서 디렉토리를 제거합니다.

        Args:
            path: 감시 목록에서 제거할 디렉토리 경로
        """
        abs_path = os.path.abspath(path)
        if abs_path in self.watched_directories:
            self.watched_directories.remove(abs_path)

            if self.running:
                self.start()

        print(f"감시 목록에서 '{path}' 디렉토리를 제거했습니다.")

    def start(self) -> None:
        if self.running: self.stop()
        self.observer = Observer()  # type: ignore

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

    def _start_watching_directory(self, directory: str) -> None:
        self.observer.schedule(self.handler, directory, recursive=True)


# import time

# class DummyCore():
#     def handle_new_file(self, file_path: str):
#         print(f"[핸들러 호출됨] 새로운 파일: {file_path}")
#     def handle_delete_file(self, file_path: str):
#         print(f"[핸들러 호출됨] 삭제한 파일: {file_path}")
#     def handle_move_file(self, file_path1: str, file_path2: str):
#         print(f"[핸들러 호출됨] 이동한 파일: {file_path1} -> {file_path2}")

# if __name__ == "__main__":
#     monitor = DirectoryMonitor(core_controller=DummyCore())
#     monitor.add_directory("C:/Users/juhyu/OneDrive/바탕 화면/SmartFileManager")  # 감시할 디렉토리 경로
#     monitor.start()

#     print("디렉토리 감시 시작됨. 새 파일을 만들어 보세요.")
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\n종료 중...")
#         monitor.stop()