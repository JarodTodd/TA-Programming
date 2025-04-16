from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import subprocess
import sys
import random

class ShotDelayApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Interface")
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()

        # Main layout as a grid
        self.grid_layout = QGridLayout()

        # Blank spaces for top-left, top-right, and bottom-left quarters
        self.grid_layout.addWidget(QWidget(), 0, 0)  # Top-left
        self.grid_layout.addWidget(QWidget(), 0, 1)  # Top-right
        self.grid_layout.addWidget(QWidget(), 1, 0)  # Bottom-left

        # Bottom-right quarter layout
        bottom_right_layout = QVBoxLayout()

        # Form layout for shots and delays input
        self.form_layout = QFormLayout()
        self.shots_input = QLineEdit()
        self.shots_input.setPlaceholderText("Enter number of shots")
        self.form_layout.addRow("Number of Shots:", self.shots_input)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        # File upload and script execution layout
        hbox5 = QHBoxLayout()

        # File upload button
        file_upload_button = QPushButton("Upload File")
        file_upload_button.clicked.connect(self.showFileDialog)

        # Script execution buttons
        vbox = QVBoxLayout()
        runscript_button = QPushButton("Run Script")
        runscript_button.clicked.connect(lambda: self.RunContent(self.text_display.toPlainText(), "forward"))

        runscript_backwards_button = QPushButton("Run Script Backwards")
        runscript_backwards_button.clicked.connect(lambda: self.RunContent(self.text_display.toPlainText(), "backwards"))

        runscript_random_button = QPushButton("Run Script Random")
        runscript_random_button.clicked.connect(lambda: self.RunContent(self.text_display.toPlainText(), "random"))

        vbox.addWidget(runscript_button)
        vbox.addWidget(runscript_backwards_button)
        vbox.addWidget(runscript_random_button)

        # File label and text display
        self.file_label = QLabel("No file selected", self)
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)

        # Add widgets to hbox5
        hbox5.addLayout(vbox)
        hbox5.addWidget(file_upload_button)
        hbox5.addWidget(self.file_label)

        # Add widgets to the bottom-right layout
        bottom_right_layout.addLayout(self.form_layout)
        bottom_right_layout.addWidget(self.status_label)
        bottom_right_layout.addLayout(hbox5)
        bottom_right_layout.addWidget(self.text_display)

        # Add the bottom-right layout to the grid layout
        spacer1 = QSpacerItem(400, 400)
        spacer2 = QSpacerItem(400, 400)
        spacer3 = QSpacerItem(400, 400)
        self.grid_layout.addItem(spacer1, 0, 0)
        self.grid_layout.addItem(spacer2, 0, 1)
        self.grid_layout.addItem(spacer3, 1, 0)
        self.grid_layout.addLayout(bottom_right_layout, 1, 1)  # Bottom-right

        # Set the grid layout as the main layout
        self.setLayout(self.grid_layout)

        # Connect signals
        self.shots_input.textChanged.connect(self.validate_inputs)


    def showFileDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select a .txt File", "", "Text Files (*.txt);;All Files (*)")
        if fileName:
            self.file_label.setText(fileName)
            try:
                with open(fileName, 'r') as file:
                    content = file.read()
                self.text_display.setText(content)
            except Exception as e:
                self.show_error_message(f"Failed to load file: {e}")

    def RunContent(self, content, orientation):
        lines = content.splitlines()
        parsed_content = []

        for line in lines:
            items = line.split(",")
            for item in items:
                item = item.strip()
                if item:
                    letters = ""
                    numbers = ""
                    for char in item:
                        if char.isdigit() or char == "." or char == "-":
                            numbers += char
                        else:
                            letters += char
                    if numbers:
                        try:
                            parsed_content.append((letters.strip(), float(numbers)))
                        except ValueError:
                            parsed_content.append((letters.strip(), None))
                    else:
                        parsed_content.append((letters.strip(), None))

        if not parsed_content:
            self.show_error_message("No file was uploaded.")
            return

        if orientation == 'backwards':
            parsed_content.reverse()

        if orientation == 'random':
            random.shuffle(parsed_content)

        number_delays = len(parsed_content)
        return parsed_content, number_delays

    def validate_inputs(self):
        try:
            shots = int(self.shots_input.text())
            valid = shots > 0
        except ValueError:
            valid = False
        self.runscript_button.setEnabled(valid)
        self.runscript_backwards_button.setEnabled(valid)
        self.runscript_random_button.setEnabled(valid)

    def run_external_script(self):
        shots = self.shots_input.text()
        _, delays = self.RunContent(self.text_display.toPlainText(), "forward")
        try:
            subprocess.run(
                [sys.executable, "main.py", shots, delays],
                check=True
            )
            self.status_label.setText("Script ran successfully!")
        except subprocess.CalledProcessError as e:
            self.status_label.setText(f"Error running script: {e}")

if __name__ == "__main__":
    app = QApplication([])
    window = ShotDelayApp()
    window.show()
    sys.exit(app.exec())
