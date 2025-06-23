import sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

class WavelengthPopUp(QDialog):
    wavelength_signal = Signal(list)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Details")
        self.init_ui()
        self.wavelengths = []

    def init_ui(self):
        layout = QVBoxLayout()

        # File selection
        self.file_button = QPushButton("Select File")
        layout.addWidget(self.file_button)

        # File path display
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Selected File:"))
        self.file_path = QLineEdit("")
        self.file_path.setReadOnly(True)
        self.file_path.setStyleSheet("background-color: lightgray;")
        file_layout.addWidget(self.file_path)
        layout.addLayout(file_layout)

        # Connect button to file dialog
        self.file_button.clicked.connect(self.select_file)

        # Load button
        self.load_button = QPushButton("Load")
        self.load_button.setEnabled(False)
        self.load_button.clicked.connect(self.load_button_pressed)
        layout.addWidget(self.load_button)
        self.setLayout(layout)

    def select_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilters(["CSV and TXT Files (*.csv *.txt)", "All Files (*)"])
        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            self.file_path.setText(selected_file)
            try:
                if selected_file.lower().endswith(".csv"):
                    # Read the header row from the CSV file
                    with open(selected_file, "r", encoding="utf-8") as f:
                        header = f.readline().strip().split(",")
                    if "Delay (ps)" in header:
                        # Wavelengths are all columns after "Delay (ps)"
                        delay_index = header.index("Delay (ps)")
                        self.wavelengths = header[delay_index + 1 :]
                        print(self.wavelengths)
                        self.load_button.setEnabled(True)
                    else:
                        self.load_button.setEnabled(False)
                        self.show_error_message("This .csv file is not compatible.")
                elif selected_file.lower().endswith(".txt"):
                    with open(selected_file, "r", encoding="utf-8") as f:
                        lines = [line.strip() for line in f if line.strip()]
                        print(lines[0])
                    if not lines:
                        msg = "The file is empty."
                        print(msg)
                        self.show_error_message(msg)
                        return
                    first_line = lines[0].split(",")
                    if not first_line or not isinstance(first_line[0], str) or not first_line[0].strip():
                        msg = "The first item before the first comma must be a non-empty string."
                        self.show_error_message(msg)
                        return
                    # Check that all items after the first are floats or ints
                    numeric_values = []
                    for item in first_line[1:]:
                        item = item.strip()
                        if not item:
                            continue
                        try:
                            val = float(item)
                            numeric_values.append(item)
                        except ValueError:
                            msg = f"Value '{item}' after the first comma is not a valid number."
                            self.show_error_message(msg)
                            return
                    if len(lines) == 1:
                        if not numeric_values:
                            msg = "No numeric wavelengths found after the first string."
                            print(msg)
                            self.show_error_message(msg)
                            return
                        self.wavelengths = numeric_values
                    else:
                        # For multi-line, expect first item of each line to be string, rest to be numbers
                        self.wavelengths = []
                        for l in lines[1:]:
                            parts = l.split(",")
                            for item in parts:
                                item = item.strip()
                                if not item:
                                    continue
                                try:
                                    float(item)
                                    self.wavelengths.append(item)
                                except ValueError:
                                    continue  # skip non-numeric
                        if not self.wavelengths:
                            msg = "No numeric data found after the first string."
                            print(msg)
                            self.show_error_message(msg)
                            return
                        print("Wavelengths loaded:", self.wavelengths)
                        self.wavelength_signal.emit(self.wavelengths)
                    self.load_button.setEnabled(True)
            except Exception as e:
                self.show_error_message(str(e))
                    
    def load_button_pressed(self):
        self.wavelength_signal.emit(self.wavelengths)
        self.close()

    def show_error_message(self, error_message):
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

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WavelengthPopUp()
    window.show()
    sys.exit(app.exec())