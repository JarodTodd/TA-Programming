import os
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class Ui_Bottom_right(QObject):
    trigger_worker_run = Signal(str, str, int)

    def __init__(self):
        super().__init__()

    def setupUi(self, Bottom_right):
        Bottom_right.setWindowTitle("Bottom_right")
        main_layout = QHBoxLayout(Bottom_right)

        # Left panel layout
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel)

        # Tab widget (right side)
        self.tabWidget = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabWidget.addTab(self.tab1, "Exponential Steps")
        self.tabWidget.addTab(self.tab2, "From File")
        main_layout.addWidget(self.tabWidget)
        self.tabWidget.setCurrentIndex(0)

        tab2layout = QHBoxLayout()
        self.file_upload_button = QPushButton("Upload File")
        self.file_upload_button.clicked.connect(self.showFileDialog)

        # File label and text display
        self.file_label = QLabel("No file selected")
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(False)

        tab2layout.addWidget(self.file_upload_button)
        tab2layout.addWidget(self.file_label)
        tab2layout.addWidget(self.text_display)

        self.tab2.setLayout(tab2layout)
        # First grid (labels and inputs)
        self.start_from_box = QDoubleSpinBox()
        self.finish_time_box = QDoubleSpinBox()
        self.integration_time_box = QDoubleSpinBox()
        self.nos_box = QSpinBox()
        self.stepping_order_box = QComboBox()
        self.total_steps = QLineEdit()

        self.integration_time_box.setValue(1)
        self.nos_box.setValue(1)

        grid1 = QGridLayout()
        self._add_label_input(grid1, "Start from, ps", self.start_from_box, 0)
        self._add_label_input(grid1, "Finish time, ps", self.finish_time_box, 1)
        self._add_label_input(grid1, "Average, s", self.integration_time_box, 2)
        self._add_label_input(grid1, "Number of scans", self.nos_box, 3)
        self._add_label_input(grid1, "Stepping order", self.stepping_order_box, 4)
        self._add_label_input(grid1, "Total # of steps", self.total_steps, 5)
        left_panel.addLayout(grid1)

        # Second grid (status/info)
        self.current_step = QLineEdit()
        self.current_delay = QLineEdit()
        self.time_remaining = QLineEdit()
        self.current_scan = QLineEdit()
        grid2 = QGridLayout()
        self._add_label_input(grid2, "Current step #", self.current_step, 0)
        self._add_label_input(grid2, "Current delay, ps", self.current_delay, 1)
        self._add_label_input(grid2, "Time remaining", self.time_remaining, 2)
        self._add_label_input(grid2, "Current scan #", self.current_scan, 3)
        left_panel.addLayout(grid2)

        self.start_button = QPushButton()
        self.start_button.setText("Start Measurement")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(lambda: self.trigger_worker_run.emit(self.text_display.toPlainText(), self.stepping_order_box.currentText(), int(self.integration_time_box.value())))
        left_panel.addWidget(self.start_button)

        self.start_from_box.valueChanged.connect(self.validate_inputs)
        self.finish_time_box.valueChanged.connect(self.validate_inputs)
        self.nos_box.valueChanged.connect(self.validate_inputs)
        self.integration_time_box.valueChanged.connect(self.validate_inputs)
        self.stepping_order_box.currentIndexChanged.connect(self.validate_inputs)

    def _add_label_input(self, layout, label_text, widget, row):
        label = QLabel(label_text)
        layout.addWidget(label, row, 0)
        layout.addWidget(widget, row, 1)

        if isinstance(widget, QDoubleSpinBox):
            widget.setDecimals(2)
            widget.setRange(-8672.66, 8672.66)

        elif isinstance(widget, QSpinBox):
            widget.setRange(0, 1000000)
            widget.setSingleStep(1)

        elif isinstance(widget, QLineEdit):
            widget.setReadOnly(True)
            widget.setStyleSheet("background-color: lightgray;")
            widget.setPlaceholderText("")

        elif isinstance(widget, QComboBox):
            widget.addItems(["Regular", "Backwards", "Random"])
            widget.setCurrentIndex(0)

    def validate_inputs(self):
        try:
            if (
                int(self.integration_time_box.value()) > 0
                and int(self.nos_box.value()) > 0
                and float(self.start_from_box.value()) != 0
            ):
                self.start_button.setEnabled(True)
            else:
                self.start_button.setEnabled(False)

        except ValueError:
            print("NONONO")

    def showFileDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(
            self.tab2, "Select a .txt File", "", "Text Files (*.txt);;All Files (*)"
        )
        if fileName:
            self.file_label.setText(os.path.basename(fileName))
            try:
                with open(fileName, "r") as file:
                    content = file.read()
                self.text_display.setText(content)
            except Exception as e:
                self.show_error_message(f"Failed to load file: {e}")

    def show_error_message(self, error_message):
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Error")
        msgbox.setText("An error occurred:")
        msgbox.setInformativeText(error_message)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    Bottom_right = QWidget()
    ui = Ui_Bottom_right()
    ui.setupUi(Bottom_right)
    Bottom_right.show()
    sys.exit(app.exec())
