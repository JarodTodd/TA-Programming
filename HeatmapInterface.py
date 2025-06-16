import os
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from exponential_steps import *
from Start_Popup import *
import csv

class Heatmap_Interface(QObject):

    """These two signals start or stop measurements from this window."""
    trigger_worker_run = Signal(list, str, int, int)
    stop_measurement_signal = Signal()

    """This signal transmits the metadata filled in in the pop-up window at measurement start."""
    metadata_signal = Signal(str, str, str, str, float, float)

    """This signal emits the list of delay times after formatting them properly."""
    parsed_content_signal = Signal(list)


    def __init__(self):
        super().__init__()
        self.startpopup = StartPopup()
        self.content = []

    def setupUi(self, Interface):
        Interface.setWindowTitle("Interface")
        full_layout = QVBoxLayout(Interface)
        main_layout = QHBoxLayout()
        full_layout.addLayout(main_layout)
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
        self.steps_box.valueChanged.connect(self.change_steps)


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
        self.file_upload_button.setToolTip("File should be either .txt or .csv with delay times in picoseconds.")

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
        self.scans_box = QSpinBox()
        self.stepping_order_box = QComboBox()
        self.total_steps = QLineEdit()


        grid1 = QGridLayout()
        self._add_label_input(grid1, "Start from, ps", self.start_from_box, 0)
        self._add_label_input(grid1, "Finish time, ps", self.finish_time_box, 1)
        self._add_label_input(grid1, "Number of shots, #", self.integration_time_box, 2)
        self._add_label_input(grid1, "Number of scans", self.scans_box, 3)
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
        self.start_button.clicked.connect(self.open_popup)
        self.startpopup.real_start_button.clicked.connect(self.on_start_button_clicked)


        left_panel.addWidget(self.start_button)

        self.stop_button = QPushButton()
        self.stop_button.setText("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(lambda: self.stop_measurement_signal.emit())
        left_panel.addWidget(self.stop_button)

        self.total_steps.setText(f"100")
        self.current_step.setText(f"0")
        self.current_scan.setText(f"0")
        self.time_remaining.setText("--")
        self.start_from_box.valueChanged.connect(self.validate_inputs)
        self.finish_time_box.valueChanged.connect(self.validate_inputs)
        self.scans_box.valueChanged.connect(self.validate_inputs)
        self.integration_time_box.valueChanged.connect(self.validate_inputs)
        self.stepping_order_box.currentIndexChanged.connect(self.validate_inputs)

        self.scans_box.valueChanged.connect(self.change_steps)
        self.start_from_box.valueChanged.connect(lambda: self.update_start_from_content(self.start_from_box.value()))
        self.start_from_box.valueChanged.connect(lambda: self.exponential_start.setValue(self.start_from_box.value()))
        self.exponential_start.valueChanged.connect(lambda: self.start_from_box.setValue(self.exponential_start.value()))
        self.finish_time_box.valueChanged.connect(lambda: self.update_finish_time_content(self.finish_time_box.value()))
        self.exponential_finish.valueChanged.connect(lambda: self.finish_time_box.setValue(self.exponential_finish.value()))
        self.tabWidget.currentChanged.connect(lambda: self.on_tab_change())

        hbox = QHBoxLayout()
        self.progressbar = QProgressBar()
        self.progressbar.setMinimum(0)
        self.progressbar.setMaximum(8672666)
        self.progressbar.setTextVisible(False)
        self.progresslabel = QLabel(f"/8672.66")
        hbox.addWidget(self.progressbar)
        hbox.addWidget(self.progresslabel)

        full_layout.addLayout(hbox)

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
            self.scans_box.setValue(1)
            self.integration_time_box.setValue(1000)
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
                and int(self.scans_box.value()) > 0
                and float(self.start_from_box.value()) != 0 
                or float(self.finish_time_box.value()) != 0
            ):
                self.start_button.setEnabled(True)
            else:
                self.start_button.setEnabled(False)

        except ValueError:
            print("NONONO")

    def open_popup(self):
        self.startpopup.exec()


    def on_start_button_clicked(self):
        if self.tabWidget.currentIndex() == 0:
            try:
                start = self.start_from_box.value()
                finish = self.finish_time_box.value()
                steps = self.steps_box.value()
                if start != finish and steps > 1:
                    if self.step_option_box.currentText() == "Exponential":
                        self.content = generate_timepoints(start, finish, steps)
                        for i in range(len(self.content)):
                            self.content[i] = float(self.content[i])
                    elif self.step_option_box.currentText() == "Linear":
                        if steps < 2:
                            self.show_error_message("Number of steps must be at least 2.")
                            return
                        self.content = list(np.linspace(start, finish, steps))
                    self.trigger_worker_run.emit(
                        self.content,
                        self.stepping_order_box.currentText(),
                        self.integration_time_box.value(),
                        self.scans_box.value()
                    )
                else:
                    self.show_error_message("Start and end time must be different and steps > 1.")
            except Exception as e:
                self.show_error_message(f"Error generating timepoints: {e}")
        if self.tabWidget.currentIndex() == 1:
            if not self.content:
                self.show_error_message("No measurement steps defined. Please upload a file or enter values.")
                return
            self.trigger_worker_run.emit(
                self.content,
                self.stepping_order_box.currentText(),
                self.integration_time_box.value(),
                self.scans_box.value()
            )
        print(f"Self.content = {self.content}")
        self.parsed_content_signal.emit(self.content)
        self.time_remaining_timer(int((int(self.total_steps.text())*9/25) + 7))
        self.emit_metadata_signal()
        self.stop_button.setEnabled(True)
        self.startpopup.close()

    def emit_metadata_signal(self):
        directory = self.startpopup.dir_path.text()
        filename = self.startpopup.filename.text().removesuffix(".csv")

        sample = self.startpopup.line_edits["Sample"].text()
        if sample == "":
            sample = "Unknown"

        solvent = self.startpopup.line_edits["Solvent"].text()
        if solvent == "":
            solvent = "Unknown"

        if self.startpopup.line_edits["Excitation wavelength: nm"].text() == "":
            excitation_wavelength = None
        else:
            excitation_wavelength = float(self.startpopup.line_edits["Excitation wavelength: nm"].text())

        if self.startpopup.line_edits["Path Length: ps"].text() == "":
            path_length = None
        else:
            path_length = float(self.startpopup.line_edits["Path Length: ps"].text())

        # Emit the signal with the collected values
        self.metadata_signal.emit(directory, filename, sample, solvent, excitation_wavelength, path_length)

    def time_remaining_timer(self, t):
        self.remaining_time = t
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

    def update_timer(self):
        if self.remaining_time > 0:
            mins, secs = divmod(self.remaining_time, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            self.time_remaining.setText(str(timer))
            self.remaining_time -= 1
        else:
            self.timer.stop()
            self.time_remaining.setText("00:00")

    def update_progress_bar(self, value):
        value = max(0, min(value, self.progressbar.maximum()))
        value = value*1000
        self.progressbar.setValue(int(value))
        self.progresslabel.setText(f"{round(value/1000, 2)}/8672.66")
        pass

    def change_steps(self):
        # Ensure that the correct amount of total steps is shown
        if self.tabWidget.currentIndex() == 0:
            self.total_steps.setText(f"{self.steps_box.value() * self.scans_box.value()}")
        elif self.tabWidget.currentIndex() == 1:
            if hasattr(self, "content") and self.content:
                self.total_steps.setText(f"{len(self.content) * self.scans_box.value()}")
            else:
                self.total_steps.setText("0")

    def showFileDialog(self):
        self.content = []
        fileName, _ = QFileDialog.getOpenFileName(
            self.tab2, "Select a .txt or .csv File", "", "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        if fileName:
            self.file_label.setText(os.path.basename(fileName))
            try:
                metadata = f"File Name: {os.path.basename(fileName)}\n"
                metadata += f"File Path: {fileName}\n"

                # Check if the file is a CSV
                if fileName.endswith(".csv"):
                    with open(fileName, "r") as file:
                        reader = csv.DictReader(file)
                        # Find the index of 'Pixel_1' and only keep columns up to and including it
                        if "Pixel_1" in reader.fieldnames:
                            pixel_idx = reader.fieldnames.index("Pixel_1")
                            columns = reader.fieldnames[:pixel_idx + 1]
                            columns = [col if col != "Pixel_1" else "Pixels" for col in columns]
                        else:
                            columns = reader.fieldnames
                        metadata += f"Columns: {', '.join(columns)}\n"
                        rows = list(reader)
                        metadata += f"Number of Rows: {len(rows)}\n"

                        if "Delay (ps)" in reader.fieldnames:
                            self.content = [float(row["Delay (ps)"]) for row in rows if row["Delay (ps)"].strip()]
                        else:
                            raise ValueError("The CSV file does not contain a 'Delay (ps)' column.")
                else:  # Assume it's a text file
                    with open(fileName, "r") as file:
                        content = file.read()
                    metadata += f"File Content Preview:\n{content[:200]}...\n"  # Show first 200 characters
                    self.text_display.setText(content)

                    # Changing self.content to a list that is accepted by measurement functions
                    lines = [item.strip() for item in content.split(",") if item.strip()]
                    if lines[0] == "ps":
                        lines = lines[1:]
                        self.content = [float(item) for item in lines]
                    elif lines[0] == "Delay (ps)":
                        lines = lines[1:]
                        self.content = [float(item) for item in lines]

                # Display metadata in the text_display widget
                self.text_display.setText(metadata)

                # Changing GUI elements to display correct values after uploading file
                self.total_steps.setText(f"{(len(self.content)) * self.scans_box.value()}")
                self.current_step.setText(f"{0}")
                self.current_scan.setText(f"{1}")

                if self.content:
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
        if self.tabWidget.currentIndex() == 1:
            if hasattr(self, "content") and self.content:
                # Update the last item to ('ps', value)
                self.content[-1] = value
                print(self.content[-1])

    def on_tab_change(self):
        if self.tabWidget.currentIndex() == 0:
            self.start_from_box.setEnabled(False)
            self.finish_time_box.setEnabled(False)
            self.start_from_box.setValue(self.exponential_start.value())
            self.finish_time_box.setValue(self.exponential_finish.value())
            self.total_steps.setText(f"{self.steps_box.value() * self.scans_box.value()}")
        elif self.tabWidget.currentIndex() == 1:
            self.start_from_box.setEnabled(True)
            self.finish_time_box.setEnabled(True)
            self.total_steps.setText(f"{len(self.content) * self.scans_box.value() if hasattr(self, 'content') else 0}")
            if hasattr(self, "content") and self.content:
                self.start_from_box.setValue(self.content[0])
                self.finish_time_box.setValue(self.content[-1])
            
    def show_error_message(self, error_message):
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Error")
        msgbox.setText("An error occurred:")
        msgbox.setInformativeText(error_message)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec()

    def disable_stop_button(self):
        self.stop_button.setEnabled(False)



if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    Bottom_right = QWidget()
    ui = Heatmap_Interface()
    ui.setupUi(Bottom_right)
    Bottom_right.show()
    sys.exit(app.exec())
