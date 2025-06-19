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
                    raise ImportError("This .csv file is not compatible.")
            elif selected_file.lower().endswith(".txt"):
                # Example for .txt: expects first line to start with "Wavelengths"
                with open(selected_file, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip().split(",")
                if first_line and first_line[0] == "Wavelengths":
                    self.wavelengths = first_line[1:]
                    print(self.wavelengths)
                    self.load_button.setEnabled(True)
                else:
                    raise ImportError("This .txt file is not compatible.")
                
    def load_button_pressed(self):
        self.wavelength_signal.emit(self.wavelengths)
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WavelengthPopUp()
    window.show()
    sys.exit(app.exec())