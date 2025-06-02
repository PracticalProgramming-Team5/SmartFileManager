import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, 
    QWidget, QHBoxLayout, QVBoxLayout, 
    QPushButton, QStackedLayout, QButtonGroup,
    QScrollArea)
from PyQt5.QtCore import QFile, QTextStream, Qt


WIN_MIN_WIDTH = 800
WIN_MIN_HEIGHT = 600

PATH_STYLE_SHEET = "style.qss"

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
    def __init__(self):
        super().__init__()
        self.setObjectName("ContentHome")
        self.setProperty("parent", "MainWindowContent")

        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("Home"))
        self.layout.addWidget(QPushButton("Run"))
        
        self.layout.addStretch()
        self.setLayout(self.layout)
        btn = self.layout.itemAt(1).widget()
        # btn.clicked.connect(lambda: print("clicked"))
    
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
        self.btn_refresh.clicked.connect(self.__update_history)
        
        self.main_layout = QVBoxLayout(self)
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



class ContentSettings(QLabel):
    def __init__(self):
        super().__init__()
        self.setObjectName("ContentSettings")
        self.setProperty("parent", "MainWindowContent")
        self.setText("Settings")

class MainWindowContent(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindowContent")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.layout = QStackedLayout()

        self.layout.addWidget(ContentHome())
        self.layout.addWidget(ContentHistory())
        self.layout.addWidget(ContentSettings())
        
        self.layout.setCurrentIndex(0)
        self.setLayout(self.layout)
    
    def update_tab(self, tab_name):
        assert tab_name in TAB_LIST, "MainWindowContent: Invalid tab_name was passed."
        self.layout.setCurrentIndex(TAB_LIST.index(tab_name))

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebarWidget")
        self.setMinimumSize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        self.setWindowTitle("File Manger")

        layout = QHBoxLayout()
        self.window_content = MainWindowContent()
        self.window_sidebar = MainWindowSideBar()
        self.window_sidebar.set_clicked_action(self.__update_tab) 

        layout.addWidget(self.window_sidebar, stretch=1)
        layout.addWidget(self.window_content, stretch=3)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.__load_stylesheet(PATH_STYLE_SHEET)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
