from typing import Callable
from event_hub import AppEvent, EventHub
from ui_main_windows import MainWindow
from ui_quick_window import InstantWindow
from ui_recommend_window import RecommendWindow
from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSlot, QMetaObject
from PyQt5.QtWidgets import QApplication
from file_manager_core import FileManagerCore
from hotkey_manager import HotKeyManager
import sys
from pynput import keyboard
from typing import List
COMBO = {keyboard.Key.shift, keyboard.Key.space} # 팝업 이벤트 핫키
"""
이벤트 목록
    1. 메인 윈도우 오픈 -> UI
    2. 백그라운드 시작
    3. 백그라운드 종료
    4. 창닫기 (백그라운드 상태 포함한) -> UI

    5. 인스턴트 윈도우 오픈 -> UI
    6. 명령어 입력
    7. 명령어 응답 전송
    8. 명령어 실행 요청
    9. 명령 수행 완료 -> UI, backend

    10. 관심 디렉토리 내 파일 생성 알림 (추천 경로 포함)  -> UI, backend
    11. move 요청

    12. 핫키 입력 -> UI

class AppEvent:
    target: str
    event: str
    data: object
"""


class UIManager(QObject):
    """
    그래픽 사용자 인터페이스(GUI) 요소들을 관리하고 사용자와의 상호작용을 처리합니다.
    """

    def __init__(self):
        super().__init__()
        # self.app = QApplication(sys.argv)
        self.setObjectName("ui")
        self.event_hub = EventHub.get_global_instance()
        self.window_main = MainWindow()
        self.window_instant = InstantWindow()
        self.window_recoomend = RecommendWindow()
        self.backend = FileManagerCore()
        self.hotkey = HotKeyManager()
        self.hotkey.add(COMBO, self.event_hub.input_opened.emit)
        self.hotkey.start()
        QApplication.instance().aboutToQuit.connect(self.hotkey.quit)
        self.backend_thread = QThread()
        self.backend.moveToThread(self.backend_thread)
        self.core_state = False

        QMetaObject.connectSlotsByName(self)
        self.event_hub.window_opened.connect(self.on_window_opened)
        self.event_hub.input_opened.connect(self.on_input_opened)
        self.event_hub.state_responded_from_core.connect(self.on_state_responded_from_core)
        # self.event_hub.command_responded_from_core.connect(self.on_command_responded_from_core)
        self.event_hub.operation_responded_from_core.connect(self.on_operation_responded_from_core)
        self.event_hub.suggestion_responded_from_core.connect(self.on_suggestion_responded_from_core)
        self.event_hub.suggestion_opperated_from_core.connect(self.on_suggestion_opperated_from_core)
        self.event_hub.undo_responded_from_core.connect(self.on_undo_responded_from_core)
        self.event_hub.history_responded_from_core.connect(self.on_history_responded_from_core)

        
    def run(self):
        """
        UI 시작
        """
        self.event_hub.window_opened.emit()
        print("run")
        # self.event_hub.event.emit(AppEvent("CoreRun", None))

    @pyqtSlot()
    def on_window_opened(self):
        self.window_main.show()
    
    # @pyqtSlot
    def on_input_opened(self):
        if not self.core_state:
            return
        self.window_instant.display_window()

    # @pyqtSlot
    def on_state_responded_from_core(self, state: bool):
        self.core_state = state # 싱크 안맞을 가능성이  있긴함.
        self.window_main.toggle(self.core_state) # 구현
    
    # @pyqtSlot
    def on_command_responded_from_core(self, err: bool, actions: List[str], explanation: str, feature: str):
        if not self.core_state:
            return
        # self.window_instant.on_llm_response(err, actions, explanation, feature)# 수정
    
    # @pyqtSlot
    def on_operation_responded_from_core(self, err: bool, message: str):
        if not self.core_state:
            return
        self.window_instant.on_operation_response(err, message)

    # @pyqtSlot
    def on_suggestion_responded_from_core(self, err: bool, src: str, dest: List[str], reason: List[str]):
        if not self.core_state:
            return
        pass
        # self.window_recoomend.on_recommned(err, src, dest, reason)
    
    # @pyqtSlot
    def on_suggestion_opperated_from_core(self, err: bool, message: str):
        if not self.core_state:
            return
        print(err, message)
    
    def on_undo_responded_from_core(self, err: bool, message: str):
        print(err, message)
    
    def on_history_responded_from_core(self, history: list):
        print(history)
        self.window_main.window_content.history.update_history(history)
            



"""
    --------
    창 생성/닫기
    메인
        코어 시작 -> 코어 답변
        히스토리 요청
    인풋
        커맨드 전송, 커맨드 응답, 커맨드 수행, 커맨드 결과
    추천
        경로 선택 + 함께 전송되는 파일
내부에서 구현
    CoreReqHistory: History 요청

    CoreReqCommand: command 제출
"""
if __name__ == "__main__":
    # print("hello")
    app = QApplication(sys.argv)

    # print("app")
    ui = UIManager()

    # print("ui")
    ui.run()
    # print("run")

    sys.exit(app.exec_())