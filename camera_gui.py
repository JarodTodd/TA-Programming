from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import pyqtgraph as pg
import sys
from GUI import *


class ShotDelayApp(QWidget):
    trigger_worker_run = Signal(str, str, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Interface")
        self.DLSWindow = DLSWindow()  
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()
        print("Setting up UI")
        # Main layout as a grid
        self.grid_layout = QGridLayout()

        # Blank spaces for top-left, top-right, and bottom-left quarters
        self.grid_layout.addWidget(QWidget(), 0, 1)  # Top-right
        self.grid_layout.addWidget(QWidget(), 1, 0)  # Bottom-left

        # Bottom-right quarter layout
        top_left_layout = QVBoxLayout()
        self.dA_avg_graph = pg.PlotWidget()
        top_left_layout.addWidget(self.dA_avg_graph)
        self.dA_avg_graph.setTitle("Delta A Graph")
        self.dA_avg_graph.setLabel('left', 'Delta A')
        self.dA_avg_graph.setLabel('bottom', 'Delay (ps)')

        self.delaytimes = []
        self.dA_inputs_avg = []
        self.dA_inputs_med = []

        # Plot the initial graph based on the combobox selection


        self.dA_avg_graph.setBackground('w')
        self.dA_avg_graph.getAxis('bottom').setLogMode(True)

        self.dA_Combobox = QComboBox()
        self.dA_Combobox.addItems(["Average", "Median"])
        self.dA_Combobox.setCurrentText("Average")
        self.dA_Combobox.currentIndexChanged.connect(self.avg_med_toggle)
        top_left_layout.addWidget(self.dA_Combobox)
        if self.dA_Combobox.currentText() == "Average":
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_avg, symbol='o', pen=None)
        elif self.dA_Combobox.currentText() == "Median":
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_med, symbol='o', pen=None)

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
        hbox = QHBoxLayout()

        # File upload button
        file_upload_button = QPushButton("Upload File")
        file_upload_button.clicked.connect(self.showFileDialog)

        # File label and text display
        self.file_label = QLabel("No file selected", self)
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(False)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 8672)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("/8672")

        # Script execution buttons
        vbox = QVBoxLayout()
        self.runscript_button = QPushButton("Run Script")
        self.runscript_button.clicked.connect(lambda: self.start_measurement(self.text_display.toPlainText(), "forward", int(self.shots_input.text())))
        self.runscript_button.setEnabled(False)

        self.runscript_backwards_button = QPushButton("Run Script Backwards")
        self.runscript_backwards_button.clicked.connect(lambda: self.start_measurement(self.text_display.toPlainText(), "backward", int(self.shots_input.text())))
        self.runscript_backwards_button.setEnabled(False)

        self.runscript_random_button = QPushButton("Run Script Random")
        self.runscript_random_button.clicked.connect(lambda: self.start_measurement(self.text_display.toPlainText(), "random", int(self.shots_input.text())))
        self.runscript_random_button.setEnabled(False)

        vbox.addWidget(self.runscript_button)
        vbox.addWidget(self.runscript_backwards_button)
        vbox.addWidget(self.runscript_random_button)

        # Add widgets to hbox5
        hbox.addLayout(vbox)
        hbox.addWidget(file_upload_button)
        hbox.addWidget(self.file_label)
    

        # Add widgets to the bottom-right layout
        bottom_right_layout.addLayout(self.form_layout)
        bottom_right_layout.addWidget(self.status_label)
        bottom_right_layout.addLayout(hbox)
        bottom_right_layout.addWidget(self.text_display)
        bottom_right_layout.addWidget(self.progress_bar)

        # Add the bottom-right layout to the grid layout
        spacer1 = QSpacerItem(400, 400)
        spacer2 = QSpacerItem(400, 400)
        spacer3 = QSpacerItem(400, 400)
        self.grid_layout.addItem(top_left_layout, 0, 0)
        self.grid_layout.addItem(spacer2, 0, 1)
        self.grid_layout.addItem(spacer3, 1, 0)
        self.grid_layout.addLayout(bottom_right_layout, 1, 1)  # Bottom-right

        # Set the grid layout as the main layout
        self.setLayout(self.grid_layout)

        # Connect signals
        self.shots_input.textChanged.connect(self.validate_inputs)
        self.text_display.textChanged.connect(self.validate_inputs)


    def update_progress_bar(self, value):
        """Update the local progress bar with the value from DLSWindow."""
        print("Updating progress bar with value:", value)
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{round(value)}/8672")

    def show_error_message(self, error_message):
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Error")
        msgbox.setText("An error occurred:")
        msgbox.setInformativeText(error_message)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec()


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


    def validate_inputs(self):
        try:
            shots = int(self.shots_input.text())
            valid = shots > 0 and self.text_display.toPlainText() != ""
        except ValueError:
            valid = False
        self.runscript_button.setEnabled(valid)
        self.runscript_backwards_button.setEnabled(valid)
        self.runscript_random_button.setEnabled(valid)

    def update_graph(self, delaytimes, dA_inputs_avg, dA_inputs_med):
        """Update the graph with new delaytimes and dA_inputs."""
        self.delaytimes = delaytimes
        self.dA_inputs_avg = dA_inputs_avg
        self.dA_inputs_med = dA_inputs_med

        # Clear the graph and re-plot with new data
        if self.dA_Combobox.currentText() == "Average":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, dA_inputs_avg, symbol='o', pen=None)
        if self.dA_Combobox.currentText() == "Median":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, dA_inputs_med, symbol='o', pen=None)
    
    def avg_med_toggle(self):
        """Toggle between average and median."""

        if self.dA_Combobox.currentText() == "Average":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_avg, symbol='o', pen=None)
        elif self.dA_Combobox.currentText() == "Median":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_med, symbol='o', pen=None)

    def start_measurement(self, content, orientation, shots):
        self.worker = Measurementworker(content, orientation, shots)
        self.worker.measurement_data_updated.connect(self.update_graph)
        self.worker.error_occurred.connect(self.show_error_message)  # Optional error handler
        self.worker.update_delay_bar_signal.connect(self.update_progress_bar)
        self.worker.start()


if __name__ == "__main__":
    app = QApplication([])
    window = ShotDelayApp()
    window.show()
    sys.exit(app.exec())
