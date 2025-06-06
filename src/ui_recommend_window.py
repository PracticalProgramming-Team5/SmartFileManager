from PyQt5.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, QStackedLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QFile, QTextStream, QSize
from PyQt5.QtGui import QCursor, QMovie, QPainter, QLinearGradient, QColor, QBrush, QFontMetrics
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

class ScrollingLabel(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setObjectName("ScrollingLabel")
        self.text = text
        self.scroll_pos = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_scroll)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover)

    def enterEvent(self, event):
        if self.text_too_long():
            self.timer.start(15)
        return super().enterEvent(event)

    def leaveEvent(self, event):
        self.timer.stop()
        self.scroll_pos = 0
        self.update()
        return super().leaveEvent(event)

    def text_too_long(self):
        fm = QFontMetrics(self.font())
        return fm.width(self.text) > self.width()

    def update_scroll(self):
        self.scroll_pos += 1
        fm = QFontMetrics(self.font())
        if self.scroll_pos > fm.width(self.text) + 48:
            self.scroll_pos = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor(255, 255, 255))
        fm = QFontMetrics(self.font())

        text_width = fm.width(self.text)
        height = self.height()

        if text_width <= self.width():
            painter.drawText(4, height // 2 + fm.ascent() // 2, self.text)
        else:
            x = -self.scroll_pos
            while x < self.width():
                painter.drawText(x+4, height // 2 + fm.ascent() // 2, self.text)
                x += text_width + 50

        painter.end()
    
    def setText(self, text):
        self.text = text
        QTimer.singleShot(10, self.update)

class GlobalHotKeyThread(QThread):
    hotkey_pressed = pyqtSignal()
    close_pressed = pyqtSignal()

    event_recomend = pyqtSignal(str, list) # 파일명, 추천 경로 목록
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
            self.event_recomend.emit("아아아아아아아아아아아아아아아아아아아아아아아주 긴 파일 명", ['동해물과 백두산이 마르고 닳도록 하느님이 보우하사 우리나라', '동해물과 백두산이 마르고', '닳도록 하는님이 봉후ㅏ사 우리나라 만세 무궁화 삼천리 화려강산'])
            # self.hotkey_pressed.emit()
            # self.event_recomend.emit("파일명", ['경로1', '경로2', '경로3'])
        elif self.__check_close():
            self.close_pressed.emit()
        elif self.__chcek_recommend():
            self.event_recomend.emit("파일명", ['경로1', '경로2', '경로3'])
    
    def __on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)

class SelectRelatedFilesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("SelectRelatedFilesWindow")

        

class SelectableItemWidget(QWidget):
    def __init__(self, path, select_callback):
        super().__init__()
        self.setObjectName("SelectableItemWidget")
        self.layout = QHBoxLayout(self)
        self.label = ScrollingLabel(path)
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
            self.setMaximumWidth(parent_width)
        super().showEvent(event)

    def get_path(self):
        return self.path

class SelectRecommendWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("SelectRecommendWindow")
        self.layout = QVBoxLayout(self)
        self.name_label = ScrollingLabel()
        self.name_label.setMinimumHeight(15)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(10)
        self.list_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.selected_callback = lambda: None
        self.selected_path = None
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.list_widget)

        self.layout.setContentsMargins(0, 11, 0, 0)
        # self.layout.addWidget(ScrollingLabel("asdasf"))
    def __add_item(self, path):
        item_widget = QListWidgetItem()
        widget = SelectableItemWidget(path, self.__select_item)
        item_widget.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item_widget)
        self.list_widget.setItemWidget(item_widget, widget)
    
    def __select_item(self, item):
        self.selected_path = item.get_path()
        self.selected_callback()

    def __clear_all(self):
        self.name_label.setText("")
        self.selected_path = None
        self.list_widget.clear()
    
    def set_selected_callback(self, func):
        self.selected_callback = func
    
    def set_recommend(self, filename, recommend_dirs):
        self.__clear_all()
        self.name_label.setText(filename + " to ..")
        for path in recommend_dirs:
            self.__add_item(path)
    
    def get_selected_path(self):
        return self.selected_path
        

class RecommendWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("RecommendWindow")
        self.isWinsOs = (platform.system() == "Windows")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # self.width = self.width()
        # self.height = self.height()
        self.resize(268, 295)
        # self.setFixedWidth(300)



        self.__listener_thread = GlobalHotKeyThread()
        self.__listener_thread.hotkey_pressed.connect(self.__display_window)
        self.__listener_thread.close_pressed.connect(self.close)
        self.__listener_thread.event_recomend.connect(self.__recommned)

        # self.__listener_thread.event_completed_operation.connect(self.__on_operation_response)
        # self.__listener_thread.event_recomend.connect(self.__on_llm_response)

        self.__listener_thread.start()
        QApplication.instance().aboutToQuit.connect(self.__listener_thread.quit)
        self.btn_cancle = QPushButton("Cancle")
        self.btn_cancle.setObjectName("CancleBtn")
        self.btn_cancle.clicked.connect(self.__cancle_response)

        self.select_recommend_widget = SelectRecommendWindow()
        self.select_related_widget = SelectRelatedFilesWindow()
        
        self.select_recommend_widget.set_selected_callback(self.__selected)
        
        
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(0, 11, 0, 0)
        self.layout_main.setSpacing(0)

        
        self.form_stack = QWidget()
        self.form_stack.setObjectName("form")
        self.layout_stack = QStackedLayout(self.form_stack)
        # self.form_stack.setStyleSheet("background-color: red;")


        self.layout_stack.addWidget(self.select_recommend_widget)
        self.layout_stack.addWidget(self.select_related_widget)
        
        self.layout_stack.setCurrentIndex(0)
        self.__load_stylesheet(PATH_RESOURCE + PATH_STYLE_SHEET)
        self.layout_main.addWidget(QLabel("📁 File Manager"))
        self.layout_main.addWidget(self.form_stack)
        self.layout_main.addWidget(self.btn_cancle)

    def __selected(self):
        self.layout_stack.setCurrentIndex(1)
        print(self.select_recommend_widget.get_selected_path())


    def __recommned(self, filename, dirs):
        if not self.isVisible():
            self.select_recommend_widget.set_recommend(filename, dirs)
        QTimer.singleShot(1, self.__display_window)

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
        self.hide()

    def __run_operation(self):  
        print("run")

    def __move_window(self): 
        mouse_pos = QCursor.pos()
        screen = QApplication.screenAt(mouse_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        
        screen_geometry = screen.availableGeometry()
        
        self.move(
            screen_geometry.x() + screen_geometry.width() - self.width(),
            screen_geometry.y() + screen_geometry.height() - self.height()
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
