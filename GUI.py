from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sys
import subprocess
import pyqtgraph as pg
import numpy as np
from main import *
from camera import *

ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"

class DLSWindow(QMainWindow):
    progress_updated = Signal(int)
    measurement_data_updated = Signal(list, list, list)

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
        self.probe_avg_graph.setTitle("Delta A Graph")
        self.probe_avg_graph.setLabel('left', 'Probe')
        self.probe_avg_graph.setLabel('bottom', 'Delay (ps)')

        self.delaytimes = []
        self.probe_inputs_avg = []
        self.probe_inputs_med = []

        # Plot the initial graph based on the combobox selection


        self.probe_avg_graph.setBackground('w')
        self.probe_avg_graph.getAxis('bottom').setLogMode(True)

        self.probe_combobox = QComboBox()
        self.probe_combobox.addItems(["Average", "Median"])
        self.probe_combobox.setCurrentText("Average")
        left_layout.addWidget(self.probe_combobox)
        if self.probe_combobox.currentText() == "Average":
            self.probe_avg_graph.plot(self.delaytimes, self.probe_inputs_avg, symbol='o')
        elif self.probe_combobox.currentText() == "Median":
            self.probe_avg_graph.plot(self.delaytimes, self.probe_inputs_med, symbol='o', pen=None)
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

    def run_script(self, argument):
        try:
            result = subprocess.Popen(
                [ironpython_executable, script_path, argument],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = result.communicate()
            print(stdout)
            movement = ["Disable", "SetReference", "GetReference", "GetPosition"]
            if argument not in movement:

                # Decode the output
                decoded_output = stdout.decode('utf-8')

                # Strip unwanted characters and convert to float
                clean_output = decoded_output.strip()
                if clean_output:  # Ensure the output is not empty
                    numerical_value = float(clean_output)
                else:
                    numerical_value = 0.0  # Default to 0 if output is empty

                # Update the delay progress bar with the numerical value
                self.update_delay_bar(numerical_value)

        except Exception as e:
            print(f"Error executing IronPython script: {e}")
        return stdout

    def Initialize(self):
        self.run_script("Initialize")

    def Disable_click(self):
        self.run_script("Disable")

    def Move_click(self):
        self.run_script("MovePositive")

    def Move_back_click(self):
        self.run_script("MoveNegative")

    def SetReference(self):
        self.run_script("SetReference")

    def GoToReference(self):
        self.run_script("GoToReference")
    
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
            barvalue = self.delay_bar.value()

            if unit == "ns":
                barvalue_ns = self.delay_bar.value() / 1000
                if 0 <= value <= (8.672 - barvalue_ns) or (value < 0 and abs(value) <= barvalue_ns):
                    self.run_script(f"MoveRelative {value}")
                    self.update_delay_bar(barvalue + value*1000)
                else:
                    raise ValueError(f"Value is out of range.")
            elif unit == "ps":
                if 0 <= value <= (8672 - barvalue) or (value < 0 and abs(value) <= barvalue):
                    self.run_script(f"MoveRelative {value/1000}")
                    self.update_delay_bar(barvalue + value)
                else:
                    raise ValueError(f"Value is out of range.")
            elif unit == "fs":
                barvalue_fs = self.delay_bar.value()*1000
                if 0 <= value <= (8672000 - barvalue_fs) or (value < 0 and abs(value) <= barvalue_fs):
                    self.run_script(f"MoveRelative {value/1000000}")
                    self.update_delay_bar(barvalue + value/1000)
                else:
                    raise ValueError(f"Value is out of range.")
        except ValueError as ve:
            self.show_error_message(str(ve))
        except Exception as e:
            self.show_error_message(str(e))

    def update_delay_bar(self, value):
        value = max(0, min(value, self.delay_bar.maximum()))*1000  # Ensure value is within the range
        self.delay_bar.setValue(round(value, 3))
        self.delay_bar.setFormat(f"{int(value)}/8672")
        self.progress_updated.emit(value)

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
    
    def RunMeasurement(self, content, number_of_shots):
        blocks = []
        delaytimes = []
        dA_inputs_avg = []
        dA_inputs_med = []
        probe_inputs_avg = []
        probe_inputs_med = []

        ref = self.run_script("GetReference")
        position = self.run_script("GetPosition")

        ref = float(ref.decode('utf-8').strip())
        position = float(position.decode('utf-8').strip())

        for item in content:
            if item[0]  == 'ns' or item[0] == 'nanosecond' or item[0] == 'nanoseconds':
                if ref + item[1] < 0:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
                if ref + item[1] > 8.672:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
            elif item[0] == 'ps' or item[0] == 'picosecond' or item[0] == 'picoseconds':
                if ref*1000 + item[1] < 0:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
                if ref*1000 + item[1] > 8672:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
            elif item[0] == 'fs' or item[0] == 'femtosecond' or item[0] == 'femtoseconds':
                if ref*1000000 + item[1] < 0:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
                if ref*1000000 + item[1] > 8672000:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return

        if round(ref, 3) != round(position, 3):
            self.run_script("GoToReference")
            self.update_delay_bar(ref*1000)

        last_item = 0
        for item in content:
            barvalue = self.delay_bar.value()
            unit = item[0].lower()
            pos = item[1]

            # Convert position to nanoseconds
            if unit in ['ps', 'picosecond', 'picoseconds']:
                pos /= 1000
            elif unit in ['fs', 'femtosecond', 'femtoseconds']:
                pos /= 1000000

            # Adjust position relative to the last item
            pos -= last_item

            print(f"pos: {pos}, last_item: {last_item}, item: {item}, barvalue: {barvalue}")

            # Move and update delay bar
            self.run_script(f"MoveRelative {pos}")
            self.update_delay_bar(barvalue + pos * 1000)

            print(f"Delay is {item[1]}")
            block_buffer = camera(number_of_shots, content.index(item))
            block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
            blocks.append(block_2d_array)

            # Update last_item for the next iteration
            if unit in ['ns', 'nanosecond', 'nanoseconds']:
                last_item = item[1]
            elif unit in ['ps', 'picosecond', 'picoseconds']:
                last_item = item[1] / 1000
            elif unit in ['fs', 'femtosecond', 'femtoseconds']:
                last_item = item[1] / 1000000

            probe_avg, probe_med, dA_avg, dA_med = delta_a_block(block_2d_array)
            dA_average = np.mean(dA_avg, axis=0)
            dA_median = np.median(dA_med, axis=0)

            delaytimes.append(last_item) # Convert to picoseconds for display
            dA_inputs_avg.append(np.mean(dA_average))
            dA_inputs_med.append(np.median(dA_median))

            self.measurement_data_updated.emit(delaytimes, dA_inputs_avg, dA_inputs_med)

            probe_average = np.mean(probe_avg, axis=0)
            probe_median = np.median(probe_med, axis=0)
            self.probe_inputs_avg.append(np.mean(probe_average))
            self.probe_inputs_med.append(np.median(probe_median))
            self.delaytimes = delaytimes
            QCoreApplication.processEvents()

        return blocks


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DLSWindow()
    window.show()
    result = subprocess.Popen(
        [ironpython_executable, script_path, "GetPosition"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, _ = result.communicate()
    window.update_delay_bar(float(stdout.decode('utf-8').strip()))
    sys.exit(app.exec())
