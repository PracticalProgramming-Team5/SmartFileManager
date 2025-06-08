import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from collections import deque
import threading
import sys
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt

class DirectoryEventHandler(FileSystemEventHandler):
    def __init__(self, callback, threshold: float = 3.0):
        self.signal = callback
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

                    if src != dst:
                        self.signal(src, dst, 2)
                        print(f"[on_moved 이벤트] {src} → {dst}")

                    # deque에서 제거(created, deleted 두 이벤트 모두 제거하기)
                    self.history = deque(e for e in self.history if e not in [item, matched_event])
                    return
        if item in self.history:
            self.history.remove(item)
            if item[1] == 'created':
                self.signal(item[2], None, 0)
                print(f"[on_created 이벤트] {item[2]}")
            if item[1] == 'deleted':
                self.signal(item[2], None, 1)
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
        if src and dst and src != dst:
            self.signal(src, dst, 2)
            print(f"[on_moved 이벤트] {src} → {dst}")


class DirectoryMonitor:
    """
    지정된 디렉토리에서 새 파일 생성이나 관련 변경 사항을 감시합니다.
    """

    def __init__(self, callback) -> None:
        """
        FileManagerCore에 대한 참조를 저장합니다.

        Args:
            callback: 콜백 함수
        """
        self.watched_directories = set()
        self.observer = None
        self.handler = DirectoryEventHandler(callback)
        self.running = False

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

# # --- 워커 객체 (시그널 기반 처리) ---
# class DummyCore(QObject):
#     file_processed = pyqtSignal(str)
    
#     def __init__(self, directory_to_watch):
#         super().__init__()
        
#         self.monitor = DirectoryMonitor(self.directoryhandler)
#         self.monitor.add_directory(directory_to_watch)
#         self.monitor.start()

#     def directoryhandler(self, src, dst, event_type):
#         if event_type == 0:
#             self.file_processed.emit(f"새 파일 생성됨: {os.path.basename(src)}")
#         if event_type == 1:
#             self.file_processed.emit(f"파일 삭제됨: {os.path.basename(src)}")
#         if event_type == 2:
#             self.file_processed.emit(f"파일 이동됨: {os.path.basename(src)} → {os.path.basename(dst)}")

# # --- 메인 UI ---
# class MainWindow(QWidget):
#     def __init__(self, directory_to_watch):
#         super().__init__()
#         self.setWindowTitle("파일 감시기")
#         self.setGeometry(200, 200, 400, 100)
#         self.label = QLabel("대기 중...", self)
#         self.label.setAlignment(Qt.AlignCenter)
#         layout = QVBoxLayout()
#         layout.addWidget(self.label)
#         self.setLayout(layout)

#         # 워커 생성 및 스레드 이동
#         self.worker = DummyCore(directory_to_watch)
#         self.worker_thread = QThread()
#         self.worker.moveToThread(self.worker_thread)
#         self.worker_thread.start()

#         # UI 업데이트 연결
#         self.worker.file_processed.connect(self.update_ui)

#     @pyqtSlot(str)
#     def update_ui(self, msg):
#         self.label.setText(msg)

#     def closeEvent(self, event):
#         self.monitor.stop()
#         self.worker_thread.quit()
#         self.worker_thread.wait()
#         event.accept()

# # --- 실행 ---
# if __name__ == "__main__":
#     watch_path = "C:/Users/amatu/Downloads"  # 감시할 폴더

#     app = QApplication(sys.argv)
#     window = MainWindow(watch_path)
#     window.show()
#     sys.exit(app.exec_())