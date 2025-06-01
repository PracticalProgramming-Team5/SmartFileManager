import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt5.QtCore import QFile, QTextStream, Qt


WIN_MIN_WIDTH = 800
WIN_MIN_HEIGHT = 600

PATH_STYLE_SHEET = "style.qss"

TAB_LIST = ["Home", "History", "Settings"]

FONT_SIZE_LARGE = 48

class MainWindowSideBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindowSideBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # self.setAutoFillBackground(True)
        self.elements = []
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        for tab in TAB_LIST:
            self.elements.append(QPushButton(tab))
            layout.addWidget(self.elements[-1])
            self.elements[-1].setProperty("parent", "MainWindowSideBar")
            self.elements[-1].setMinimumHeight(FONT_SIZE_LARGE+10)
        layout.addStretch()
        self.setLayout(layout)

class MainWindowContent(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindowContent")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # self.setAutoFillBackground(True)
        

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebarWidget")
        self.setMinimumSize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        self.setWindowTitle("File Manger")

        layout = QHBoxLayout()
        self.window_content = MainWindowContent()
        self.window_sidebar = MainWindowSideBar()

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

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
