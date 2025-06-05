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

COMBO = {keyboard.Key.shift, keyboard.Key.space}
COMBO2 = {keyboard.Key.cmd, keyboard.Key.shift}

PATH_RESOURCE = "./resource/"
PATH_STYLE_SHEET = "quick_style.qss"


class GlobalHotKeyThread(QThread):
    hotkey_pressed = pyqtSignal()
    close_pressed = pyqtSignal()
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
    
    def __on_press(self, key):
        self.current_keys.add(key)
        if self.__check_hot_key():
            self.hotkey_pressed.emit()
        elif self.__check_close():
            self.close_pressed.emit()
    
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
        self.__clear_paint()
        self.__is_loading = 0
        self.update()

    def __clear_paint(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        base_color = QColor(255, 255, 255, 0)
        painter.fillRect(self.rect(), base_color)

    def paintEvent(self, event):
        if not self.__is_loading:
            super().paintEvent(event)
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

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

        layout = QVBoxLayout(self)

        self.message = ResponseLabel()
        self.feature = ResponseLabel()

        form_btn = QWidget()

        layout_btn = QHBoxLayout(form_btn)

        self.btn_cancle = FocusableBtn("Cancle")
        self.btn_ok = FocusableBtn("Ok")

        layout_btn.addWidget(self.btn_cancle, stretch=1)
        layout_btn.addWidget(self.btn_ok, stretch=2)

        layout.addWidget(QLabel("LLM Response"))
        layout.addWidget(self.message.get_scroll())
        layout.addWidget(QLabel("Features"))
        layout.addWidget(self.feature.get_scroll()) 
        layout.addWidget(form_btn)

        self.__clear()
    
    def set_clicked_action_cancle(self, func):
        self.btn_cancle.clicked.connect(func)

    def set_clicked_action_ok(self, func):
        self.btn_ok.clicked.connect(func)

    def __clear(self):
        # self.btn_ok.setEnabled(False)
        self.message.setText("")
        self.feature.setText("")

    def set_response(self, message, feature):
        self.message.setText(message)
        self.message.setText(feature)
    
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
        self.listener_thread = GlobalHotKeyThread()
        self.listener_thread.hotkey_pressed.connect(self.display_window)
        self.listener_thread.close_pressed.connect(self.close)
        self.listener_thread.start()
        QApplication.instance().aboutToQuit.connect(self.listener_thread.quit)


        self.layout = QVBoxLayout(self)
        self.input = QuickInput()
        self.output = QWidget()
        # self.input.closed.connect()
        self.layout.addWidget(self.input)
        
        self.__load_stylesheet(PATH_RESOURCE + PATH_STYLE_SHEET)
        # 포커스 변경 감지
        QApplication.instance().focusChanged.connect(self.__on_focus_change)


    def __update_cycle(self, next_state, **kwargs):
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
        
        if self.__state == LifeCycle.SUBMITTED:
            self.__add_status_widget()
            QTimer.singleShot(5, lambda: self.input.setEnabled(False))
            self.status_widget.set_btn_enabled(True, False)
            return
    
        if self.status_widget is None:
            self.__update_cycle(LifeCycle.TYPING)

        if self.__state == LifeCycle.RESPONDED:
            self.status_widget.set_response(kwargs['message'], kwargs['feature'])
            self.status_widget.set_btn_enabled(True, True)
            
        if self.__state == LifeCycle.OPERATING:
            self.status_widget.set_btn_enabled(False, False)
        if self.__state == LifeCycle.OPERATED:
            self.status_widget.set_btn_enabled(False, True)
        

    def __submit(self):
        self.__update_cycle(LifeCycle.SUBMITTED)

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
        elif event.key() == Qt.Key_Return:
            self.__submit()
        else:
            super().keyPressEvent(event)  
    
    def set_response(self, message, feature):
        self.__update_cycle(LifeCycle.RESPONDED, message, feature)
        


    def __add_status_widget(self): 
        self.status_widget = LLMStatusWidget()
        self.status_widget.set_clicked_action_cancle(self.__cancle_response)
        self.layout.addWidget(self.status_widget)
    
    def __cancle_response(self):
        self.__update_cycle(LifeCycle.TYPING)
        
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
