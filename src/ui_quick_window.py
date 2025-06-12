from PyQt5.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QFile, QTextStream, QSize
from PyQt5.QtGui import QCursor, QMovie, QPainter, QLinearGradient, QColor, QBrush
from context_type import ActionCommand, ActionMove, ActionCommandList
import sys
from pynput import keyboard
import platform
from enum import Enum
from event_hub import AppEvent, EventHub
from typing import List

PATH_RESOURCE = "./resource/"
PATH_STYLE_SHEET = "quick_style.qss"

class LifeCycle(Enum):
    TYPING = 0 # 사용자로부터 입력을 받는 상태
    SUBMITTED = 1 # 사용자 입력을 LLM에게 제출한 상태
    RESPONDED = 2 # LLM으로 부터 응답이 온 상태
    OPERATING = 3 # 사용자가 동작을 수락하고 동작중인 상태
    OPERATED = 4 # 동작이 완료된 상태

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
        self.event_hub = EventHub.get_global_instance()

        self.status_widget = None
        # self.__listener_thread = GlobalHotKeyThread()
        # self.__listener_thread.hotkey_pressed.connect(self.__display_window)
        # self.__listener_thread.close_pressed.connect(self.close)
        # self.__listener_thread.event_completed_operation.connect(self.__on_operation_response)
        # self.__listener_thread.event_llm_response.connect(self.__on_llm_response)

        # self.__listener_thread.start()
        # QApplication.instance().aboutToQuit.connect(self.__listener_thread.quit)


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
            print(self.input.text())
            # self.event_hub.event.emit(AppEvent("CoreReqCommand", self.input.text()))
            self.event_hub.command_requested_from_ui.emit(self.input.text())
            return
    
        if self.status_widget is None:
            self.__update_cycle(self.__state, LifeCycle.TYPING)

        if cur_state == LifeCycle.SUBMITTED and next_state == LifeCycle.RESPONDED:
            if [param for param in ("err", "action", "explanation", 'feature') if param not in kwargs]:
                self.__update_cycle(self.__state, LifeCycle.TYPING)
                return
            err = kwargs['err']
            action = kwargs['action']
            explanation = kwargs['explanation']
            feature = kwargs['feature']
            
            self.status_widget.set_message(explanation)
            if feature:
                self.status_widget.set_feature(feature)
                self.status_widget.show_feature()
            if err:
                self.status_widget.set_btn_enabled(False, True)
                self.status_widget.set_clicked_action_ok(self.__cancle_response)
            else:
                self.status_widget.set_btn_enabled(True, True)
                self.status_widget.set_clicked_action_ok(lambda: self.__run_operation(action, explanation))
            return
            
        if cur_state == LifeCycle.RESPONDED and next_state == LifeCycle.OPERATING:
            # self.__dummy_focus.setFocusPolicy(Qt.StrongFocus)
            # self.__dummy_focus.setFocus()
            if [param for param in ("action", "explanation") if param not in kwargs]:
                self.__update_cycle(self.__state, LifeCycle.TYPING)
                return
            
            action = kwargs['action']
            explanation = kwargs['explanation']
            
            self.status_widget.set_btn_enabled(False, False)
            self.status_widget.show_result()
            self.event_hub.operation_requested_from_ui.emit(action, explanation)
            return
        
        if cur_state == LifeCycle.OPERATING and next_state == LifeCycle.OPERATED:

            if [param for param in ("err", "message") if param not in kwargs]:
                self.__update_cycle(self.__state, LifeCycle.TYPING)
                return
            err = kwargs['err']
            message = kwargs['message']

            self.status_widget.set_result(message)
            if err:
                self.status_widget.set_btn_enabled(False, True)
            else:
                self.status_widget.set_btn_enabled(True, True)
                self.status_widget.btn_cancle.setText("undo")
                self.status_widget.btn_cancle.clicked.connect(self.event_hub.undo_requested_from_ui.emit)
                self.status_widget.update()
            self.status_widget.set_clicked_action_ok(self.__cancle_response)
            return
        
        self.__update_cycle(self.__state, LifeCycle.TYPING)

    def __submit(self):
        self.__update_cycle(self.__state, LifeCycle.SUBMITTED)

    def display_window(self):

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

    def __run_operation(self, action: List[str], explanation: str):  
        print("run")
        self.__update_cycle(self.__state, LifeCycle.OPERATING, action=action, explanation=explanation)

    def on_llm_response(self, err: bool, action: List[str], explanation: str, feature: str):
        self.__update_cycle(self.__state, LifeCycle.RESPONDED, err=err, action=action, explanation=explanation, feature=feature)
    
    def on_operation_response(self, err: bool, message: str):
        print("completed")
        self.__update_cycle(self.__state, LifeCycle.OPERATED, err=err, message=message)

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
