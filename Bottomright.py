import os
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class Ui_Bottom_right(QObject):
    trigger_worker_run = Signal(str, str, int, int)

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
        self.integration_time_box = QSpinBox()
        self.nos_box = QSpinBox()
        self.stepping_order_box = QComboBox()
        self.total_steps = QLineEdit()


        grid1 = QGridLayout()
        self._add_label_input(grid1, "Start from, ps", self.start_from_box, 0)
        self._add_label_input(grid1, "Finish time, ps", self.finish_time_box, 1)
        self._add_label_input(grid1, "Number of shots, #", self.integration_time_box, 2)
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
        self.start_button.clicked.connect(lambda: self.trigger_worker_run.emit(self.content, self.stepping_order_box.currentText(), self.integration_time_box.value(), self.nos_box.value()))
        self.start_button.clicked.connect(lambda: print(self.content))
        left_panel.addWidget(self.start_button)

        self.start_from_box.valueChanged.connect(self.validate_inputs)
        self.finish_time_box.valueChanged.connect(self.validate_inputs)
        self.nos_box.valueChanged.connect(self.validate_inputs)
        self.integration_time_box.valueChanged.connect(self.validate_inputs)
        self.stepping_order_box.currentIndexChanged.connect(self.validate_inputs)

        self.nos_box.valueChanged.connect(lambda: self.total_steps.setText(f"{self.nos_box.value()*len(self.content)}"))
        self.start_from_box.valueChanged.connect(lambda: self.update_start_from_content(self.start_from_box.value()))
        self.finish_time_box.valueChanged.connect(lambda: self.update_finish_time_content(self.finish_time_box.value()))

    def _add_label_input(self, layout, label_text, widget, row):
        label = QLabel(label_text)
        layout.addWidget(label, row, 0)
        layout.addWidget(widget, row, 1)

        if isinstance(widget, QDoubleSpinBox):
            widget.setDecimals(2)
            widget.setRange(-8672.66, 8672.66)

        elif isinstance(widget, QSpinBox):
            widget.setMinimum(1)
            widget.setSingleStep(1)
            widget.setValue(1)

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
                or float(self.finish_time_box.value()) != 0
            ):
                self.start_button.setEnabled(True)
            else:
                self.start_button.setEnabled(False)

        except ValueError:
            print("NONONO")

    def showFileDialog(self):
        self.content = []
        fileName, _ = QFileDialog.getOpenFileName(
            self.tab2, "Select a .txt File", "", "Text Files (*.txt);;All Files (*)"
        )
        if fileName:
            self.file_label.setText(os.path.basename(fileName))
            try:
                with open(fileName, "r") as file:
                    content = file.read()
                self.text_display.setText(content)

                # Changing self.content to a list that is accepted by measurement functions
                self.content = [item.strip() for item in content.split(",") if item.strip()]
                self.content = [(unit, float(value)) for item in self.content for value, unit in [item.strip().split()]]

                # Changing GUI elements to display correct values after uploading file
                self.total_steps.setText(f"{len(self.content)*self.nos_box.value()}")
                self.current_step.setText(f"{0}")
                self.current_scan.setText(f"{1}")
                
                if self.content[0][0] in ['ns', 'nanosecond', 'nanoseconds']:
                    self.start_from_box.setValue(self.content[0][1]*1000)
                if self.content[0][0] in ['fs', 'femtosecond', 'femtoseconds']:
                    self.start_from_box.setValue(self.content[0][1]/1000)

                if self.content[-1][0] in ['ns', 'nanosecond', 'nanoseconds']:
                    self.finish_time_box.setValue(self.content[-1][1]*1000)
                if self.content[-1][0] in ['fs', 'femtosecond', 'femtoseconds']:
                    self.finish_time_box.setValue(self.content[-1][1]/1000)
            except Exception as e:
                self.show_error_message(f"Failed to load file: {e}")

    def update_start_from_content(self, value):
        if hasattr(self, "content") and self.content:
            # Update the first item to ('ps', value)
            self.content[0] = ('ps', value)
            print(self.content[0])

    def update_finish_time_content(self, value):
        if hasattr(self, "content") and self.content:
            # Update the last item to ('ps', value)
            self.content[-1] = ('ps', value)
            print(self.content[-1])

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
