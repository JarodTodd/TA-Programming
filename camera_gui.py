from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import pyqtgraph as pg
from WorkerThread import *
from Bottomright import *
from dAwindow import *
import numpy as np                      
from cursor_plot import TAPlotWidget
from pyqtgraph.exporters import ImageExporter
from PySide6 import QtCore


class ShotDelayApp(QWidget):


    def __init__(self, dls_window):
        super().__init__()
        self.setWindowTitle("Camera Interface")
        self.DLSWindow = dls_window
        self.worker = Measurementworker("", "", 0, 0)
        self.bottomright = Ui_Bottom_right()
        self.dAwindow = dA_Window()
        self.setup_ui()
        self.worker.update_ref_signal.connect(self.update_t0, Qt.QueuedConnection)
        self.worker.update_delay_bar_signal.connect(self.update_current_delay, Qt.QueuedConnection)
        

    def setup_ui(self):
        self.t_0 = 0
        self.layout = QVBoxLayout()
        print("Setting up UI")
        # Main layout as a grid
        self.grid_layout = QGridLayout()

        # TAPlotWidget 
        delay_times   = np.array([0.0, 0.2, 0.5, 1.0])
        pixel_indices = np.arange(1074)
        self.ta_widgets = TAPlotWidget(delay_times, pixel_indices) 
        self.ta_widgets.canvas_heatmap.setBackground('w')
        self.ta_widgets.canvas_plot1.setBackground('w')
        self.ta_widgets.canvas_plot2.setBackground('w')

        self.delaytimes = []
        self.dA_inputs_avg = []
        self.dA_inputs_med = []

        # Adding interaction elements to GUI
        bottom_right_layout = QVBoxLayout()
        # bottom_right_layout.addLayout(self.form_layout)
        # bottom_right_layout.addWidget(self.status_label)
        self.bottomright_widget = QWidget()
        self.bottomright = Ui_Bottom_right()
        self.bottomright.setupUi(self.bottomright_widget)
        bottom_right_layout.addWidget(self.bottomright_widget)

        # Putting GUI elements in correct spaces
        self.grid_layout.addWidget(self.ta_widgets.canvas_heatmap, 0, 0)
        self.grid_layout.addWidget(self.ta_widgets.canvas_plot1, 0, 1)
        self.grid_layout.addWidget(self.ta_widgets.canvas_plot2, 1, 0)
        self.grid_layout.addWidget(self.bottomright_widget, 1, 1)

        self.setLayout(self.grid_layout)

    def update_current_delay(self, value):
        """Update the current delay values."""
        value = round(value, 2)
        print("Updating progress bar with value:", value)
        self.bottomright.current_delay.setText(f"{value}")
        self.dAwindow.verticalSlider.setValue(value*1000)
        self.dAwindow.abs_pos_line.setText(f"{value}")

    def update_t0(self, t_0):
        """Update the t_0 value."""
        print(f"Updating t_0 in UI: {t_0}")  # Debugging
        self.t_0 = round(t_0,2)
        self.bottomright.t0_line.setText(f"{t_0}")
        self.dAwindow.t_0 = self.t_0
        self.dAwindow.t0_spinbox.setValue(self.t_0)
        self.dA.window.verticalSlider.setValue(t_0*1000)
        self.dAwindow.abs_pos_line.setText(f"{t_0}")
        self.dAwindow.rel_pos_line.setText(f"{0}")



    def show_error_message(self, error_message):
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Error")
        msgbox.setText("An error occurred:")
        msgbox.setInformativeText(error_message)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec()




    @Slot(float, float, float)
    def update_graph(self, delaytimes, dA_inputs_avg, dA_inputs_med):
        """Update the graph with new delaytimes and dA_inputs."""
        self.delaytimes.append(delaytimes)
        self.dA_inputs_avg.append(dA_inputs_avg)
        self.dA_inputs_med.append(dA_inputs_med)


class DLSWindow(QMainWindow):
    progress_updated = Signal(int)
    run_command_signal = Signal(str, str, int, int)

    

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delayline GUI")
        self.probe_worker = ProbeThread()
        self.worker = Measurementworker("", "", 0, 0)
        self.worker.update_delay_bar_signal.connect(self.update_delay_bar)
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layouts
        left_layout = QVBoxLayout()
        self.probe_avg_graph = pg.PlotWidget()
        left_layout.addWidget(self.probe_avg_graph)
        self.probe_avg_graph.setTitle("Probe")
        self.probe_avg_graph.setLabel('left', 'Intensity (counts)')
        self.probe_avg_graph.setLabel('bottom', 'Wavelength (nm)')
        self.probe_avg_graph.setBackground('w')

        self.probe_inputs_avg = []
        self.probe_inputs_med = []

        self.start_probe_thread()

        self.save_probe_button = QPushButton("Save Probe Data")
        self.save_probe_button.clicked.connect(lambda: self.save_probe_data())
        left_layout.addWidget(self.save_probe_button)

        right_layout = QVBoxLayout()

        hbox = QHBoxLayout()

        initialize_button = QPushButton("Initialize")
        initialize_button.clicked.connect(lambda: self.run_command_signal.emit("Initialize", "ButtonPress", 0, 0))
        hbox.addWidget(initialize_button)

        disable_button = QPushButton("Disable/Ready")
        disable_button.clicked.connect(lambda: self.run_command_signal.emit("Disable", "ButtonPress", 0, 0))
        hbox.addWidget(disable_button)

        move_neg_button = QPushButton("Move -100ps")
        move_neg_button.clicked.connect(lambda: self.run_command_signal.emit("MoveNegative", "ButtonPress", 0, 0))
        hbox.addWidget(move_neg_button)

        move_pos_button = QPushButton("Move +100ps")
        move_pos_button.clicked.connect(lambda: self.run_command_signal.emit("MovePositive", "ButtonPress", 0, 0))
        hbox.addWidget(move_pos_button)

        right_layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        self.delay_input = QLineEdit()
        self.delay_input.setPlaceholderText("Enter delay time, ps")
        self.delay_input.setValidator(QDoubleValidator(-8672.666, 8672.666, 20, self))
        self.delay_input.validator().setLocale(QLocale(QLocale.C))
        self.delay_input.returnPressed.connect(self.Submitted)

        hbox2.addWidget(self.delay_input)

        hbox3 = QHBoxLayout()

        self.delay_label = QLabel("Delay (ps):", self)
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

        self.probe_worker: ProbeThread | None = None

    def start_probe_thread(self, shots: int = 10):
        """Create and launch the single ProbeThread.  
        Call this exactly once from MainApp after all tabs exist."""
        if self.probe_worker is not None:
            return                              # already running
        self.probe_worker = ProbeThread(shots)
        self.probe_worker.probe_update.connect(self.update_probe_data, Qt.QueuedConnection)
        self.probe_worker.dA_update.connect(self.update_dA_plot, Qt.QueuedConnection)
        self.probe_worker.start()

    def stop_probe_thread(self):
        if self.probe_worker is not None:
            self.probe_worker.stop()
            self.probe_worker.wait()
            self.probe_worker = None

    def Submitted(self):
        try:
            value = float(self.delay_input.text())
            current_bar_value = self.delay_bar.value()  # In ps

            if 0 <= current_bar_value + value <= 8672:
                self.run_command_signal.emit(f"MoveRelative {value}", "ButtonPress", 0, 0)
                print(f"Emitting command: MoveRelative {value}")

            else:
                raise ValueError("Value is out of range.")
        except ValueError as ve:
            self.show_error_message(str(ve))
        except Exception as e:
            self.show_error_message(str(e))



    def update_delay_bar(self, value):
        value = max(0, min(value, self.delay_bar.maximum()))  # Keep in picoseconds
        self.delay_bar.setValue(round(value/1000))
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

    
    @Slot(object, object)                          
    def update_probe_data(self, avg_row, med_row):
        self.probe_inputs_avg = avg_row
        self.probe_inputs_med = med_row
        self.probe_avg_graph.plot(self.probe_inputs_avg, pen='r')           

    @Slot(object, object)
    def update_dA_plot(self, avg_row, med_row):
        self.window().dA_window.update_dA_graph(avg_row, med_row)


    def save_probe_data(self):
        try:
            # Open a file dialog to choose the save location and filename
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Probe Data",
                "",
                "CSV files (*.csv);;All Files (*)"
            )

            # If the user cancels the dialog, filename will be an empty string
            if not filename:
                print("Save operation cancelled.")
                return

            # Save the probe data to CSV
            import csv
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Write header
                writer.writerow(["Index", "Average", "Median"])
                # Write data rows
                for i, (avg, med) in enumerate(zip(self.probe_inputs_avg, self.probe_inputs_med)):
                    writer.writerow([i, avg, med])

            print(f"Probe data saved successfully to {filename}.")

        except Exception as e:
            self.show_error_message(f"Failed to save probe data: {e}")


    def SetReference(self):
        self.run_command_signal.emit("SetReference", "ButtonPress", 0, 0)

    def GoToReference(self):
        self.run_command_signal.emit("GoToReference", "ButtonPress", 0, 0)
    

    def closeEvent(self, event):
        self.worker_thread.stop()  # Stop the worker thread
        self.worker_thread.wait()  # Ensure the thread has finished
        event.accept()  # Accept the close event
