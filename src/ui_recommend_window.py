from PyQt5.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, QStackedLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QFile, QTextStream, QSize
from PyQt5.QtGui import QCursor, QMovie, QPainter, QLinearGradient, QColor, QBrush
import sys
from pynput import keyboard
import platform
from enum import Enum

COMBO = {keyboard.Key.shift, keyboard.Key.space} # 팝업 이벤트 핫키
COMBO2 = {keyboard.Key.cmd, keyboard.Key.shift} # 닫기 이벤트 핫키
COMBO3 = {keyboard.Key.ctrl, keyboard.KeyCode.from_char('c')} # dummy 이벤트(llm 응답 옴) 발생을 위한 핫키
COMBO4 = {keyboard.Key.ctrl, keyboard.KeyCode.from_char('v')} # dummy 이벤트(opeation 수행됨) 발생을 위한 핫키

PATH_RESOURCE = "./resource/"
PATH_STYLE_SHEET = "recommend_style.qss"


class GlobalHotKeyThread(QThread):
    hotkey_pressed = pyqtSignal()
    close_pressed = pyqtSignal()

    event_llm_response = pyqtSignal(str, list) # 파일명, 추천 경로 목록
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

    def __chcek_recommend(self):
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
        elif self.__chcek_recommend():
            self.event_llm_response.emit("파일명", ['경로1', '경로2', '경로3'])
    
    def __on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)

class SelectFilesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("SelectFilesWindow")

        

class SelectableItemWidget(QWidget):
    def __init__(self, path, select_callback):
        super().__init__()
        self.setObjectName("SelectableItemWidget")
        self.layout = QHBoxLayout(self)
        self.label = QLabel(path)
        self.path = path

        self.select_btn = QPushButton(">")
        self.select_btn.setObjectName("BtnSelectRecommend")
        self.select_btn.setFixedWidth(40)
        self.layout.addWidget(self.label, stretch=1)
        self.layout.addWidget(self.select_btn)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.select_callback = select_callback
        self.select_btn.clicked.connect(lambda: self.select_callback(self))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.select_callback(self)
            
    def showEvent(self, event):
        parent = self.parentWidget()
        if parent:
            parent_width = parent.width()
             
            self.setMaximumWidth(parent_width)  # 예시
        super().showEvent(event)

    def text(self):
        return self.path

class SelectPathWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("SelectPathWindow")
        self.layout = QVBoxLayout(self)
        self.name_label = QLabel()
        
        self.list_widget = QListWidget()
        self.list_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        


        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.list_widget)
        self.set_recommend("testfile.py", ["/home/user/projects/my-app", "/var/www/html/portfolio", "C:\\Users\\Alice\\Documents\\Work\\Reports"])

    def __add_item(self, path):
        item_widget = QListWidgetItem()
        widget = SelectableItemWidget(path, self.__select_item)
        item_widget.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item_widget)
        self.list_widget.setItemWidget(item_widget, widget)
    
    def __select_item(self, item):
        print(item.text())
        # self.list_widget.clear()

    def __clear_all(self):
        self.name_label.setText("")

    def set_recommend(self, filename, recommend_dirs):
        self.__clear_all()
        self.name_label.setText(filename + " to ..")
        for path in recommend_dirs:
            self.__add_item(path)
        
        

class RecommendWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("RecommendWindow")
        self.isWinsOs = (platform.system() == "Windows")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        self.width = 300
        self.height = 400
        self.resize(self.width, self.height)


        self.__listener_thread = GlobalHotKeyThread()
        self.__listener_thread.hotkey_pressed.connect(self.__display_window)
        self.__listener_thread.close_pressed.connect(self.close)

        # self.__listener_thread.event_completed_operation.connect(self.__on_operation_response)
        # self.__listener_thread.event_llm_response.connect(self.__on_llm_response)

        self.__listener_thread.start()
        QApplication.instance().aboutToQuit.connect(self.__listener_thread.quit)


        self.layout = QStackedLayout(self)
        self.layout.addWidget(SelectPathWindow())
        
        self.__load_stylesheet(PATH_RESOURCE + PATH_STYLE_SHEET)


    def __submit(self):
        pass

    def __display_window(self):
        if self.isVisible():
            self.hide()
            return
        # def show():
        #     self.__move_window()
        #     self.show()
        #     self.raise_()
        #     self.activateWindow()

        self.__move_window()
        self.show()
        self.raise_()
        self.activateWindow()
        # QTimer.singleShot(50, show)
    
    def __cancle_response(self):
        print("cancle")

    def __run_operation(self):  
        print("run")

    def __move_window(self): 
        mouse_pos = QCursor.pos()
        screen = QApplication.screenAt(mouse_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        
        screen_geometry = screen.availableGeometry()
        
        self.move(
            screen_geometry.x() + screen_geometry.width() - self.width,
            screen_geometry.y() + screen_geometry.height() - self.height
        )
    
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
    window = RecommendWindow()
    sys.exit(app.exec_())
