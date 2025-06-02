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
        

class ContentHistory(QLabel):
    def __init__(self):
        super().__init__()
        self.setObjectName("ContentHistory")
        self.setProperty("parent", "MainWindowContent")
        self.setText("History")

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
