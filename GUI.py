from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sys
import subprocess
import pyqtgraph as pg
import numpy as np
from main import *
from camera import *
import matplotlib.pyplot as plt
import random
import time
ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"

class DLSWindow(QMainWindow):
    progress_updated = Signal(int)
    trigger_worker_run = Signal(str, str, int)
    run_command_signal = Signal(str)

    

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delayline GUI")
        self.worker_thread = Measurementworker()
        self.worker_thread.measurement_data_updated.connect(self.handle_measurement_data)
        self.worker_thread.update_delay_bar_signal.connect(self.update_delay_bar)
        self.worker_thread.error_occurred.connect(self.show_error_message)
        self.worker_thread.update_probe.connect(self.update_probe_graph)
        self.run_command_signal.connect(self.worker_thread.run_script)
        self.worker_thread.start()


        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layouts
        left_layout = QVBoxLayout()
        self.probe_avg_graph = pg.PlotWidget()
        left_layout.addWidget(self.probe_avg_graph)
        self.probe_avg_graph.setTitle("Probe Spectrum")
        self.probe_avg_graph.setLabel('left', 'Probe')
        self.probe_avg_graph.setLabel('bottom', 'Delay (ps)')

        if not hasattr(self, 'probe_inputs_avg'):
            self.probe_inputs_avg = []
        if not hasattr(self, 'probe_inputs_med'):
            self.probe_inputs_med = []

        
        self.probe_avg_graph.setBackground('w')

        self.probe_combobox = QComboBox()
        self.probe_combobox.addItems(["Average", "Median"])
        self.probe_combobox.setCurrentText("Average")
        left_layout.addWidget(self.probe_combobox)

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






    def Initialize(self):
        self.run_command_signal.emit("Initialize")

    def Disable_click(self):
        self.run_command_signal.emit("Disable")

    def Move_click(self):
        self.run_command_signal.emit("MovePositive")

    def Move_back_click(self):
        self.run_command_signal.emit("MoveNegative")

    def SetReference(self):
        self.run_command_signal.emit("SetReference")

    def GoToReference(self):
        self.run_command_signal.emit("GoToReference")
    

    def LabelChange(self):
        selected = self.delay_unit.currentText()
        if selected == "ns":
            self.delay_label.setText("Delay (ns):")
        elif selected == "ps":
            self.delay_label.setText("Delay (ps):")
        elif selected == "fs":
            self.delay_label.setText("Delay (fs):")

    def handle_measurement_data(self, delaytimes, avg, med):
        # Process and update GUI based on measurement data
        print(f"Delaytimes: {delaytimes}, Avg: {avg}, Med: {med}")
        self.update_delay_bar(delaytimes[-1])

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
    

    def update_probe_graph(self, avg_list, med_list):

        print("Updating graph with data:", len(self.probe_inputs_avg), len(self.probe_inputs_med))  # Debugging


        if len(avg_list) > 0:
            print("Avg List:", avg_list)
            self.probe_avg_graph.plot(range(len(avg_list)), avg_list, symbol='o', pen='r')
                
        elif self.probe_combobox.currentText() == "Median":
            if len(med_list) > 0:
                self.probe_avg_graph.plot(med_list, symbol='o', pen='b')
            else:
                print("No data for Median plot.")
        pass

    def closeEvent(self, event):
        self.worker_thread.stop()
        event.accept()
        

class Measurementworker(QThread):
    measurement_data_updated = Signal(list, list, list)
    update_delay_bar_signal = Signal(float)
    error_occurred = Signal(str)
    update_probe = Signal(list, list)

    def __init__(self):
        super().__init__()
        self.process = None
        self.timer = QTimer(self)
        self.timer.setInterval(100)  # Check every 100ms
        self.timer.timeout.connect(self.check_process_output)


    def run(self):
        self.timer.start()
        pass


    @Slot(str)
    def run_script(self, argument):
        print(f"Running script with argument: {argument}")
        try:
            self.process = subprocess.Popen(
                [ironpython_executable, script_path, argument],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            self.error_occurred.emit(str(e))

    def check_process_output(self):
        if self.process:
            stdout_line = self.process.stdout.readline()
            
            if stdout_line:
                decoded_output = stdout_line.decode('utf-8').strip()
                print(f"Decoded output: {decoded_output}")  # Debugging
                try:
                    numerical_value = float(decoded_output)
                    self.update_delay_bar_signal.emit(numerical_value)  # Emit value for UI update
                    print(f"Emitting numerical value: {numerical_value}")  # Debugging
                    return numerical_value  # Return value for further use
                except ValueError:
                    print("Invalid numerical output received.")  # Debugging
                    return None

            return None


    @Slot(str, str, int)
    def parse_and_run(self, content: str, orientation: str, shots: int):
        parsed = self.parse_script_content(content, orientation)
        if not parsed:
            self.error_occurred.emit("No valid script content parsed.")
            return
        self.RunMeasurement(parsed, shots)

    def parse_script_content(self, content: str, orientation: str):
        lines = content.splitlines()
        parsed_content = []
        for line in lines:
            items = line.split(",")
            for item in items:
                item = item.strip()
                if item:
                    letters = ""
                    numbers = ""
                    for char in item:
                        if char.isdigit() or char == "." or char == "-":
                            numbers += char
                        else:
                            letters += char
                    if numbers:
                        try:
                            parsed_content.append((letters.strip(), float(numbers)))
                        except ValueError:
                            parsed_content.append((letters.strip(), None))
                    else:
                        parsed_content.append((letters.strip(), None))
        if orientation == 'backwards':
            parsed_content.reverse()
        elif orientation == 'random':
            random.shuffle(parsed_content)
        return parsed_content

    def RunMeasurement(self, content, number_of_shots):
        blocks = []
        delaytimes = []
        dA_inputs_avg = []
        dA_inputs_med = []

        self.run_script("GetReference")
        ref = self.check_process_output()
        self.run_script("GetPosition")
        position = self.check_process_output()

        # try:
        #     ref = float(ref.decode('utf-8').strip())
        #     position = float(position.decode('utf-8').strip())
        # except ValueError:
        #     self.error_occurred.emit("Failed to parse reference/position from script.")
        #     return

        unit_multipliers = {'ns': 1, 'nanosecond': 1, 'nanoseconds': 1,
                            'ps': 1000, 'picosecond': 1000, 'picoseconds': 1000,
                            'fs': 1000000, 'femtosecond': 1000000, 'femtoseconds': 1000000}

        limits = {'ns': 8.672, 'ps': 8672, 'fs': 8672000}

        for unit, value in content:
            if unit in unit_multipliers:
                adjusted_ref = ref * unit_multipliers[unit]
                if not (0 <= adjusted_ref + value <= limits[unit]):
                    self.error_occurred.emit(f"Reference point is out of range. {value}")
                    return

        if round(ref, 3) != round(position, 3):
            self.run_script("GoToReference")
            print(self.check_process_output())
            self.update_delay_bar_signal.emit(ref * 1000)


        last_item = 0
        barvalue = ref * 1000
        for item in content:
            unit = item[0].lower()
            pos = item[1]

            if unit in ['ps', 'picosecond', 'picoseconds']:
                pos /= 1000
            elif unit in ['fs', 'femtosecond', 'femtoseconds']:
                pos /= 1000000

            pos -= last_item
            barvalue = ref + pos * 1000

            self.run_script(f"MoveRelative {pos}")
            print(self.check_process_output())
            self.update_delay_bar_signal.emit(barvalue)

            block_buffer = camera(number_of_shots, content.index(item))
            block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
            blocks.append(block_2d_array)

            if unit in ['ns', 'nanosecond', 'nanoseconds']:
                last_item = item[1]
            elif unit in ['ps', 'picosecond', 'picoseconds']:
                last_item = item[1] / 1000
            elif unit in ['fs', 'femtosecond', 'femtoseconds']:
                last_item = item[1] / 1000000

            probe_avg, probe_med, dA_avg, dA_med = delta_a_block(block_2d_array)
            dA_average = np.mean(dA_avg, axis=0)
            dA_median = np.median(dA_med, axis=0)

            delaytimes.append(last_item)
            dA_inputs_avg.append(np.mean(dA_average))
            dA_inputs_med.append(np.median(dA_median))

            self.measurement_data_updated.emit(delaytimes, dA_inputs_avg, dA_inputs_med)
            self.update_probe.emit(probe_avg[0], probe_med[0])

        self.delaytimes = delaytimes
        self.probe_inputs_avg = probe_avg[0]
        self.probe_inputs_med = probe_med[0]
        return blocks
    
    def stop(self):
        self._is_running = False  # Safely stop the loop
        self.quit()
        self.wait()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DLSWindow()
    window.show()
    window.run_command_signal.emit("GetPosition")
    sys.exit(app.exec())
