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
        self.worker_thread.process_content_signal.connect(self.worker_thread.process_content)
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
        print("Updating graph with data:", len(avg_list), len(med_list))  # Debugging
        if avg_list:
            self.probe_avg_graph.plot(range(len(avg_list)), avg_list, symbol='o', pen='r')
        elif med_list:
            self.probe_avg_graph.plot(range(len(med_list)), med_list, symbol='o', pen='b')
        pass

    def closeEvent(self, event):
        self.worker_thread.stop()  # Stop the worker thread
        self.worker_thread.wait()  # Ensure the thread has finished
        event.accept()  # Accept the close event


class Measurementworker(QThread):
    measurement_data_updated = Signal(list, list, list)
    update_delay_bar_signal = Signal(float)
    error_occurred = Signal(str)
    update_probe = Signal(list, list)
    process_content_signal = Signal(list, float, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._content: list = []
        self._orientation: str = ""
        self._shots: int = 1
        self.process = QProcess(self)
        self.process.setProgram(ironpython_executable)
        self.process.setArguments([script_path, "GetReference"])
        self.process.readyReadStandardOutput.connect(self.handle_process_output)
        self.process.readyReadStandardError.connect(self.handle_process_error)
        self.ref = None
        self.position = None

    @Slot(str, str, int)
    def start_measurement(self, content: str, orientation: str, shots: int) -> None:
        """
        Called from the GUI thread.  Stores parameters and kicks off self.run().
        """
        self._content = content
        self._orientation = orientation
        self._shots = shots
        self.start()

    def run(self):
        try:
            parsed = self.parse_script_content(self._content, self._orientation)
            if not parsed:
                self.error_occurred.emit("No valid script content parsed.")
                return
            
            self.process.start()

            self._run_measurement_loop(parsed, self._shots)  # Call the measurement loop
        
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _run_measurement_loop(self, content: list[dict], shots: int) -> None:
        """
        Example loop that calls your existing RunMeasurement() and streams data.
        Modify freely to match your real-world needs.
        """
        acc_x: list[float] = []
        acc_y: list[float] = []
        acc_err: list[float] = []

        ref = self.get_reference_value()
        position = self.get_position_value()
        print(f"Reference: {ref}, Position: {position}")

        if not self.validate_reference_and_position(ref, position, content):
            return

        if round(ref, 3) != round(position, 3):
            self.move_to_reference(ref)

        for item in content:
            if self.isInterruptionRequested():  # allow user to abort
                break

            result = self.process_content(item, ref, shots)  # hardware I/O – heavy stuff
            x, y, err = result["x"], result["y"], result["err"]

            acc_x.extend(x)
            acc_y.extend(y)
            acc_err.extend(err)

            # live update in the GUI
            self.measurement_data_updated.emit(acc_x, acc_y, acc_err)

        # Clean-up
        self._proc.close()


    @Slot(str)
    def run_script(self, argument):
        print(f"Running script with argument: {argument}")
        try:
            if self.process.state() == QProcess.Running:
                print("Waiting for the current process to finish...")
                self.process.waitForFinished()  # Wait for the current process to finish

            self.process.start(ironpython_executable, [script_path, argument])
            print(f"Command: {ironpython_executable} {script_path} {argument}")
        except Exception as e:
            self.error_occurred.emit(str(e))

    def handle_process_output(self):
        stdout_line = self.process.readAllStandardOutput().data().decode('utf-8').strip()
        if stdout_line:
            print(f"Decoded output: {stdout_line}")  # Debugging

            try:
                if "Reference position" in stdout_line:
                    self.ref = float(stdout_line.split(":")[1].strip().split()[0])
                    print(f"Reference position set to: {self.ref}")

                elif "Current position" in stdout_line:
                    self.position = float(stdout_line.split(":")[1].strip().split()[0])
                    print(f"Current position set to: {self.position}")

                elif "Moved to reference position" in stdout_line:
                    self.position = float(stdout_line.split(":")[1].strip().split()[0])
                    print(f"Moved to reference position: {self.position}")

                elif "Moved to relative position" in stdout_line:
                    self.position = float(stdout_line.split(":")[1].strip().split()[0])
                    print(f"Moved to relative position: {self.position}")

                else:
                    print("Output does not match expected format.")
                    
                # Emit a signal when position updates


            except (ValueError, IndexError) as e:
                print(f"Error parsing output: {e}")  # Debugging

        return self.ref, self.position


    def handle_process_error(self):
        stderr_line = self.process.readAllStandardError().data().decode('utf-8').strip()
        if stderr_line:
            print(f"Error output: {stderr_line}")
            self.error_occurred.emit(stderr_line)

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

    @Slot(list, int)
    def RunMeasurement(self, content, number_of_shots):

        # Step 1: Get reference value
        ref = self.get_reference_value()

        # Step 2: Get position value
        position = self.get_position_value()


        print(f"Reference: {ref}, Position: {position}")

        # Step 3: Validate reference and position
        if not self.validate_reference_and_position(ref, position, content):
            return

        # Step 4: Move to reference position if needed
        if round(ref, 3) != round(position, 3):
            self.move_to_reference(ref)
        # Step 5: Process each item in the content
        print("Signal emitted to process content.")
        self.process_content_signal.emit(content, ref, number_of_shots)
        

    
    def stop(self):
        self._is_running = False  # Safely stop the loop
        self.quit()
        self.wait()

    def get_reference_value(self):
        self.run_script("GetReference")
        while self.ref is None:
            QCoreApplication.processEvents()  # Allow the event loop to process signals
        return self.ref

    def get_position_value(self):
        self.run_script("GetPosition")
        while self.position is None:
            QCoreApplication.processEvents()  # Allow the event loop to process signals
        return self.position

    def validate_reference_and_position(self, ref, position, content):
        unit_multipliers = {'ns': 1, 'ps': 1000, 'fs': 1000000}
        limits = {'ns': 8.672, 'ps': 8672, 'fs': 8672000}

        for unit, value in content:
            if unit in unit_multipliers:
                adjusted_ref = ref * unit_multipliers[unit]
                if not (0 <= adjusted_ref + value <= limits[unit]):
                    self.error_occurred.emit(f"Reference point is out of range. {value}")
                    return False
        return True
    
    def move_to_reference(self, ref):
        self.run_script("GoToReference")
        while abs(self.position - ref) > 0.01:
            QCoreApplication.processEvents()  # Wait for the position to update
        self.update_delay_bar_signal.emit(ref * 1000)

    @Slot(list, float, int)
    def process_content(self, blk, ref, number_of_shots):
        blocks = []
        delaytimes = []
        dA_inputs_avg = []
        dA_inputs_med = []
        last_item = 0
        barvalue = ref * 1000
        counter = 0
        print("A")

        unit = blk[0].lower()
        pos = blk[1]

        if unit in ['ps', 'picosecond', 'picoseconds']:
            pos /= 1000
        elif unit in ['fs', 'femtosecond', 'femtoseconds']:
            pos /= 1000000

        pos -= last_item
        barvalue = ref + pos * 1000

        self.run_script(f"MoveRelative {pos}")
        self.update_delay_bar_signal.emit(barvalue)

        # Simulate measurement
        time.sleep(2)
        block_buffer = camera(number_of_shots, counter)
        block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
        blocks.append(block_2d_array)

        if unit in ['ns', 'nanosecond', 'nanoseconds']:
            last_item = blk[1]
        elif unit in ['ps', 'picosecond', 'picoseconds']:
            last_item = blk[1] / 1000
        elif unit in ['fs', 'femtosecond', 'femtoseconds']:
            last_item = blk[1] / 1000000

        probe_avg, probe_med, dA_avg, dA_med = delta_a_block(block_2d_array)
        self.update_probe.emit(probe_avg[0], probe_med[0])  # Emit probe data incrementally
        dA_average = np.mean(dA_avg, axis=0)
        dA_median = np.median(dA_med, axis=0)

        delaytimes.append(last_item) # Convert to picoseconds for display
        dA_inputs_avg.append(np.mean(dA_average))
        dA_inputs_med.append(np.median(dA_median))
        counter += 1

        return blocks


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DLSWindow()
    worker = Measurementworker
    window.show()
    window.run_command_signal.emit("GetPosition")
    sys.exit(app.exec())
    sys.exit(worker.stop())
