import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from GUI import DLSWindow  # Import the MainWindow class from GUI.py
from camera_gui import ShotDelayApp
import random


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tab-Based Application")
        self.setGeometry(100, 100, 800, 600)

        # Create a QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add tabs    
        self.tabs.addTab(ShotDelayApp(), "Shot Delay App")
        self.tabs.addTab(DLSWindow(), "DLS Window")


if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    app.exec()
