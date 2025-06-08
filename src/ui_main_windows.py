import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, 
    QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedLayout, QButtonGroup,
    QScrollArea, QLineEdit, QFileDialog, QListWidget,
    QListWidgetItem)
from PyQt5.QtCore import QFile, QTextStream, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from event_hub import AppEvent, EventHub
from context_type import ActionCommand, ActionMove, ActionCommandList
from settings_manager import SettingsManager

SETTINGS_PATH = "./settings.json"

WIN_MIN_WIDTH = 800
WIN_MIN_HEIGHT = 600

PATH_RESOURCE = "./resource/"
PATH_STYLE_SHEET = "main_style.qss"

TAB_LIST = ["Home", "History", "Settings"]

FONT_SIZE_LARGE = 48

class SideBarElement(QPushButton):
    def __init__(self, text):
        super().__init__()
        self.name = text
        self.setObjectName("SideBarElement")
        self.setMinimumHeight(FONT_SIZE_LARGE + 10)
        self.setText(text)
        self.setCheckable(True)
    
    def set_clicked_action(self, func):
        # self.clicked.connect(lambda: func(self.name))
        self.clicked.connect(func)
    
    def get_name(self):
        return self.name

class MainWindowSideBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindowSideBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.elements = []
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        for tab in TAB_LIST:
            self.elements.append(SideBarElement(tab))
            layout.addWidget(self.elements[-1])
            self.elements[-1].clicked.connect(self.__clicked)
        self.elements[0].setChecked(True)
        layout.addStretch()
        self.setLayout(layout)

    def set_clicked_action(self, func):
        for element in self.elements:
            element.set_clicked_action(func)
    
    def __clicked(self):
        sender = self.sender()
        for element in self.elements:
            element.setChecked(False)
        sender.setChecked(True)

class ContentHome(QWidget):
    def __init__(self, event_hub):
        super().__init__()
        self.event_hub = event_hub
        self.setObjectName("ContentHome")
        self.setProperty("parent", "MainWindowContent")

        self.layout = QVBoxLayout()
        label = QLabel("Home")
        label.setObjectName("h1")
        self.layout.addWidget(label)

        self.btn = QPushButton("Run")
        self.btn.setObjectName("BtnStop")
        self.layout.addWidget(self.btn)
        self.btn.clicked.connect(self.__send)

        
        self.layout.addStretch()
        self.setLayout(self.layout)
        self.state = False
        # self.btn = self.layout.itemAt(1).widget()

        self.toggle(False)
        
    def toggle(self, state):
        self.state = state
        if state:
            self.btn.setText("Stop")
            self.btn.setObjectName("BtnStop")
        else:
            self.btn.setText("Run")
            self.btn.setObjectName("BtnRun")
        print(self.btn.objectName())
        self.btn.style().unpolish(self.btn)
        self.btn.style().polish(self.btn)

        self.btn.update()
    def get_state(self):
        return self.state
    
    def __send(self):
        if self.state:
            self.event_hub.event.emit(AppEvent("CoreStop", None))
        else:
            self.event_hub.event.emit(AppEvent("CoreRun", None))
    # def __set_background_control(self, func):
    #     self.layout.itemAt(1).widget().clicked.connect(func)
        

class ContentHistory(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("ContentHistory")

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setProperty("parent", "ContentHistory")

        self.scroll_area.setWidget(self.content_widget)
        self.content_layout = QVBoxLayout(self.content_widget)
        
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setObjectName("BtnNormal")
        self.btn_refresh.clicked.connect(self.__update_history)
        
        self.main_layout = QVBoxLayout(self)
        label = QLabel("History")
        label.setObjectName("h1")

        self.main_layout.addWidget(label)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.btn_refresh)
        
        self.__update_history()

    def __update_history(self):
        self.__clear_layout()
        history = [ # for test
            {
                "id":0,
                "date":"2025.06.01 13:12",
                "title":"Delete file A.",
                "detail":"Lorem Ipsum is simply dummy text of the printing and typesetting industry."
            },
            {
                "id":1,
                "date":"2025.06.01 13:15",
                "title":"Delete file A.",
                "detail":"Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book."
            },
            {
                "id":2,
                "date":"2025.06.01 13:23",
                "title":"Delete file A.",
                "detail":"It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum."
            },
            {
                "id":4,
                "date":"2025.06.01 18:01",
                "title":"Delete file A.",
                "detail":"Contrary to popular belief, Lorem Ipsum is not simply random text."
            },
            {
                "id":5,
                "date":"2025.06.01 19:59",
                "title":"Delete file A.",
                "detail":"Lorem Ipsum is simply dummy text of the printing and typesetting industry."
            },
            {
                "id":6,
                "date":"2025.06.02 15:04",
                "title":"Delete file A.",
                "detail":"It has roots in a piece of classical Latin literature from 45 BC, making it over 2000 years old. Richard McClintock, a Latin professor at Hampden-Sydney College in Virginia, looked up one of the more obscure Latin words, consectetur, from a Lorem Ipsum passage, and going through the cites of the word in classical literature, discovered the undoubtable source."
            },
            {
                "id":7,
                "date":"2025.06.02 18:05",
                "title":"Delete file A.",
                "detail":"Lorem Ipsum is simply dummy text of the printing and typesetting industry."
            },
            {
                "id":3,
                "date":"2025.06.02 19:55",
                "title":"Delete file A.",
                "detail":"Lorem Ipsum is simply dummy text of the printing and typesetting industry."
            },
        ]
        for job in history:
            id = job["id"]
            date = job["date"]
            title = job["title"]
            detail = job["detail"]

            widget = QWidget()
            layout = QVBoxLayout(widget)

            label_title = QLabel(title)
            label_date = QLabel(date)
            label_detail = QLabel(detail)
            
            label_title.setWordWrap(True)
            label_date.setWordWrap(True)
            label_detail.setWordWrap(True)

            layout.addWidget(label_title)
            layout.addWidget(label_date)
            layout.addWidget(label_detail)
            self.content_layout.addWidget(widget)

    def __clear_layout(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

class SettingsFormApiKey(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        
        input_form = QWidget()
        # input_form_layout = QHBoxLayout(input_form)
        # input_form_layout.addWidget(QLabel("발급받은 GPT-4o의 API KEY를 입력합니다."))
        # self.input = QLineEdit()
        
        # input_form_layout.addWidget(self.input)
        self.input = QLineEdit()
        self.input.setPlaceholderText("API KEY 입력")
        label = QLabel("API KEY")
        label.setObjectName("h2")
        layout.addWidget(label)
        FONT_SIZE_LARGE
        layout.addWidget(QLabel("발급받은 모델의 API KEY를 입력합니다."))
        layout.addWidget(self.input)

        self.__load_value()

    def __load_value(self):
        api_key = SettingsManager.get('api_key')
        self.input.setText(api_key)

    def get_value(self):
        return self.input.text()

class SettingsFormModelName(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        
        input_form = QWidget()
        # input_form_layout = QHBoxLayout(input_form)
        # input_form_layout.addWidget(QLabel("발급받은 GPT-4o의 API KEY를 입력합니다."))
        # self.input = QLineEdit()
        
        # input_form_layout.addWidget(self.input)
        self.input = QLineEdit()
        self.input.setPlaceholderText("모델명 입력")

        label = QLabel("Model Name")
        label.setObjectName("h2")
        layout.addWidget(label)
        layout.addWidget(QLabel("사용할 모델명을 입력합니다."))
        layout.addWidget(self.input)

        self.__load_value()

    def __load_value(self):
        model_name = SettingsManager.get('model_name')
        self.input.setText(model_name)

    def get_value(self):
        return self.input.text()

class PathItemWidget(QWidget):
    def __init__(self, path, remove_callback):
        super().__init__()
        layout = QHBoxLayout(self)
        label = QLabel(path)
        
        remove_btn = QPushButton("-")
        remove_btn.setObjectName("BtnRemove")
        remove_btn.setFixedWidth(26)
        remove_btn.setFixedHeight(26)
        layout.addWidget(remove_btn)
        layout.addWidget(label)
        layout.setContentsMargins(0, 0, 0, 0)
        remove_btn.clicked.connect(remove_callback)

    def text(self):
        return self.layout().itemAt(1).widget().text()

class SettingsFormMonitoringDirectory(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ListForm")
        self.list_widget.setMinimumHeight(100)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # self.list_widget.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        # self.list_widget.setWordWrap(False)

        btn_add = QPushButton("디렉토리 추가")
        btn_add.setObjectName("BtnNormal")
        btn_add.clicked.connect(self.__open_path_explorer)
        label = QLabel("Monitoring directories")
        label.setObjectName("h2")

        layout.addWidget(label)
        layout.addWidget(QLabel("파일 생성을 감시할 디렉토리를 설정합니다."))
        layout.addWidget(self.list_widget)
        layout.addWidget(btn_add)
        self.__load_value()
    
    def __open_path_explorer(self):
        dir_path = QFileDialog.getExistingDirectory(self, "디렉토리 추가", "")
        if not dir_path:
            return
        self.__add_item(dir_path)
    
    def __add_item(self, path):
        item_widget = QListWidgetItem()
        widget = PathItemWidget(path, lambda: self.__delete_item(item_widget))
        item_widget.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item_widget)
        self.list_widget.setItemWidget(item_widget, widget)
    
    def __delete_item(self, item):
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
    
    def __load_value(self):
        list_dir_path = SettingsManager.get('available_dirs')
        for path in list_dir_path:
            self.__add_item(path)

    def get_value(self):
        list_allowed_path = [self.list_widget.itemWidget(self.list_widget.item(i)).text() for i in range(self.list_widget.count())]
        return list_allowed_path

class SettingsFormAllowedDirectory(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ListForm")
        self.list_widget.setMinimumHeight(100)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # self.list_widget.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        # self.list_widget.setWordWrap(False)

        btn_add = QPushButton("디렉토리 추가")
        btn_add.setObjectName("BtnNormal")
        btn_add.clicked.connect(self.__open_path_explorer)
        
        label = QLabel("Allowed directories")
        label.setObjectName("h2")

        layout.addWidget(label)
        layout.addWidget(QLabel("LLM이 명령을 수행하면서 접근 가능한 디렉토리를 설정합니다."))
        layout.addWidget(self.list_widget)
        layout.addWidget(btn_add)
        self.__load_value()
    
    def __open_path_explorer(self):
        dir_path = QFileDialog.getExistingDirectory(self, "디렉토리 추가", "")
        if not dir_path:
            return
        self.__add_item(dir_path)
    
    def __add_item(self, path):
        item_widget = QListWidgetItem()
        widget = PathItemWidget(path, lambda: self.__delete_item(item_widget))
        item_widget.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item_widget)
        self.list_widget.setItemWidget(item_widget, widget)
    
    def __delete_item(self, item):
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
    
    def __load_value(self):
        list_dir_path = SettingsManager.get('available_dirs')
        for path in list_dir_path:
            self.__add_item(path)

    def get_value(self):
        list_allowed_path = [self.list_widget.itemWidget(self.list_widget.item(i)).text() for i in range(self.list_widget.count())]
        return list_allowed_path

class ActionItemWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, action, state="차단"):
        super().__init__()
        layout = QHBoxLayout(self)
        label = QLabel(action)
        self.label_state = QLabel(state)
        layout.addWidget(label, alignment=Qt.AlignLeft)
        layout.addWidget(self.label_state, alignment=Qt.AlignRight)
        self.clicked.connect(self.change_state)
        layout.setContentsMargins(0, 0, 0, 0)
        # remove_btn.clicked.connect(remove_callback)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def change_state(self):
        if self.label_state.text() == "허용":
            self.label_state.setText("관심")
        elif self.label_state.text() == "관심":
            self.label_state.setText("차단")
        else:
            self.label_state.setText("허용")

    def get_action_name(self):
        return self.layout().itemAt(0).widget().text()
    def get_value(self):
        return self.layout().itemAt(1).widget().text()

class SettingsFormAllowedAction(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ListForm")
        self.list_widget.setMinimumHeight(100)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # self.list_widget.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        # self.list_widget.setWordWrap(False)

        # btn_add = QPushButton("디렉토리 추가")
        # btn_add.clicked.connect(self.__open_path_explorer)
        label = QLabel("Allowed directories")
        label.setObjectName("h2")
        layout.addWidget(label)
        layout.addWidget(QLabel("LLM이 수행 가능한 동작을 관리합니다. (클릭으로 수정하기)"))
        layout.addWidget(self.list_widget)
        layout.addWidget(QLabel("허용: 해당 명령을 허용합니다."))
        layout.addWidget(QLabel("관심: 해당 명령이 포함 되는 경우 사용자에게 경고 합니다."))
        layout.addWidget(QLabel("차단: 해당 명령이 포함 되는 경우 해당 동작을 차단 합니다."))
        self.__load_value()
    
    def __add_item(self, action, state):
        item_widget = QListWidgetItem()
        widget = ActionItemWidget(action, state)
        item_widget.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(item_widget)
        self.list_widget.setItemWidget(item_widget, widget)
    
    def __load_value(self):
        list_available_action = SettingsManager.get('available_commands')
        list_interst_action = SettingsManager.get('interest_commands')
        list_action = SettingsManager.get('command_list')

        for action in list_action:

            if action in list_available_action:
                self.__add_item(action, "허용")
            elif action in list_interst_action:
                self.__add_item(action, "관심")
            else:
                self.__add_item(action, "차단")

    def get_value(self, filter=''):
        result = []
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if widget.get_value() == filter:
                result.append(widget.get_action_name())
        return result

class ContentSettings(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("ContentSettings")
        self.setProperty("parent", "MainWindowContent")

        self.settings_manager = SettingsManager()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setProperty("parent", "ContentSettings")

        self.scroll_area.setWidget(self.content_widget)
        self.content_layout = QVBoxLayout(self.content_widget)
        
        self.form_api_key = SettingsFormApiKey()
        self.form_model_name = SettingsFormModelName()
        self.form_monitoring_directory = SettingsFormMonitoringDirectory()
        self.form_allowed_directory = SettingsFormAllowedDirectory()
        self.form_allowed_method = SettingsFormAllowedAction()

        self.content_layout.addWidget(self.form_api_key)
        self.content_layout.addWidget(self.form_model_name)
        self.content_layout.addWidget(self.form_monitoring_directory)
        self.content_layout.addWidget(self.form_allowed_directory)
        self.content_layout.addWidget(self.form_allowed_method)
        self.content_layout.addStretch()

        self.btn_save = QPushButton("Save changes")
        self.btn_save.setObjectName("BtnNormal")
        self.btn_save.clicked.connect(self.__submit_changes)
        
        self.main_layout = QVBoxLayout(self)
        label = QLabel("Settings")
        label.setObjectName("h1")

        self.main_layout.addWidget(label)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.btn_save)

    def __submit_changes(self):
        SettingsManager.set('api_key', self.form_api_key.get_value())
        SettingsManager.set('model_name', self.form_model_name.get_value())
        SettingsManager.set('monitoring_dirs', self.form_monitoring_directory.get_value())
        SettingsManager.set('available_dirs', self.form_allowed_directory.get_value())
        SettingsManager.set('available_commands', self.form_allowed_method.get_value('허용'))
        SettingsManager.set('interest_commands', self.form_allowed_method.get_value('관심'))
        
    
class MainWindowContent(QWidget):
    def __init__(self, event_hub):
        super().__init__()
        self.event_hub = event_hub
        self.setObjectName("MainWindowContent")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QStackedLayout()

        self.home = ContentHome(event_hub)
        self.layout.addWidget(self.home)
        self.layout.addWidget(ContentHistory())
        self.layout.addWidget(ContentSettings())
        
        self.layout.setCurrentIndex(0)
        self.setLayout(self.layout)
    
    def update_tab(self, tab_name):
        assert tab_name in TAB_LIST, "MainWindowContent: Invalid tab_name was passed."
        self.layout.setCurrentIndex(TAB_LIST.index(tab_name))

class MainWindow(QMainWindow):

    def __init__(self, event_hub):
        super().__init__()
        self.setObjectName("sidebarWidget")
        self.setMinimumSize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        self.setWindowTitle("File Manger")
        self.event_hub = event_hub

        layout = QHBoxLayout()
        self.window_content = MainWindowContent(event_hub)
        self.window_sidebar = MainWindowSideBar()
        self.window_sidebar.set_clicked_action(self.__update_tab) 
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.window_sidebar, stretch=1)
        layout.addWidget(self.window_content, stretch=3)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.__load_stylesheet(PATH_RESOURCE + PATH_STYLE_SHEET)

    def __load_stylesheet(self, path):
        qss_file = QFile(path)
        qss_file.open(QFile.ReadOnly | QFile.Text)
        qss_stream = QTextStream(qss_file)
        self.setStyleSheet(qss_stream.readAll())
        qss_file.close()
    
    # def __update_tab(self, tab_name):
    #     self.window_content.update_tab(tab_name)

    def __update_tab(self):
        sender = self.sender()
        self.window_content.update_tab(sender.get_name())
    
    def toggle(self, state):
        self.window_content.home.toggle(state)
    
    def closeEvent(self, event):
        # if self.window_content.home.get_state():
        #     event.ignore()
        #     self.hide()
        #     return
        QApplication.quit()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
