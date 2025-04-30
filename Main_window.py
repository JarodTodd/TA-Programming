import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from GUI import *
from camera_gui import *

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tab-Based Application")
        self.setGeometry(100, 100, 800, 600)

        # Create a QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.shot_delay_app = ShotDelayApp()
        self.dls_window = DLSWindow()
        self.worker = Measurementworker()
        self.worker.start()

        # Add tabs    
        self.tabs.addTab(self.shot_delay_app, "Shot Delay App")
        self.tabs.addTab(self.dls_window, "DLS Window")

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()



if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    worker = Measurementworker()
    worker.start()
    main_app.show()
    app.exec()
    worker.stop()
