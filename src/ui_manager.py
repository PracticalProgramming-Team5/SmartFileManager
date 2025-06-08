from typing import Callable
from event_hub import AppEvent, EventHub
from ui_main_windows import MainWindow
from ui_quick_window import InstantWindow
from ui_recommend_window import RecommendWindow
from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSlot
from PyQt5.QtWidgets import QApplication
from file_manager_core import FileManagerCore
from hotkey_manager import HotKeyManager
import sys
from pynput import keyboard
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
        self.event_hub = EventHub()
        self.window_main = MainWindow(self.event_hub)
        self.window_instant = InstantWindow(self.event_hub)
        self.window_recoomend = RecommendWindow(self.event_hub)
        self.backend = FileManagerCore(self.event_hub)
        self.hotkey = HotKeyManager(self.event_hub)
        self.hotkey.add("UiOpenInstantWin", COMBO)
        self.hotkey.start()
        QApplication.instance().aboutToQuit.connect(self.hotkey.quit)
        self.backend_thread = QThread()
        self.backend.moveToThread(self.backend_thread)
        self.event_hub.event.connect(self.__process_event)
        self.core_state = False
        print(self.event_hub)
    def run(self):
        """
        UI 시작
        """
        self.event_hub.event.emit(AppEvent("UiOpenMainWin", None))
        # self.event_hub.event.emit(AppEvent("CoreRun", None))
    
    # @pyqtSlot(object)
    def __process_event(self, event: AppEvent):
        print("front:", event.name)
        if event.name == "UiOpenMainWin": # 메인 윈도우 열기
            QTimer.singleShot(100, self.window_main.show)
        elif event.name == "UiCloseMainWin": # 메인 윈도우 닫기
            self.window_main.hide()
        elif event.name == "UiOpenInstantWin": # 인풋 윈도우 열기
            self.window_instant.display_window()
        # elif event.name == "UiCloseInstantWin": # 인풋 윈도우 닫기
        #     self.window_instant.hide()
        elif event.name == "UiOpenRecommendWin": # 추천 윈도우 열기
            self.window_recoomend.show()
        # elif event.name == "UiCloseRecommendWin": # 추천 윈도우 닫기
        #     self.window_recoomend.hide()



        elif event.name == "UiResCoreState": # 코어 상태 업데이트(T/F)
            self.core_state = event.data # 싱크 안맞을 가능성이  있긴함.
            self.window_main.toggle(self.core_state)
        elif event.name == "UiResHistory": # 히스토리 결과 도착
            pass
        elif event.name == "UiResCommand": # 커맨드 요청에 대한 LLM 응답
            self.window_instant.on_llm_response(data=event.data)
        elif event.name == "UiResOper": # 커맨드 수행 요청에 대한 결과 도착
            message = "수행 완료." if event.data is None else event.data
            self.window_instant.on_operation_response(message=message)
        elif event.name == "UiAddFile": # 파일 제안 이벤트 도착
            self.window_recoomend.on_recommned(recommend=event.data)
        elif event.name == "UiResFile": # 파일 제안 수락 결과
            print(event.data)



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

    app = QApplication(sys.argv)
    ui = UIManager()
    ui.run()

    sys.exit(app.exec_())