import sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

class WavelengthPopUp(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Details")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # --- Tab 1: From File ---
        file_tab = QWidget()
        file_tab_layout = QVBoxLayout()

        # File selection
        self.file_button = QPushButton("Select File")
        file_tab_layout.addWidget(self.file_button)

        # File path display
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Selected File:"))
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        self.file_path.setStyleSheet("background-color: lightgray;")
        file_layout.addWidget(self.file_path)
        file_tab_layout.addLayout(file_layout)

        # Connect button to file dialog
        self.file_button.clicked.connect(self.select_file)

        file_tab.setLayout(file_tab_layout)
        tabs.addTab(file_tab, "From File")

        # --- Tab 2: Min/Max Wavelength ---
        minmax_tab = QWidget()
        minmax_tab_layout = QVBoxLayout()

        # Labels and LineEdits
        fields = {
            "Lowest wavelength: nm": QLineEdit(),
            "Highest wavelength: nm": QLineEdit()
        }
        self.line_edits = fields  # Store references to line edits in a dictionary

        for label_text, line_edit in fields.items():
            layout1 = QHBoxLayout()
            layout1.addWidget(QLabel(label_text))
            layout1.addWidget(line_edit)
            minmax_tab_layout.addLayout(layout1)

        minmax_tab.setLayout(minmax_tab_layout)
        tabs.addTab(minmax_tab, "Min/Max Wavelength")

        # Load button (outside tabs, applies to both)
        self.load_button = QPushButton("Load")
        self.load_button.setEnabled(False)
        layout.addWidget(self.load_button)
        self.setLayout(layout)

    def select_file(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilters(["CSV and TXT Files (*.csv *.txt)", "All Files (*)"])
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.file_path.setText(selected_files[0])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WavelengthPopUp()
    window.show()
    sys.exit(app.exec())