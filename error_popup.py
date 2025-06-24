from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

def show_error_message(error_message):
    """
    Display an error message dialog.

    Args:
        error_message (str): The error message to display.
    """
    msgbox = QMessageBox()
    msgbox.setWindowTitle("Error")
    msgbox.setText("An error occurred:")
    msgbox.setInformativeText(error_message)
    msgbox.setIcon(QMessageBox.Critical)
    msgbox.setStandardButtons(QMessageBox.Ok)
    msgbox.exec()
