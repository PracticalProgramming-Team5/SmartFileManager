from PyQt5.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QFile, QTextStream, QSize
from PyQt5.QtGui import QCursor, QMovie, QPainter, QLinearGradient, QColor, QBrush
import sys
from pynput import keyboard
import platform
from enum import Enum

class LifeCycle(Enum):
    TYPING = 0 # 사용자로부터 입력을 받는 상태
    SUBMITTED = 1 # 사용자 입력을 LLM에게 제출한 상태
    RESPONDED = 2 # LLM으로 부터 응답이 온 상태
    OPERATING = 3 # 사용자가 동작을 수락하고 동작중인 상태
    OPERATED = 4 # 동작이 완료된 상태

COMBO = {keyboard.Key.shift, keyboard.Key.space} # 팝업 이벤트 핫키
COMBO2 = {keyboard.Key.cmd, keyboard.Key.shift} # 닫기 이벤트 핫키
COMBO3 = {keyboard.Key.ctrl, keyboard.KeyCode.from_char('c')} # dummy 이벤트(llm 응답 옴) 발생을 위한 핫키
COMBO4 = {keyboard.Key.ctrl, keyboard.KeyCode.from_char('v')} # dummy 이벤트(opeation 수행됨) 발생을 위한 핫키

PATH_RESOURCE = "./resource/"
PATH_STYLE_SHEET = "quick_style.qss"


class GlobalHotKeyThread(QThread):
    hotkey_pressed = pyqtSignal()
    close_pressed = pyqtSignal()

    event_llm_response = pyqtSignal(bool, str, str) # 요청 성공 여부, 동작 요약 메시지, 추가 정보
    event_completed_operation = pyqtSignal(bool, str) # 동작 수행 여부, 설명
    current_keys = set()
    
    
    def run(self):
        with keyboard.Listener(on_press=self.__on_press, on_release=self.__on_release) as listener:
            listener.join()

    def __check_hot_key(self):
        if all(k in self.current_keys for k in COMBO):
            return True
        return False
    
    def __check_close(self):
        if all(k in self.current_keys for k in COMBO2):
            return True
        return False

    def __check_llm_response_event(self):
        if all(k in self.current_keys for k in COMBO3):
            return True
        return False
    
    def __check_oper_completed_event(self):
        if all(k in self.current_keys for k in COMBO4):
            return True
        return False
    
    def __on_press(self, key):
        self.current_keys.add(key)
        if self.__check_hot_key():
            self.hotkey_pressed.emit()
        elif self.__check_close():
            self.close_pressed.emit()
        elif self.__check_llm_response_event():
            self.event_llm_response.emit(True, "동작 설명 메시지.", "경고 메시지. 없으면 빈 문자열 제출")
        elif self.__check_oper_completed_event():
            self.event_completed_operation.emit(True, "명령 수행 결과 메시지.")
            # self.event_completed_operation.emit(True, "명령 수행중 다음 문제가 발생했습니다. 이런 저런 문제 발생.")
    
    def __on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)

class QuickInput(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setObjectName("QuickInput")
        self.setFixedHeight(50)
        self.setFixedWidth(600)
        self.setPlaceholderText("Type something...")
    
    def keyPressEvent(self, event):
        if self.text() and event.key() == Qt.Key_Escape:
            self.clear()
        else:
            super().keyPressEvent(event)

class FocusableBtn(QPushButton):
    def __init__(self, text):
        super().__init__()
        self.setObjectName("FocusableBtn")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setText(text)
        self.setDefault(True)

class ResponseLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setObjectName("ResponseLabel")
        self.setWordWrap(True)
        self.__is_loading = 0
        # self.setAttribute(Qt.WA_StyledBackground, True)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setFixedHeight(80)
        self.scroll.setFocusPolicy(Qt.NoFocus)

        self.offset = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.__update_animation)
        self.__start_animation()

    def __update_animation(self):
        self.offset += 10
        if self.offset > self.width():
            self.offset = -self.width() - 300
        self.update()
    
    def __start_animation(self):
        self.__is_loading = 1
        self.timer.start(10)

    def __stop_animation(self):
        self.timer.stop()
        self.__is_loading = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.__is_loading:
            base_color = QColor(255, 255, 255, 0)
            painter.fillRect(self.rect(), base_color)
            super().paintEvent(event)
            return
        
        grad = QLinearGradient(self.offset, 0, self.offset + 300, 0)
        grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.5, QColor(125, 125, 125, 50))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))

        brush = QBrush(grad)

        painter.fillRect(self.rect(), brush)

    def setText(self, text):
        if text:
            self.__stop_animation()
        super().setText(text)


    def get_scroll(self):
        return self.scroll

class LLMStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("LLMStatusWidget")

        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QVBoxLayout(self)

        self.form_message = QWidget()
        self.form_feature = QWidget()
        self.form_result = QWidget()

        self.layout_message = QVBoxLayout(self.form_message)
        self.layout_feature = QVBoxLayout(self.form_feature)
        self.layout_result = QVBoxLayout(self.form_result)

        self.message = ResponseLabel()
        self.feature = ResponseLabel()
        self.result = ResponseLabel()

        self.form_btn = QWidget()

        layout_btn = QHBoxLayout(self.form_btn)

        self.btn_cancle = FocusableBtn("Cancle")
        self.btn_ok = FocusableBtn("Ok")

        layout_btn.addWidget(self.btn_cancle, stretch=1)
        layout_btn.addWidget(self.btn_ok, stretch=2)
        
        self.layout_message.addWidget(QLabel("LLM Response"))
        self.layout_message.addWidget(self.message.get_scroll())

        self.layout_feature.addWidget(QLabel("Features"))
        self.layout_feature.addWidget(self.feature.get_scroll()) 

        self.layout_result.addWidget(QLabel("Results"))
        self.layout_result.addWidget(self.result.get_scroll()) 

        self.form_feature.hide()
        self.form_result.hide()
        self.layout.addWidget(self.form_message)
        self.layout.addWidget(self.form_feature)
        self.layout.addWidget(self.form_result)
        self.layout.addWidget(self.form_btn)

        # 포커스 가능한 객체 모두 비활성화 될 때 포커스 아웃 방지용
        self.__dummy_btn = QPushButton()
        self.__dummy_btn.setFixedSize(0, 0)
        self.__dummy_btn.setFocusPolicy(Qt.StrongFocus)
        layout_btn.addWidget(self.__dummy_btn)

    def set_clicked_action_cancle(self, func):
        # disconnect 에러 발생 방지용임.
        self.btn_cancle.clicked.connect(func)
        self.btn_cancle.clicked.disconnect()
        self.btn_cancle.clicked.connect(func)

    def set_clicked_action_ok(self, func):
        self.btn_ok.clicked.connect(func)
        self.btn_ok.clicked.disconnect()
        self.btn_ok.clicked.connect(func)

    # def __clear(self): 
    #     self.message.setText("")
    #     self.feature.setText("")
    #     self.result.setText("")
    def __update(self):
        # self.updateGeometry()
        # self.adjustSize()
        # self.repaint()
        # 윈도우에서 테스트 한 뒤 삭제.
        pass
    def show_message(self):
        self.form_message.show()
        self.__update()
    
    def show_feature(self):
        self.form_feature.show()
        self.__update()
    
    def show_result(self):
        self.form_result.show()
        self.__update()

    def set_message(self, message):
        self.message.setText(message)

    def set_feature(self, feature):
        self.feature.setText(feature)

    def set_result(self, result):
        self.result.setText(result)
    
    def set_btn_enabled(self, btn_cancle, btn_ok):
        self.btn_cancle.setEnabled(btn_cancle)
        self.btn_ok.setEnabled(btn_ok)
        
class InstantWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.__state = LifeCycle.TYPING
        self.isWinsOs = (platform.system() == "Windows")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.status_widget = None
        self.__listener_thread = GlobalHotKeyThread()
        self.__listener_thread.hotkey_pressed.connect(self.__display_window)
        self.__listener_thread.close_pressed.connect(self.close)
        self.__listener_thread.event_completed_operation.connect(self.__on_operation_response)
        self.__listener_thread.event_llm_response.connect(self.__on_llm_response)

        self.__listener_thread.start()
        QApplication.instance().aboutToQuit.connect(self.__listener_thread.quit)


        self.layout = QVBoxLayout(self)
        self.input = QuickInput()
        self.output = QWidget()
        self.layout.addWidget(self.input)
        
        self.__load_stylesheet(PATH_RESOURCE + PATH_STYLE_SHEET)
        QApplication.instance().focusChanged.connect(self.__on_focus_change)


    def __update_cycle(self, cur_state, next_state, **kwargs):
        if self.__state == next_state:
            return
        self.__state = next_state

        if self.__state == LifeCycle.TYPING:
            self.input.setEnabled(True)
            if not self.status_widget is None:
                self.input.setFocus()
                self.status_widget.hide()

                self.updateGeometry()
                self.adjustSize()
                self.repaint()
                self.layout.removeWidget(self.status_widget)
                self.status_widget.deleteLater()
                self.status_widget = None
            return
        
        if cur_state == LifeCycle.TYPING and next_state == LifeCycle.SUBMITTED:
            self.__add_status_widget()
            QTimer.singleShot(5, lambda: self.input.setEnabled(False))
            self.status_widget.set_btn_enabled(True, False)
            return
    
        if self.status_widget is None:
            self.__update_cycle(self.__state, LifeCycle.TYPING)

        if cur_state == LifeCycle.SUBMITTED and next_state == LifeCycle.RESPONDED:
            if [param for param in ("status", 'message', 'feature') if param not in kwargs]:
                self.__update_cycle(self.__state, LifeCycle.TYPING)
                return
            
            status = kwargs['status']
            message = kwargs['message']
            feature = kwargs['feature']
            # if feature:
            #     print(feature) 
            self.status_widget.show_feature()
            if status:
                self.status_widget.set_message(message)
                QTimer.singleShot(5, lambda: self.status_widget.set_feature(feature))
                self.status_widget.set_btn_enabled(True, True)
                self.status_widget.set_clicked_action_ok(self.__run_operation)
            else:
                self.status_widget.set_message(message)
                self.status_widget.set_feature(feature)
                self.status_widget.set_btn_enabled(False, True)
                self.status_widget.set_clicked_action_ok(self.__cancle_response)
            

            return
            
        if cur_state == LifeCycle.RESPONDED and next_state == LifeCycle.OPERATING:
            # self.__dummy_focus.setFocusPolicy(Qt.StrongFocus)
            # self.__dummy_focus.setFocus()
            self.status_widget.set_btn_enabled(False, False)
            self.status_widget.show_result()
            print("작업 수행 요청")
            return
        
        if cur_state == LifeCycle.OPERATING and next_state == LifeCycle.OPERATED:

            if [param for param in ("status", 'result') if param not in kwargs]:
                self.__update_cycle(self.__state, LifeCycle.TYPING)
                return
            
            status = kwargs['status']
            result = kwargs['result']
            self.status_widget.set_result(result)
            self.status_widget.set_btn_enabled(False, True)
            self.status_widget.set_clicked_action_ok(self.__cancle_response)
            return
        
        self.__update_cycle(self.__state, LifeCycle.TYPING)

    def __submit(self):
        self.__update_cycle(self.__state, LifeCycle.SUBMITTED)

    def __display_window(self):

        if self.isVisible():
            self.hide()
            return
        def show():
            self.__move_window()
            self.show()
            self.raise_()
            self.activateWindow()
            self.input.setFocus()

        QTimer.singleShot(50, show)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif self.__state == LifeCycle.TYPING and event.key() == Qt.Key_Return:
            self.__submit()
        else:
            super().keyPressEvent(event)  

    def __add_status_widget(self): 
        self.status_widget = LLMStatusWidget()
        self.status_widget.set_clicked_action_cancle(self.__cancle_response)
        self.layout.addWidget(self.status_widget)
    
    def __cancle_response(self):
        print("cancle")
        self.__update_cycle(self.__state, LifeCycle.TYPING)

    def __run_operation(self):  
        print("run")
        self.__update_cycle(self.__state, LifeCycle.OPERATING)

    def __on_llm_response(self, status, message, feature):
        print("on response")
        self.__update_cycle(self.__state, LifeCycle.RESPONDED, status=status, message=message, feature=feature)
    
    def __on_operation_response(self, status, result):
        print("completed")
        self.__update_cycle(self.__state, LifeCycle.OPERATED, status=status, result=result)

    def __move_window(self): 
        mouse_pos = QCursor.pos()
        screen = QApplication.screenAt(mouse_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        
        screen_geometry = screen.availableGeometry()
        window_size = self.frameGeometry()

        
        self.move(
            screen_geometry.center().x() - window_size.width() // 2,
            screen_geometry.center().y()//2,
        )

    def __on_focus_change(self, old, now):
        if now is None or not self.isAncestorOf(now):
            self.hide()
    
    def __load_stylesheet(self, path):
        qss_file = QFile(path)
        qss_file.open(QFile.ReadOnly | QFile.Text)
        qss_stream = QTextStream(qss_file)
        self.setStyleSheet(qss_stream.readAll())
        qss_file.close()

    def closeEvent(self, event):
        QApplication.quit()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InstantWindow()
    sys.exit(app.exec_())
