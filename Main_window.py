import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
from camera_gui import *

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tab-Based Application")
        self.setGeometry(100, 100, 800, 600)

        # Create a QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.dls_window = DLSWindow()
        self.shot_delay_app = ShotDelayApp(self.dls_window)



        # Add tabs    
        self.tabs.addTab(self.shot_delay_app, "Shot Delay App")
        self.tabs.addTab(self.dls_window, "DLS Window")




if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    app.exec()
