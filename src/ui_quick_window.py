from PyQt5.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QFile, QTextStream
from PyQt5.QtGui import QCursor
import sys
from pynput import keyboard
import platform
from enum import Enum

class LifeCycle(Enum):
    TYPING = 0 # 사용자로부터 입력을 받는 상태
    SUBMITTED = 1 # 사용자 입력을 LLM에게 제출한 상태
    RESPONDED = 2 # LLM으로 부터 응답이 온 상태
    OPERATING = 3 # 사용자가 동작을 수락하고 동작중인 상태

COMBO = {keyboard.Key.shift, keyboard.Key.space}
COMBO2 = {keyboard.Key.cmd, keyboard.Key.shift}

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

class ScrollableLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setObjectName("ScrollableLabel")
        self.setWordWrap(True)
        # self.setAttribute(Qt.WA_StyledBackground, True)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setMinimumHeight(5)
        self.scroll.setMaximumHeight(80)
        self.scroll.setFocusPolicy(Qt.NoFocus)
    
    def get_scroll(self):
        return self.scroll

class LLMStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("LLMStatusWidget")

        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)

        self.message = ScrollableLabel()
        self.feature = ScrollableLabel()

        form_btn = QWidget()

        layout_btn = QHBoxLayout(form_btn)

        self.btn_cancle = FocusableBtn("Cancle")
        self.btn_ok = FocusableBtn("Ok")

        self.btn_cancle.setEnabled(False)
        self.btn_ok.setEnabled(False)

        layout_btn.addWidget(self.btn_cancle, stretch=1)
        layout_btn.addWidget(self.btn_ok, stretch=2)
        
        self.btn_ok.clicked.connect(self.hide)

        layout.addWidget(QLabel("LLM Response"))
        layout.addWidget(self.message.get_scroll())
        layout.addWidget(QLabel("Features"))
        layout.addWidget(self.feature.get_scroll()) 
        layout.addWidget(form_btn)

    
class InstantWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.state = LifeCycle.TYPING
        self.isWinsOs = (platform.system() == "Windows")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.listener_thread = GlobalHotKeyThread()
        self.listener_thread.hotkey_pressed.connect(self.display_window)
        self.listener_thread.close_pressed.connect(self.close)
        self.listener_thread.start()
        QApplication.instance().aboutToQuit.connect(self.listener_thread.quit)


        layout = QVBoxLayout(self)
        self.input = QuickInput()
        self.output = QWidget()
        # self.input.closed.connect()
        layout.addWidget(self.input)
        layout.addWidget(LLMStatusWidget())
        
        # self.resize(400, 500) 
        
        self.__load_stylesheet(PATH_STYLE_SHEET)
        # 포커스 변경 감지
        QApplication.instance().focusChanged.connect(self.__on_focus_change)
    
    def __submit(self):
        print(self.input.text()) 
        # 라이프 사이클 관리 추가 해야 함.

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
