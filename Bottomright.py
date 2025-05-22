import os
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from exponential_steps import *


class Ui_Bottom_right(QObject):
    trigger_worker_run = Signal(list, str, int, int)
    parsed_content_signal = Signal(list)

    def __init__(self):
        super().__init__()
        self.content = []

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
        tab1layout = QVBoxLayout()

        self.step_option_box = QComboBox()
        self.step_option_box.addItems(["Exponential", "Linear"])
        grid = QGridLayout()
        self.exponential_start = QDoubleSpinBox()
        self.exponential_start.setRange(-8672.66, 8672.66)
        self.exponential_finish = QDoubleSpinBox()
        self.exponential_finish.setRange(-8672.66, 8672.66)
        self.steps_box = QSpinBox()
        self.steps_box.setMaximum(999999)
        self.steps_box.setValue(100)

        grid.addWidget(QLabel("Start from, ps:"), 0, 0)
        grid.addWidget(self.exponential_start, 0, 1)
        grid.addWidget(QLabel("Finish time, ps:"), 1, 0)
        grid.addWidget(self.exponential_finish, 1, 1)
        grid.addWidget(QLabel("Number of steps:"), 2, 0)
        grid.addWidget(self.steps_box, 2, 1)

        tab1layout.addWidget(self.step_option_box)
        tab1layout.addLayout(grid)
        self.tab1.setLayout(tab1layout)
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
        self.t0_line = QLineEdit()
        grid2 = QGridLayout()
        self._add_label_input(grid2, "Current step #", self.current_step, 0)
        self._add_label_input(grid2, "Current delay, ps", self.current_delay, 1)
        self._add_label_input(grid2, "Reference time (t0)", self.t0_line, 2)
        self._add_label_input(grid2, "Time remaining", self.time_remaining, 3)
        self._add_label_input(grid2, "Current scan #", self.current_scan, 4)
        left_panel.addLayout(grid2)

        self.start_button = QPushButton()
        self.start_button.setText("Start Measurement")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.on_start_button_clicked)
        left_panel.addWidget(self.start_button)

        self.start_from_box.valueChanged.connect(self.validate_inputs)
        self.finish_time_box.valueChanged.connect(self.validate_inputs)
        self.nos_box.valueChanged.connect(self.validate_inputs)
        self.integration_time_box.valueChanged.connect(self.validate_inputs)
        self.stepping_order_box.currentIndexChanged.connect(self.validate_inputs)

        self.nos_box.valueChanged.connect(lambda: self.total_steps.setText(f"{self.nos_box.value()*len(self.content)}"))
        self.start_from_box.valueChanged.connect(lambda: self.update_start_from_content(self.start_from_box.value()))
        self.start_from_box.valueChanged.connect(lambda: self.exponential_start.setValue(self.start_from_box.value()))
        self.exponential_start.valueChanged.connect(lambda: self.start_from_box.setValue(self.exponential_start.value()))
        self.finish_time_box.valueChanged.connect(lambda: self.update_finish_time_content(self.finish_time_box.value()))
        self.exponential_finish.valueChanged.connect(lambda: self.finish_time_box.setValue(self.exponential_finish.value()))
        self.tabWidget.currentChanged.connect(lambda: self.on_tab_change())

    def _add_label_input(self, layout, label_text, widget, row):
        label = QLabel(label_text)
        layout.addWidget(label, row, 0)
        layout.addWidget(widget, row, 1)

        if isinstance(widget, QDoubleSpinBox):
            widget.setDecimals(2)
            widget.setRange(-8672.66, 8672.66)
            widget.setEnabled(False)

        elif isinstance(widget, QSpinBox):
            widget.setMinimum(1)
            widget.setMaximum(999999)
            widget.setSingleStep(1)
            widget.setValue(1)
            widget.setMaximum(9999999)
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


    def on_start_button_clicked(self):
        if self.tabWidget.currentIndex() == 0:
            try:
                if self.start_from_box.value() != self.finish_time_box.value():
                    self.content = generate_timepoints(self.start_from_box.value(), self.finish_time_box.value(), self.steps_box.value())
                    self.trigger_worker_run.emit(self.content, self.stepping_order_box.currentText(), self.integration_time_box.value(), self.nos_box.value())
            except Exception as e:
                self.show_error_message(f"Start and end time are the same.")
        if self.tabWidget.currentIndex() == 1:
            if not self.content:
                self.show_error_message("No measurement steps defined. Please upload a file or enter values.")
                return
            self.trigger_worker_run.emit(
                self.content,
                self.stepping_order_box.currentText(),
                self.integration_time_box.value(),
                self.nos_box.value()
            )
        print(f"Self.content = {self.content}")

        self.parsed_content_signal.emit(self.content)


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
                lines = [item.strip() for item in content.split(",") if item.strip()]
                if lines[0] == "ps":
                    lines = lines[1:]
                self.content = [float(item) for item in lines]

                # Changing GUI elements to display correct values after uploading file
                self.total_steps.setText(f"{(len(self.content))*self.nos_box.value()}")
                self.current_step.setText(f"{0}")
                self.current_scan.setText(f"{1}")
                

                self.start_from_box.setValue(self.content[0])
                self.finish_time_box.setValue(self.content[-1])         
                               
            except Exception as e:
                self.show_error_message(f"Failed to load file: {e}")

    def update_start_from_content(self, value):
        if hasattr(self, "content") and self.content:
            # Update the first item to ('ps', value)
            self.content[0] = value
            print(self.content[0])

    def update_finish_time_content(self, value):
        if hasattr(self, "content") and self.content:
            # Update the last item to ('ps', value)
            self.content[-1] = value
            print(self.content[-1])

    def on_tab_change(self):
        if self.tabWidget.currentIndex() == 0:
            self.start_from_box.setEnabled(False)
            self.finish_time_box.setEnabled(False)
        elif self.tabWidget.currentIndex() == 1:
            self.start_from_box.setEnabled(True)
            self.finish_time_box.setEnabled(True)
            
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
