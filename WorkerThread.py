from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sys
import numpy as np
from main import *
from camera import *
import random
import time

ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"



class Measurementworker(QThread):
    measurement_data_updated = Signal(float, float, float)
    update_delay_bar_signal = Signal(float)
    update_ref_signal = Signal(float)
    error_occurred = Signal(str)
    update_probe = Signal(list, list)
    process_content_signal = Signal(list, float, int)
    task_done_signal = Signal()
    start_process_signal = Signal(str)
    orientation_signal = Signal(str)

    parsed_content_signal = Signal(list)
    plot_row_update = Signal(int, np.ndarray, np.ndarray)

    def __init__(self, content, orientation, shots):
        super().__init__()
        self._is_running = True
        self.process = None
        self._content = content
        self._orientation: str = orientation
        self._shots: int = shots
        self.ref = None
        self.position = None
        self.data_processor = ComputeData()
        

    @Slot(str, str, int)
    def start_measurement(self, content: str, orientation: str, shots: int) -> None:
        """
        Called from the GUI thread.  Stores parameters and kicks off self.run().
        """

        self._content = content
        self._orientation = orientation
        self._shots = shots
        self.start()

    def update_command(self, content, orientation, shots):
        self._orientation = orientation
        self._content = content
        self._shots = shots

    @Slot(str)
    def run(self):

        if self._orientation == "forward" or self._orientation == "backward" or self._orientation == "random":
            try:
                print(f"Running script with content: {self._content}")
                self._run_measurement_loop(self._content, self._shots)  # Call the measurement loop
            
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
                self.task_done_signal.emit()

            except Exception as e:
                self.error_occurred.emit(str(e))
        
    def _run_measurement_loop(self, content: list[dict], shots: int) -> None:
        """
        Example loop that calls your existing RunMeasurement() and streams data.
        Modify freely to match your real-world needs.
        """
        print("Starting measurement loop...")
        self.counter = 0
        self.teller = 0
        self.last_item = 0
        ref, position = self.start_gui()
        print(f"Position: {position}, Reference: {ref}")
        if not self.validate_reference_and_position(ref, position, content):
            return

        if round(ref, 3) != round(position, 3):
            self.move_to_reference(ref)

        for item in content:
            print(item)
            if self.isInterruptionRequested():  # allow user to abort
                break

            result = self.process_content(item, ref, shots)
            self.counter += 1  # hardware I/O – heavy stuff
            

        # Clean-up
        self.process.close()


    @Slot(str)
    def run_script(self, argument):
        print(f"Running script with argument: {argument}")
        try:
            if self.process.state() == QProcess.Running:
                self.process.waitForFinished()  # Wait for the current process to finish

            self.process.start(ironpython_executable, [script_path, argument])
            print(f"Command: {ironpython_executable} {script_path} {argument}")
        except Exception as e:
            self.error_occurred.emit(str(e))

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

        delay_values = []
        for item in parsed_content:
            value = item[1]
            unit = item[0].lower()
            if unit in ['ns', 'nanosecond', 'nanoseconds']:            
                value = value * 1000                             
            elif unit in ['ps', 'picosecond', 'picoseconds']:           
                value = value                                     
            else:                                                       
                value = value / 1000 
            delay_values.append(value)
        self.parsed_content_signal.emit(delay_values)

        #Signal
        return parsed_content
    
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
        self.start_process_signal.emit("GoToReference")
        while abs(self.position - ref) > 0.01:
            QCoreApplication.processEvents()  # Wait for the position to update
        self.update_delay_bar_signal.emit(ref * 1000)

    def start_gui(self):

        self.start_process_signal.emit("StartGUI")
        while self.position is None:
            QCoreApplication.processEvents()
        print("Emitting position and reference")
        self.update_delay_bar_signal.emit(self.position * 1000)
        self.update_ref_signal.emit(self.ref * 1000)
        return self.ref, self.position


    @Slot(list, float, int)
    def process_content(self, blk, ref, number_of_shots):
        blocks = []
        delaytime = 0
        dA_inputs_avg = 0
        dA_inputs_med = 0
        unit = blk[0].lower()
        pos = blk[1]

        if unit in ['ps', 'picosecond', 'picoseconds']:
            pos /= 1000
        elif unit in ['fs', 'femtosecond', 'femtoseconds']:
            pos /= 1000000

        pos -= self.last_item
        self.barvalue += pos * 1000
        print(self.barvalue, pos, self.last_item)
        self.start_process_signal.emit(f"MoveRelative {pos}")
        

        # Simulate measurement

        self.update_delay_bar_signal.emit(self.barvalue)
        print("a")
        block_buffer = camera(number_of_shots, self.counter)
        print("b")
        block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
        blocks.append(block_2d_array)

        if unit in ['ns', 'nanosecond', 'nanoseconds']:
            self.last_item = blk[1]
        elif unit in ['ps', 'picosecond', 'picoseconds']:
            self.last_item = blk[1] / 1000
        elif unit in ['fs', 'femtosecond', 'femtoseconds']:
            self.last_item = blk[1] / 1000000

        probe_avg, probe_med, dA_avg, dA_med = self.data_processor.delta_a_block(block_2d_array)
        
        # compute the delay in picoseconds that belongs to this block
        if unit in ['ns', 'nanosecond', 'nanoseconds']:            
            delaytime = blk[1] * 1000                             
        elif unit in ['ps', 'picosecond', 'picoseconds']:           
            delaytime = blk[1]                                     
        else:                                                       
            delaytime = blk[1] / 1000 

        # last‑shot ΔA row
        row_data_avg = dA_avg[-1]
        row_data_med = dA_med[-1]
        self.plot_row_update.emit(delaytime, row_data_avg, row_data_med)  

        self.update_probe.emit(probe_avg[self.teller], probe_med[self.teller])  # Emit probe data incrementally
        print("Probe data emitted:", probe_avg[self.teller], probe_med[self.teller])  # Debugging
        dA_average = np.mean(dA_avg, axis=0)
        dA_median = np.median(dA_med, axis=0)

        delaytime = self.last_item *1000 # Convert to picoseconds for display
        dA_inputs_avg = np.mean(dA_average)
        dA_inputs_med = np.mean(dA_median)

        self.measurement_data_updated.emit(delaytime, dA_inputs_avg, dA_inputs_med)
        self.teller += 1

        return blocks


if __name__ == "__main__":
    app = QApplication(sys.argv)
    sys.exit(app.exec())