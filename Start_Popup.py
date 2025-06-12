import sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

class StartPopup(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Directory Picker and Inputs")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Labels and LineEdits
        fields = {
            "Sample": QLineEdit(),
            "Solvent": QLineEdit(),
            "Excitation wavelength: nm": QLineEdit(),
            "Path Length: ps": QLineEdit()
        }
        self.line_edits = fields  # Store references to line edits in a dictionary

        for label_text, line_edit in fields.items():
            layout1 = QHBoxLayout()
            layout1.addWidget(QLabel(label_text))
            layout1.addWidget(line_edit)
            layout.addLayout(layout1)

        hbox = QHBoxLayout()
        self.filename_label = QLabel("Filename:")
        self.filename = QLineEdit("")
        self.filename.textChanged.connect(self.enable_start)
        self.filename.setToolTip('If there is more than 1 scan "_Scan_n" will be added to the end AND a file with the averages of all scans will be added ending with "_AVG_all_scans"' )
        hbox.addWidget(self.filename_label)
        hbox.addWidget(self.filename)
        layout.addLayout(hbox)

        # Directory selection
        self.dir_button = QPushButton("Select Directory")
        self.dir_button.clicked.connect(self.open_directory_dialog)
        layout.addWidget(self.dir_button)

        self.setLayout(layout)

        # Directory path display
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Selected Directory:"))
        self.dir_path = QLineEdit()
        self.dir_path.setReadOnly(True)
        self.dir_path.setStyleSheet("background-color: lightgray;")
        dir_layout.addWidget(self.dir_path)
        layout.addLayout(dir_layout)

        self.real_start_button = QPushButton("Start (REAL)")
        self.real_start_button.setEnabled(False)
        layout.addWidget(self.real_start_button)
        self.setLayout(layout)

    def open_directory_dialog(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.dir_path.setText(directory)

    def enable_start(self, text):
        # Remove trailing .csv if present to allow editing
        if text.endswith(".csv"):
            base = text[:-4]
        else:
            base = text

        # Ensure we only update if necessary
        expected_text = base + ".csv"
        if text != expected_text:
            cursor_pos = self.filename.cursorPosition()
            # Limit cursor to before the extension
            if cursor_pos > len(base):
                cursor_pos = len(base)

            self.filename.blockSignals(True)
            self.filename.setText(expected_text)
            self.filename.setCursorPosition(cursor_pos)
            self.filename.blockSignals(False)
            text = expected_text  # Update for button logic

        # Enable the button only if there's something before ".csv"
        if text != ".csv":
            self.real_start_button.setEnabled(True)
        else:
            self.real_start_button.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StartPopup()
    window.show()
    sys.exit(app.exec())