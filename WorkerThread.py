from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import numpy as np
from Plot_Calculations import *
from camera import *
import socket
import json
import time
import csv
import os

ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"

class ProbeThread(QThread):
    """
    QThread subclass that captures raw camera data, processes it,
    and emits signals with averaged probe and dA data as numpy arrays.
    """
    
    # Signals emitted by the thread to the DLS or dA Window:
    # - probe_update: emits averaged probe intensity array
    # - probe_rejected: emits percent of rejected probe measurements
    # - dA_update: emits averaged delta-A array
    # - dA_rejected: emits percent of rejected delta-A measurements
    probe_update = Signal(np.ndarray)
    probe_rejected = Signal(float)
    dA_update = Signal(np.ndarray)
    dA_rejected = Signal(float)
    

    def __init__(self, shots = 1000, parent: QObject | None = None):
        """
        Initialize the thread.
        shots: number of shots per acquisition block. 
        """
        super().__init__(parent)
        self.shots = shots
        self.running = True
        self.scan_complete = False
        self.wavelengths = [f'{i}' for i in range(1, 1023)]
        self.data_processor = ComputeData()
    
    def run(self):
        """Main execution loop. Continuously capture shots and process data until stopped."""
        while self.running:
            # capture raw data block from camera
            block_buffer = camera(self.shots, 0)
            block_2d_array = np.array(block_buffer).reshape(self.shots, 1088)

            # process data: compute probe and dA averages
            probe_avg, dA_average = self.data_processor.delta_a_block(block_2d_array)

            # Emit processed data and rejection stats to visualize them in the GUI
            self.probe_update.emit(probe_avg)
            self.dA_update.emit(dA_average)
            self.probe_rejected.emit(self.data_processor.rejected_probe)
            self.dA_rejected.emit(self.data_processor.rejected_dA)
    
    def stop(self):
        """
        Request the thread to stop. Safely exits the loop and waits for thread to finish.
        """
        self.running = False
        self.quit()
        self.wait()
            

class MeasurementWorker(QThread):
    measurement_data_updated = Signal(float, float)
    update_delay_bar_signal = Signal(float)
    update_ref_signal = Signal(float)
    error_occurred = Signal(str)
    update_probe = Signal(list)
    update_dA = Signal(list)
    start_process_signal = Signal(str)
    current_step_signal = Signal(int, int)
    stop_button = Signal()
    plot_row_update = Signal(float, np.ndarray, int)
    reset_currentMatrix =  Signal()

    def __init__(self, content, orientation, shots, scans, host='localhost', port=9999):
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
        self.socket_host = host
        self.socket_port = port
        self.sock = None

    def setup_socket(self, argument):
        try:
            if not hasattr(self, "server_socket") or self.server_socket.fileno() == -1:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind((self.socket_host, self.socket_port))
                self.server_socket.listen(1)
                print(f"Server is listening on {self.socket_host}:{self.socket_port}")
            time.sleep(1)  # Allow time for the server to start listening
            self.start_process_signal.emit(argument)
            print("Waiting for connection from IronPython...")
            self.conn, _ = self.server_socket.accept()
            print("Connected.")
            self.buffer = b""
        except Exception as e:
            print(f"Error in setup_socket: {e}")
            self.error_occurred.emit(str(e))



    def receive_data_from_client(self):
        try:
            print("Waiting for data from IronPython...")
            while b"\n" not in self.buffer:
                chunk = self.conn.recv(1024)  # Receive data from the client
                if not chunk:
                    print("Connection closed by client.")
                    return None  # Return None if the connection is closed
                self.buffer += chunk

            # Parse the received message
            line, self.buffer = self.buffer.split(b"\n", 1)
            data = json.loads(line.decode())
            print(f"Received data: {data}")
            self.buffer = b""
            return data  # Return the parsed data
        except Exception as e:
            print(f"Error receiving data from client: {e}")
            self.error_occurred.emit(str(e))
            return None
        

    def send_data(self, data: dict):
        if self.sock:
            message = json.dumps(data) + "\n"
            self.sock.sendall(message.encode())

    def update_command(self, content, orientation, shots, scans):
        self._orientation = orientation
        self._content = content
        self._shots = shots
        self._scans = scans

    def update_metadata(self, directory, filename, sample, solvent, pump, pump_unit, pathlength, path_unit, exc_power, power_unit, notes):
        self.directory = directory
        self.filename = filename
        self.sample = sample
        self.solvent = solvent
        self.pump = pump
        self.pump_unit = pump_unit
        self.pathlength = pathlength
        self.pathlength_unit = path_unit
        self.exc_power = exc_power
        self.exc_power_unit = power_unit
        self.notes = notes

    def wavelength_change(self, wavelengths):
        self.wavelengths = wavelengths

    @Slot(str)
    def run(self):
        print(f"This is {self._orientation}")
        self._is_running = True
        if self._orientation in ("Regular", "Backwards", "Random"):
            try:
                self._run_measurement_loop(self._content, self._shots, self._scans)
            except Exception as e:
                self.error_occurred.emit(str(e))

        if self._orientation == "ButtonPress":
            argument = self._content
            print(f"Running script with argument: {argument}")
            try:
                self.setup_socket(argument)
            except Exception as e:
                self.error_occurred.emit(str(e))
            finally:
                self.conn.close()
                self.server_socket.close()

        if self._orientation == "StartUp":
            try:
                ref, pos = self.start_gui()
                print(f"Position: {pos}, Reference: {ref}")

            except Exception as e:
                self.error_occurred.emit(str(e))
            finally:
                self.conn.close()
                self.server_socket.close()
                print("Connection closed and server socket shut down.")

    def _run_measurement_loop(self, content: list[dict], shots: int, scans) -> None:
        try:
            self.ref, self.position = self.start_gui()
            if not self.validate_reference_and_position(self.ref, content):
                return
            
            self.barvalue = self.ref
            self.update_delay_bar_signal.emit(self.ref)
            self.last_item = 0
            self.counter = 0
            self.teller = 0
            self.content = content
            self.scans = 1
            self.nos = scans
            self.averaged_probe_measurement = []
            self.measurement_average = []
            self.setup_socket(f"MeasurementLoop {content} {scans}")
            while self._is_running:
                while b"\n" not in self.buffer:
                    chunk = self.conn.recv(1024)
                    if not chunk:
                        print("Connection closed.")
                        return
                    self.buffer += chunk

                line, self.buffer = self.buffer.split(b"\n", 1)
                data = json.loads(line.decode())

                # You receive one data point here
                print(f"Received: {data}")
                result = self.process_content(data, shots)

                # Send a message back to the client socket
                response = {"status": "processed", "counter": self.counter}
                self.conn.sendall((json.dumps(response) + "\n").encode())

                self.counter += 1

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.conn.close()
            self.server_socket.close()



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

        # Notify the client to stop, if connection exists
        try:
            if hasattr(self, "conn") and self.conn is not None:
                # Check if socket is still open
                try:
                    if self.conn.fileno() != -1:
                        stop_message = {"command": "stop"}
                        self.conn.sendall((json.dumps(stop_message) + "\n").encode())
                        print("Sent stop command to client.")
                    else:
                        pass
                except OSError as e:
                    print(f"Socket error: {e}")
            else:
                print("No valid connection to send stop command.")
        except Exception as e:
            print(f"Error sending stop command to client: {e}")

        # Save current scan data if available
        if hasattr(self, "averaged_probe_measurement") and self.averaged_probe_measurement and self.scan_complete is False:
            try:
                self.save_scan_file(
                    getattr(self, "directory", ""),
                    getattr(self, "filename", ""),
                    getattr(self, "sample", ""),
                    getattr(self, "solvent", ""),
                    getattr(self, "pump", ""),
                    getattr(self, "pathlength", ""),
                    getattr(self, "exc_power", ""),
                    getattr(self, "notes", "")
                )
                print("Partial scan data saved before stopping.")
            except Exception as e:
                print(f"Error saving partial scan data: {e}")

        # Save average of all scans if more than one scan
        if hasattr(self, "measurement_average") and self.nos > 1 and self.measurement_average and self.scan_complete is False:
            try:
                self.save_avg_file(
                    getattr(self, "directory", ""),
                    getattr(self, "filename", ""),
                    getattr(self, "sample", ""),
                    getattr(self, "solvent", ""),
                    getattr(self, "pump", ""),
                    getattr(self, "pathlength", ""),
                    getattr(self, "exc_power", ""),
                    getattr(self, "notes", "")
                )
                print("Partial average scan data saved before stopping.")
            except Exception as e:
                print(f"Error saving partial average scan data: {e}")

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

    def validate_reference_and_position(self, ref, content):
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
        self.setup_socket("StartGUI")
        try:
            data = self.receive_data_from_client()
            if data is None:
                return 

            # Extract position and reference from the received data
            self.position = data.get("position", 0)
            self.ref = data.get("reference", 0)

            # Emit signals to update the GUI
            self.update_ref_signal.emit(self.ref)
            self.update_delay_bar_signal.emit(self.position)

        except Exception as e:
            print(f"Error in start_gui: {e}")
            self.error_occurred.emit(str(e)) 

        return self.ref, self.position



    def process_content(self, delay_relative, number_of_shots):
        blocks = []
        dA_inputs_avg = 0
        pos = delay_relative
        pos -= self.last_item
        if delay_relative == self.content[0]:
            self.averaged_probe_measurement = []
        self.scan_complete = False
        self.barvalue += pos

        self.update_delay_bar_signal.emit(self.barvalue)
        block_buffer = camera(number_of_shots, self.counter)
        block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
        blocks.append(block_2d_array)

        probe_avg, dA_avg = self.data_processor.delta_a_block(block_2d_array)
        self.averaged_probe_measurement.append((delay_relative, *probe_avg))
        delaytime = delay_relative                                     
        # last‑shot ΔA row
        row_data_avg = dA_avg
        self.plot_row_update.emit(delaytime, row_data_avg, self.scans) 
        self.update_dA.emit(row_data_avg) 

        self.update_probe.emit(probe_avg)  # Emit probe data incrementally
        dA_average = np.mean(dA_avg, axis=0)
        
        self.last_item = delaytime # Convert to picoseconds for display
        dA_inputs_avg = np.mean(dA_average)

        self.measurement_data_updated.emit(delaytime, dA_inputs_avg)
        self.teller += 1
        self.current_step_signal.emit(self.teller, self.scans)

        """When a scan is completed, save the data to a CSV file in the format:
        Delay, Probe_Avg (per pixel)"""
        if delay_relative == self.content[-1]:
            self.save_scan_file(self.directory, self.filename, self.sample, self.solvent, self.pump, self.pathlength, self.exc_power, self.notes)
            self.scan_complete = True
            if self.nos == self.scans and self.nos > 1:
                self.save_avg_file(self.directory, self.filename, self.sample, self.solvent, self.pump, self.pathlength, self.exc_power, self.notes)
 
            if self.scans != self.nos:
                self.reset_currentMatrix.emit() 
                
            self.scans += 1
            
        return blocks
    

    def save_scan_file(self, directory, name, sample, solvent, pump, pathlength, exc_power, notes):
        if self.nos > 1:
            filename = f"{name}_Scan_{self.scans}.csv"
        else:
            filename = f"{name}.csv"
        filepath = os.path.join(directory, filename)  # Combine directory and filename
        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            # Write metadata and measurement headers in the same row
            writer.writerow(['Sample', 'Solvent', f'Pump ({self.pump_unit})', f'Path Length ({self.pathlength_unit})', f'Excitation Power({self.exc_power_unit})', 'Notes', 'Delay (ps)'] + [f'{i}' for i in self.wavelengths])
            
            # Write metadata and the first row of measurement data in the next row
            writer.writerow([sample, solvent, pump, pathlength, exc_power, notes, self.averaged_probe_measurement[0][0]] + list(self.averaged_probe_measurement[0][1:]))
            
            # Write the remaining rows of measurement data (excluding the first row already written)
            for row in self.averaged_probe_measurement[1:]:
                writer.writerow([None, None, None, None, None, None, row[0]] + list(row[1:]))  # Convert tuple to list for concatenation
        
        print(f"Saved measurement data to {filepath}")
        self.measurement_average.append(np.array([list(row[1:]) for row in self.averaged_probe_measurement]))  # Exclude delay time for averaging

        # Make sure the stop button gets disabled after the measurement is done.
        if self.nos == 1:
            self.stop_button.emit()

    def save_avg_file(self, directory, name, sample, solvent, pump, pathlength, exc_power, notes):
        # Allow averaging even if scans have different lengths (pad with NaN)
        if not self.measurement_average:
            print("No scans to average.")
            return

        max_len = max(scan.shape[0] for scan in self.measurement_average)
        num_pixels = self.measurement_average[0].shape[1] if self.measurement_average else 0

        # Pad scans with NaN so all have the same number of delay points
        padded_scans = []
        for scan in self.measurement_average:
            if scan.shape[0] < max_len:
                pad_width = ((0, max_len - scan.shape[0]), (0, 0))
                padded = np.pad(scan, pad_width, mode='constant', constant_values=np.nan)
                padded_scans.append(padded)
            else:
                padded_scans.append(scan)
        all_scans = np.array(padded_scans)  # Shape: (scans, max_len, pixels)

        # Calculate the average for each delay across all scans, ignoring NaN
        avg_all_scans = np.round(np.nanmean(all_scans, axis=0), 4)  # Shape: (max_len, pixels)

        # Save the averaged data to a CSV file
        filename = f"{name}_Average_Probe_Entire_Measurement.csv"
        filepath = os.path.join(directory, filename)
        with open(filepath, mode='w', newline='') as file:
            writer = csv.writer(file)

            # Write metadata and measurement headers in the same row
            writer.writerow(['Sample', 'Solvent', f'Pump ({self.pump_unit})', f'Path Length ({self.pathlength_unit})', f'Excitation Power({self.exc_power_unit})', 'Notes', 'Delay (ps)'] + [f'{i}' for i in self.wavelengths])

            # Write metadata and the first row of measurement data in the next row
            delay = self.content[0] if len(self.content) > 0 else None
            writer.writerow([sample, solvent, pump, pathlength, exc_power, notes, delay] + avg_all_scans[0].tolist())

            # Write the averaged data for each delay (excluding the first row already written)
            for i, row in enumerate(avg_all_scans[1:], start=1):
                delay = self.content[i] if i < len(self.content) else None
                writer.writerow([None, None, None, None, None, None, delay] + row.tolist())
        self.stop_button.emit()
        self.averaged_probe_measurement = []
        self.measurement_average = []
        print(f"Saved averaged measurement data to {filepath}")
