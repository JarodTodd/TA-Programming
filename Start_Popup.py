import sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

class StartPopup(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Details")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Labels and LineEdits
        fields = {
            "Sample:": QLineEdit(),
            "Solvent:": QLineEdit(),
            "Excitation wavelength:": {"value": QLineEdit(), "unit": QLineEdit()},
            "Path Length:": {"value": QLineEdit(), "unit": QLineEdit()},
            "Excitation Power:": {"value": QLineEdit(), "unit": QLineEdit()}
        }
        self.line_edits = fields  # Store references to line edits in a dictionary

        for label_text, line_edit in fields.items():
            layout1 = QHBoxLayout()
            layout1.addWidget(QLabel(label_text))
            if isinstance(line_edit, dict):
                layout1.addWidget(line_edit["value"])
                le_unit = line_edit["unit"]
                le_unit.setMaximumWidth(80)
                le_unit.setPlaceholderText("Unit")
                le_unit.setStyleSheet("background-color: lightgray;")
                layout1.addWidget(le_unit)
            else:
                layout1.addWidget(line_edit)
            layout.addLayout(layout1)

        self.notes_label = QLabel("Additional Notes:")
        self.notes_box = QTextEdit()
        layout.addWidget(self.notes_label)
        layout.addWidget(self.notes_box)

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
        self.dir_path.textChanged.connect(self.enable_start)
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
        sender = self.sender()
        if sender == self.filename:
            # Remove trailing .csv if present to allow editing
            base = text[:-4] if text.endswith(".csv") else text
            expected_text = base + ".csv"

            # Update the filename only if necessary
            if text != expected_text:
                cursor_pos = min(self.filename.cursorPosition(), len(base))  # Limit cursor position
                self.filename.blockSignals(True)
                self.filename.setText(expected_text)
                self.filename.setCursorPosition(cursor_pos)
                self.filename.blockSignals(False)

        # Enable the button only if both filename and directory are valid
        filename_valid = self.filename.text().strip() not in ("", ".csv")
        directory_valid = self.dir_path.text().strip() != ""
        self.real_start_button.setEnabled(filename_valid and directory_valid)

    def get_metadata(self):
        sample = self.line_edits["Sample:"].text()
        solvent = self.line_edits["Solvent:"].text()
        exc_wl = self.line_edits["Excitation wavelength:"]["value"].text()
        exc_wl_unit = self.line_edits["Excitation wavelength:"]["unit"].text()
        path_len = self.line_edits["Path Length:"]["value"].text()
        path_len_unit = self.line_edits["Path Length:"]["unit"].text()
        exc_power = self.line_edits["Excitation Power:"]["value"].text()
        exc_power_unit = self.line_edits["Excitation Power:"]["unit"].text()
        notes = self.notes_box.text()
        return sample, solvent, exc_wl, exc_wl_unit, path_len, path_len_unit, exc_power, exc_power_unit, notes


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StartPopup()
    window.show()
    sys.exit(app.exec())