import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel


WIN_MIN_WIDTH = 800
WIN_MIN_HEIGHT = 600

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setProperty("item", "MainWindow")
        self.setMinimumSize(WIN_MIN_WIDTH, WIN_MIN_HEIGHT)
        self.setWindowTitle("File Manger")

        self.setCentralWidget(QLabel("Hello"))

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
