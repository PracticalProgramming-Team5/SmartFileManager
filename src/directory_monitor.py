import os
import time
from typing import Callable, Dict, Optional, Set, Union  # Set 추가
from watchdog.observers.api import BaseObserver, ObservedWatch
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from file_manager_core import FileManagerCore
from collections import deque
import threading


class DirectoryEventHandler(FileSystemEventHandler):
    def __init__(self, core_controller, threshold: float = 3.0):
        self.core = core_controller
        self.threshold = threshold
        self.history = deque()  # (timestamp, type, path)
        self.lock = threading.Lock()

    def _check_valid(self, event: FileSystemEvent, flag=True):
        path = event.src_path if flag else event.dest_path

        parts = os.path.normpath(path).split(os.sep)
        if any(part.startswith('.') for part in parts):
            return None
        
        if isinstance(path, bytes):
            path = path.decode()
        if not isinstance(path, str):
            return None
        if os.path.basename(path).startswith("."):
            return None
        return path

    def _record_event(self, event_type: str, path: str):
        timestamp = time.time()
        with self.lock:
            self.history.append((timestamp, event_type, path))
        return (timestamp, event_type, path)

    def _resolve_pair(self, item:tuple):
        # (timestamp, event_type, path)
        time.sleep(self.threshold)
        with self.lock:
            basename = os.path.basename(item[2])
            counterpart_type = 'deleted' if item[1] == 'created' else 'created'
            for t, e_type, e_path in list(self.history):
                if e_type == counterpart_type and os.path.basename(e_path) == basename:
                    matched_event = (t, e_type, e_path)
                    # 두 이벤트 쌍 처리
                    if item[1] == 'created':
                        src, dst = e_path, item[2]
                    else:
                        src, dst = item[2], e_path

                    self.core.handle_move_file(src, dst)
                    print(f"[on_moved 이벤트] {src} → {dst}")

                    # deque에서 제거(created, deleted 두 이벤트 모두 제거하기)
                    self.history = deque(e for e in self.history if e not in [item, matched_event])
                    return
        if item in self.history:
            self.history.remove(item)
            if item[1] == 'created':
                self.core.handle_new_file(item[2])
                print(f"[on_created 이벤트] {item[2]}")
            if item[1] == 'deleted':
                self.core.handle_delete_file(item[2])
                print(f"[on_deleted 이벤트] {item[2]}")

    def on_created(self, event):
        path = self._check_valid(event)
        if not path: return

        result = self._record_event('created', path)
        threading.Thread(target=self._resolve_pair, args=(result,), daemon=True).start()

    def on_deleted(self, event):
        path = self._check_valid(event)
        if not path: return

        result = self._record_event('deleted', path)
        threading.Thread(target=self._resolve_pair, args=(result,), daemon=True).start()

    def on_moved(self, event):
        src = self._check_valid(event)
        dst = self._check_valid(event, False)
        if src and dst:
            self.core.handle_move_file(src, dst)
            print(f"[on_moved 이벤트] {src} → {dst}")


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

class DummyCore():
    def handle_new_file(self, file_path: str):
        print(f"[핸들러 호출됨] 새로운 파일: {file_path}")
    def handle_delete_file(self, file_path: str):
        print(f"[핸들러 호출됨] 삭제한 파일: {file_path}")
    def handle_move_file(self, file_path1: str, file_path2: str):
        print(f"[핸들러 호출됨] 이동한 파일: {file_path1} -> {file_path2}")

if __name__ == "__main__":
    monitor = DirectoryMonitor(core_controller=DummyCore())
    monitor.add_directory("C:/Users/juhyu/OneDrive/바탕 화면/SmartFileManager")  # 감시할 디렉토리 경로
    monitor.start()

    print("디렉토리 감시 시작됨. 새 파일을 만들어 보세요.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n종료 중...")
        monitor.stop()