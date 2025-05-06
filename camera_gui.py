from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import pyqtgraph as pg
import sys
from WorkerThread import *
import numpy as np                      
from cursor_plot import TAPlotWidget

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

        # Bottom-righ quarter layout
        top_left_layout = QVBoxLayout()
        top_right_layout = QVBoxLayout()
        bottom_left_layout = QVBoxLayout()
        

        # TAPlotWidget 
        delay_times   = np.array([-0.2, 0.0, 0.2, 0.5, 1.0])
        pixel_indexes = np.arange(10)
        self.ta_widgets = TAPlotWidget(delay_times, pixel_indexes)
        top_left_layout.addWidget(self.ta_widgets.canvas_heatmap)
        top_right_layout.addWidget(self.ta_widgets.canvas_plot1)
        bottom_left_layout.addWidget(self.ta_widgets.canvas_plot2)

        # old dA_graph 
        # self.dA_avg_graph = pg.PlotWidget()
        # top_left_layout.addWidget(self.dA_avg_graph)
        # self.dA_avg_graph.setTitle("Delta A Graph")
        # self.dA_avg_graph.setLabel('left', 'Delta A')
        # self.dA_avg_graph.setLabel('bottom', 'Delay (ps)')

        self.delaytimes = []
        self.dA_inputs_avg = []
        self.dA_inputs_med = []


        self.dA_Combobox = QComboBox()
        self.dA_Combobox.addItems(["Average", "Median"])
        self.dA_Combobox.setCurrentText("Average")
        self.dA_Combobox.currentIndexChanged.connect(self.avg_med_toggle)
        top_left_layout.addWidget(self.dA_Combobox)
        # if self.dA_Combobox.currentText() == "Average":
        #     self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_avg, symbol='o', pen=None)
        # elif self.dA_Combobox.currentText() == "Median":
        #     self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_med, symbol='o', pen=None)

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
        self.grid_layout.addItem(top_right_layout, 0, 1)
        self.grid_layout.addItem(bottom_left_layout, 1, 0)
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

    @Slot(float, float, float)
    def update_graph(self, delaytimes, dA_inputs_avg, dA_inputs_med):
        """Update the graph with new delaytimes and dA_inputs."""
        self.delaytimes.append(delaytimes)
        self.dA_inputs_avg.append(dA_inputs_avg)
        self.dA_inputs_med.append(dA_inputs_med)

        # Clear the graph and re-plot with new data
        if self.dA_Combobox.currentText() == "Average":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_avg, symbol='o')
        if self.dA_Combobox.currentText() == "Median":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_med, symbol='o')
    
    def avg_med_toggle(self):
        """Toggle between average and median."""

        if self.dA_Combobox.currentText() == "Average":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_avg, symbol='o')
        elif self.dA_Combobox.currentText() == "Median":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_med, symbol='o')

    def start_measurement(self, content, orientation, shots):
        self.worker = Measurementworker(content, orientation, shots)
        self.worker.measurement_data_updated.connect(self.update_graph, Qt.QueuedConnection)
        self.worker.error_occurred.connect(self.show_error_message)  # Optional error handler
        self.worker.update_delay_bar_signal.connect(self.update_progress_bar)
        self.worker.update_delay_bar_signal.connect(self.DLSWindow.update_delay_bar)
        self.worker.update_probe.connect(self.DLSWindow.update_probe_graph, Qt.QueuedConnection)
        self.worker.start()

class DLSWindow(QMainWindow):
    progress_updated = Signal(int)
    run_command_signal = Signal(str)

    

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delayline GUI")



        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layouts
        left_layout = QVBoxLayout()
        self.probe_avg_graph = pg.PlotWidget()
        left_layout.addWidget(self.probe_avg_graph)
        self.probe_avg_graph.setTitle("Probe Spectrum")
        self.probe_avg_graph.setLabel('left', 'Probe')
        self.probe_avg_graph.setLabel('bottom', 'Wavelength (nm)')
        self.probe_avg_graph.setBackground('w')

        self.probe_inputs_avg = []
        self.probe_inputs_med = []

        


        self.probe_combobox = QComboBox()
        self.probe_combobox.addItems(["Average", "Median"])
        self.probe_combobox.setCurrentText("Average")
        left_layout.addWidget(self.probe_combobox)
        if self.probe_combobox.currentText() == "Average":
            self.probe_avg_graph.plot(range(len(self.probe_inputs_avg)), self.probe_inputs_avg, symbol='o', pen=None)
        elif self.probe_combobox.currentText() == "Median":
            self.probe_avg_graph.plot(range(len(self.probe_inputs_med)), self.probe_inputs_med, symbol='o', pen=None)

        self.probe_combobox.currentIndexChanged.connect(self.update_probe_graph)

        right_layout = QVBoxLayout()

        hbox = QHBoxLayout()

        initialize_button = QPushButton("Initialize")
        initialize_button.clicked.connect(self.Initialize)
        hbox.addWidget(initialize_button)

        disable_button = QPushButton("Disable/Ready")
        disable_button.clicked.connect(self.Disable_click)
        hbox.addWidget(disable_button)

        move_neg_button = QPushButton("Move -100ps")
        move_neg_button.clicked.connect(self.Move_back_click)
        hbox.addWidget(move_neg_button)

        move_pos_button = QPushButton("Move +100ps")
        move_pos_button.clicked.connect(self.Move_click)
        hbox.addWidget(move_pos_button)

        right_layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        self.delay_input = QLineEdit()
        self.delay_input.setPlaceholderText("Enter delay time")
        self.delay_input.setValidator(QDoubleValidator(-8672000.0, 8672000.0, 20, self))
        self.delay_input.validator().setLocale(QLocale(QLocale.C))
        self.delay_input.returnPressed.connect(self.Submitted)

        self.delay_unit = QComboBox()
        self.delay_unit.addItems(["ns", "ps", "fs"])
        self.delay_unit.currentIndexChanged.connect(self.LabelChange)

        hbox2.addWidget(self.delay_input)
        hbox2.addWidget(self.delay_unit)

        hbox3 = QHBoxLayout()

        self.delay_label = QLabel("Delay (ns):", self)
        hbox3.addWidget(self.delay_label)

        self.delay_bar = QProgressBar()
        self.delay_bar.setMinimum(0)
        self.delay_bar.setMaximum(8672)  # max picoseconds delay
        self.delay_bar.setValue(0)
        self.delay_bar.setFormat(f"/8672")

        hbox3.addWidget(self.delay_bar)

        hbox4 = QHBoxLayout()

        setref_button = QPushButton("Set Reference")
        setref_button.clicked.connect(self.SetReference)
        hbox4.addWidget(setref_button)

        gotoref_button = QPushButton("Go to Reference")
        gotoref_button.clicked.connect(self.GoToReference)
        hbox4.addWidget(gotoref_button)


        
        right_layout.addLayout(hbox2)
        right_layout.addLayout(hbox3)
        right_layout.addLayout(hbox4)

        central_layout = QHBoxLayout()
        central_layout.addLayout(left_layout)
        central_layout.addLayout(right_layout)
        central_widget.setLayout(central_layout)


    def LabelChange(self):
        selected = self.delay_unit.currentText()
        if selected == "ns":
            self.delay_label.setText("Delay (ns):")
        elif selected == "ps":
            self.delay_label.setText("Delay (ps):")
        elif selected == "fs":
            self.delay_label.setText("Delay (fs):")


    def Submitted(self):
        try:
            unit = self.delay_unit.currentText()
            value = float(self.delay_input.text())
            current_bar_value = self.delay_bar.value()*1000  # In ps

            if unit == "ns":
                value_ps = value * 1000
            elif unit == "ps":
                value_ps = value
            elif unit == "fs":
                value_ps = value / 1000
            else:
                raise ValueError("Unknown time unit.")

            if 0 <= current_bar_value + value_ps <= 8672:
                value_ns = value_ps / 1000  # Convert to ns for script
                self.run_command_signal.emit(f"MoveRelative {value_ns}")
                print(f"Emitting command: MoveRelative {value_ns}")

            else:
                raise ValueError("Value is out of range.")
        except ValueError as ve:
            self.show_error_message(str(ve))
        except Exception as e:
            self.show_error_message(str(e))



    def update_delay_bar(self, value):
        value = max(0, min(value, self.delay_bar.maximum()))  # Keep in picoseconds
        self.delay_bar.setValue(round(value))
        self.delay_bar.setFormat(f"{int(value)}/8672")
        self.progress_updated.emit(value)
        pass



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
        return content
    
    @Slot(list, list)
    def update_probe_graph(self, avg_list, med_list):
        self.probe_avg_graph.clear()  # Clear the graph before plotting new data
        self.probe_inputs_avg = avg_list
        self.probe_inputs_med = med_list
        if self.probe_combobox.currentText() == "Average":
            print("Plotting average data")  # Debugging
            self.probe_avg_graph.plot(range(len(avg_list)), avg_list, symbol='o', pen='r')
        elif self.probe_combobox.currentText() == "Median":
            med_list = [1, 2, 3, 4, 5]  # Example data for median
            self.probe_avg_graph.plot(range(len(med_list)), med_list, symbol='o', pen='b')
        pass


    def Initialize(self):
        self.start_measurement("Initialize", "ButtonPress", 0)

    def Disable_click(self):
        self.start_measurement("Disable", "ButtonPress", 0)

    def Move_click(self):
        self.start_measurement("MovePositive", "ButtonPress", 0)

    def Move_back_click(self):
        self.start_measurement("MoveNegative", "ButtonPress", 0)

    def SetReference(self):
        self.start_measurement("SetReference", "ButtonPress", 0)

    def GoToReference(self):
        self.start_measurement("GoToReference", "ButtonPress", 0)
    
    def start_measurement(self, content, orientation, shots):
        self.worker = Measurementworker(content, orientation, shots)
        self.worker.start()


    def closeEvent(self, event):
        self.worker_thread.stop()  # Stop the worker thread
        self.worker_thread.wait()  # Ensure the thread has finished
        event.accept()  # Accept the close event

if __name__ == "__main__":
    app = QApplication([])
    window = ShotDelayApp()
    window.show()

    window.start_fake_measurement()

    sys.exit(app.exec())