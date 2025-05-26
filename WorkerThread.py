from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sys
import numpy as np
from main import *
from camera import *
import random
import time
import threading

ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"

class ProbeThread(QThread):
    probe_update = Signal(np.ndarray, np.ndarray)
    dA_update = Signal(np.ndarray, np.ndarray)

    def __init__(self, shots = 1000, parent: QObject | None = None):
        super().__init__(parent)
        self.shots = shots
        self.running = True
        self.probe_processor = ComputeData()
        self.dA_processor =  ComputeData()
    
    def run(self):
        while self.running:
            block_buffer = camera(self.shots, 0)
            block_2d_array = np.array(block_buffer).reshape(self.shots, 1088)

            probe_avg, probe_med, dA_average, dA_median = self.probe_processor.delta_a_block(block_2d_array)

            if probe_avg == None or probe_med == None:
                continue

            self.probe_update.emit(probe_avg[-1], probe_med[-1])
            self.dA_update.emit(dA_average[-1], dA_median[-1])
    
    def stop(self):
        self.running = False
        self.quit()
        self.wait()
            

class Measurementworker(QThread):
    measurement_data_updated = Signal(float, float, float)
    update_delay_bar_signal = Signal(float)
    update_ref_signal = Signal(float)
    error_occurred = Signal(str)
    update_probe = Signal(list, list)
    update_dA = Signal(list, list)
    start_process_signal = Signal(str)

    plot_row_update = Signal(float, np.ndarray, np.ndarray)

    def __init__(self, content, orientation, shots, scans):
        super().__init__()
        self._is_running = True
        self.process = None
        self._content = content
        self._orientation: str = orientation
        self._shots: int = shots
        self._scans = scans
        self.ref = None
        self.position = None
        self.data_processor = ComputeData()

    def update_command(self, content, orientation, shots, scans):
        self._orientation = orientation
        self._content = content
        self._shots = shots
        self._scans = scans

    @Slot(str)
    def run(self):
        print(f"This is {self._orientation}")
        if self._orientation in ("Regular", "Backwards", "Random"):
            try:
                self._run_measurement_loop(self._content, self._shots, self._scans)
            except Exception as e:
                self.error_occurred.emit(str(e))

        if self._orientation == "ButtonPress":
            argument = self._content
            print(f"Running script with argument: {argument}")
            try:
                self.start_process_signal.emit(argument)
            except Exception as e:
                self.error_occurred.emit(str(e))

        if self._orientation == "StartUp":
            try:
                self.start_process_signal.emit("StartGUI")
                ref, pos = self.start_gui()
                print(f"Position: {pos}, Reference: {ref}")

            except Exception as e:
                self.error_occurred.emit(str(e))
        
    def _run_measurement_loop(self, content: list[dict], shots: int, scans) -> None:
        """
        Example loop that calls your existing RunMeasurement() and streams data.
        Modify freely to match your real-world needs.
        """
        print("Starting measurement loop...")
        self.counter = 0
        self.teller = 0
        self.last_item = 0
        self.barvalue = 0
        self.nos = 0
        ref, position = self.start_gui()

        if not self.validate_reference_and_position(ref, position, content):
            return
        
        if self._orientation == "Backwards":
            content.reverse()
        elif self._orientation == "Random":
            random.shuffle(content)

        if round(ref, 3) != round(position, 3):
            self.move_to_reference(ref)
        self.barvalue = ref
        self.update_delay_bar_signal.emit(ref)
        for i in range(0, scans):
            for item in content:
                if item == content[0]:
                    self.nos += 1
                    print(f"Starting scan {self.nos} of {scans}")
                print(item)
                if self.isInterruptionRequested():
                    break
                
                result = self.process_content(item, ref, shots)
                self.counter += 1

    def handle_process_output(self):
        stdout_line = self.process.readAllStandardOutput().data().decode('utf-8').strip()
        if stdout_line:

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

                elif "Starting GUI with position" in stdout_line:
                    parts = stdout_line.split(":")
                    if len(parts) >= 3:
                        self.position = float(parts[1].strip().split()[0])
                        self.ref = float(parts[2].strip().split()[0])


                else:
                    print("Output does not match expected format.")


            except (ValueError, IndexError) as e:
                print(f"Error parsing output: {e}")  # Debugging

        return self.ref, self.position


    def handle_process_error(self):
        stderr_line = self.process.readAllStandardError().data().decode('utf-8').strip()
        if stderr_line:
            print(f"Error output: {stderr_line}")
            self.error_occurred.emit(stderr_line)
    
    def stop(self):
        print("Stopping the worker thread...")
        self._is_running = False
        if self.process and self.process.state() == QProcess.Running:
            print("Terminating process...")
            self.process.terminate()
            self.process.waitForFinished()
        self.process = None
        self.quit()
        if not self.wait(5000):
            self.terminate()
            self.wait()
        
        print("Worker thread stopped.")


    def get_reference_value(self):
        self.start_process_signal.emit("GetReference")
        while self.ref is None:
            QCoreApplication.processEvents()  # Allow the event loop to process signals
        return self.ref

    def get_position_value(self):
        self.start_process_signal.emit("GetPosition")
        while self.position is None:
            QCoreApplication.processEvents()  # Allow the event loop to process signals
        return self.position

    def validate_reference_and_position(self, ref, position, content):
        for value in content:
                if not 0 <= ref + value <= 8672:
                    self.error_occurred.emit(f"Reference point is out of range. {value}")
                    return False
        return True
    
    def move_to_reference(self, ref):
        self.start_process_signal.emit("GoToReference")
        while abs(self.position - ref) > 0.01:
            QCoreApplication.processEvents()  # Wait for the position to update
        self.update_delay_bar_signal.emit(ref)

    def start_gui(self):
        self.start_process_signal.emit("StartGUI")
        while self.ref is None or self.position is None:
            QCoreApplication.processEvents()
        print("Signal emitted. Current position:", self.position, "Current reference:", self.ref)
        self.update_delay_bar_signal.emit(self.position if self.position else 0)
        self.update_ref_signal.emit(self.ref if self.ref else 0)
        return self.ref, self.position


    @Slot(list, float, int)
    def process_content(self, delay_relative, ref, number_of_shots):
        blocks = []
        dA_inputs_avg = 0
        dA_inputs_med = 0
        pos = delay_relative
        pos -= self.last_item
        
        self.barvalue += pos
        self.start_process_signal.emit(f"MoveRelative {pos}")

        

        # Simulate measurement
        QThread.sleep(2.5)
        self.update_delay_bar_signal.emit(self.barvalue)
        block_buffer = camera(number_of_shots, self.counter)
        block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
        blocks.append(block_2d_array)

        probe_avg, probe_med, dA_avg, dA_med = self.data_processor.delta_a_block(block_2d_array)
        
        delaytime = delay_relative                                     
        # last‑shot ΔA row
        row_data_avg = dA_avg[-1]
        row_data_med = dA_med[-1]
        self.plot_row_update.emit(delaytime, row_data_avg, row_data_med) 
        self.update_dA.emit(row_data_avg, row_data_med) 

        self.update_probe.emit(probe_avg[self.teller], probe_med[self.teller])  # Emit probe data incrementally
        print("Probe data emitted:", probe_avg[self.teller], probe_med[self.teller])  # Debugging
        dA_average = np.mean(dA_avg, axis=0)
        dA_median = np.median(dA_med, axis=0)

        self.last_item = delaytime # Convert to picoseconds for display
        dA_inputs_avg = np.mean(dA_average)
        dA_inputs_med = np.mean(dA_median)

        self.measurement_data_updated.emit(delaytime, dA_inputs_avg, dA_inputs_med)
        self.teller += 1

        return blocks


if __name__ == "__main__":
    app = QApplication(sys.argv)
    worker = Measurementworker([], "Regular", 0, 0)
    worker.speed_test()
    sys.exit(app.exec())