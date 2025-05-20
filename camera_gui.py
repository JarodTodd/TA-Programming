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
from dAwindow import *


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
        self.worker.update_delay_bar_signal.connect(self.update_progress_bar, Qt.QueuedConnection)
        

    def setup_ui(self):
        self.t_0 = 0
        self.layout = QVBoxLayout()
        print("Setting up UI")
        # Main layout as a grid
        self.grid_layout = QGridLayout()

        # Bottom-righ quarter layout
        top_left_layout = QVBoxLayout()
        top_right_layout = QVBoxLayout()
        bottom_left_layout = QVBoxLayout()
        

        # TAPlotWidget 
        delay_times   = np.array([0.0, 0.2, 0.5, 1.0])
        pixel_indices = np.arange(1074)
        self.ta_widgets = TAPlotWidget(delay_times, pixel_indices) 
        self.ta_widgets.canvas_heatmap.setBackground('w')
        self.ta_widgets.canvas_plot1.setBackground('w')
        self.ta_widgets.canvas_plot2.setBackground('w')

        # Add plots to the layout
        top_left_layout.addWidget(self.ta_widgets.canvas_heatmap)
        top_right_layout.addWidget(self.ta_widgets.canvas_plot1)
        bottom_left_layout.addWidget(self.ta_widgets.canvas_plot2)
        self.delaytimes = []
        self.dA_inputs_avg = []
        self.dA_inputs_med = []


        self.dA_Combobox = QComboBox()
        self.dA_Combobox.addItems(["Average", "Median"])
        self.dA_Combobox.setCurrentText("Average")
        self.dA_Combobox.currentIndexChanged.connect(self.avg_med_toggle)
        top_left_layout.addWidget(self.dA_Combobox)
        self.dA_Combobox.currentTextChanged.connect(lambda txt: self.ta_widgets.set_mode("avg" if txt == "Average" else "med"))
        # if self.dA_Combobox.currentText() == "Average":
        #     self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_avg, symbol='o', pen=None)
        # elif self.dA_Combobox.currentText() == "Median":
        #     self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_med, symbol='o', pen=None)

        # Simplified setup for bottom-right layout and widgets
        bottom_right_layout = QVBoxLayout()

        # Form layout for shots input
        self.form_layout = QFormLayout()
        self.shots_input = QLineEdit(placeholderText="Enter number of shots")
        self.form_layout.addRow("Number of Shots:", self.shots_input)

        # Status label
        self.status_label = QLabel("", alignment=Qt.AlignCenter)

        # Add widgets to bottom-right layout
        bottom_right_layout.addLayout(self.form_layout)
        bottom_right_layout.addWidget(self.status_label)
        self.bottomright_widget = QWidget()
        self.bottomright = Ui_Bottom_right()
        self.bottomright.setupUi(self.bottomright_widget)
        bottom_right_layout.addWidget(self.bottomright_widget)

        self.grid_layout.addItem(top_left_layout, 0, 0)
        self.grid_layout.addItem(top_right_layout, 0, 1)
        self.grid_layout.addItem(bottom_left_layout, 1, 0)
        self.grid_layout.addWidget(self.bottomright_widget, 1, 1)

        self.setLayout(self.grid_layout)

    def update_progress_bar(self, value):
        """Update the local progress bar with the value from DLSWindow."""
        print("Updating progress bar with value:", value)
        self.bottomright.current_delay.setText(f"{round(value, 2)}")
        self.dAwindow.verticalSlider.setValue(round(value*1000, 2))

    def update_t0(self, t_0):
        """Update the t_0 value."""
        print(f"Updating t_0 in UI: {t_0}")  # Debugging
        self.t_0 = round(t_0,2)
        self.bottomright.t0_line.setText(f"{t_0}")
        self.dAwindow.t_0 = self.t_0
        self.dAwindow.t0_spinbox.setValue(self.t_0)



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

        # Clear the graph and re-plot with new data

    def avg_med_toggle(self):
        """Toggle between average and median."""

        if self.dA_Combobox.currentText() == "Average":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_avg, symbol='o')
        elif self.dA_Combobox.currentText() == "Median":
            self.dA_avg_graph.clear()
            self.dA_avg_graph.plot(self.delaytimes, self.dA_inputs_med, symbol='o')

class DLSWindow(QMainWindow):
    progress_updated = Signal(int)
    run_command_signal = Signal(str, str, int, int)

    

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delayline GUI")

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


        self.probe_combobox = QComboBox()
        self.probe_combobox.addItems(["Average", "Median"])
        self.probe_combobox.setCurrentText("Average")
        left_layout.addWidget(self.probe_combobox)
        self.probe_combobox.currentIndexChanged.connect(self.redraw_probe_plot)


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
        self.delay_input.setPlaceholderText("Enter delay time")
        self.delay_input.setValidator(QDoubleValidator(-8672666.0, 8672666.0, 20, self))
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

    def start_probe_thread(self, shots = 10):
        self.probe_worker = ProbeThread(shots)
        self.probe_worker.probe_update.connect(self.update_probe_data, Qt.QueuedConnection)
        
       
        self.probe_worker.start()

    def stop_probe_thread(self):
        self.probe_worker.stop()
        self.probe_worker.wait()

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
            print(current_bar_value)
            print(current_bar_value - value)
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
                self.run_command_signal.emit(f"MoveRelative {value_ns}", "ButtonPress", 0, 0)
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

    
    @Slot(object, object)                          
    def update_probe_data(self, avg_row, med_row):
        self.probe_inputs_avg = avg_row
        self.probe_inputs_med = med_row
        self.redraw_probe_plot()             

    @Slot(int)
    def redraw_probe_plot(self, *_):
        self.probe_avg_graph.clear()
        if self.probe_combobox.currentText() == "Average":
            if self.probe_inputs_avg.size:
                self.probe_avg_graph.plot(self.probe_inputs_avg, pen='r')
        else:
            if self.probe_inputs_med.size:
                self.probe_avg_graph.plot(self.probe_inputs_med, pen='b')

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
