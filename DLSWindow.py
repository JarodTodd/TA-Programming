from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import pyqtgraph as pg
from WorkerThread import *
from  Heatmap_Interface  import *
from dAwindow import *

class DLSWindow(QMainWindow):
    run_command_signal = Signal(str, str, int, int)
    delay_bar_update = Signal(float)
    switch_outlier_rejection = Signal(bool)
    deviation_threshold_changed = Signal(float)
    

    def __init__(self, dA_Window):
        super().__init__()
        self.setWindowTitle("Delayline GUI")
        self.probe_worker = ProbeThread()
        self.worker = MeasurementWorker("", "StartUp", 0, 0, 'localhost', 9999)
        self.dA_window = dA_Window
        self.worker.update_delay_bar_signal.connect(self.update_delay_bar)
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layouts
        left_layout = QVBoxLayout()

        self.shot_input = QLineEdit()
        self.shot_input.setPlaceholderText("Number of shots")
        self.shot_input.returnPressed.connect(self.shot_input_entered)
        left_layout.addWidget(self.shot_input)  

        self.probe_avg_graph = pg.PlotWidget()
        left_layout.addWidget(self.probe_avg_graph)
        self.probe_avg_graph.setTitle("Probe")
        self.probe_avg_graph.setLabel('left', 'Intensity (counts)')
        self.probe_avg_graph.setLabel('bottom', 'Pixel index')
        self.probe_avg_graph.setBackground('w')
        self.probe_avg_graph.scene().sigMouseClicked.connect(lambda event: self.dA_window.on_click(event, self.probe_avg_graph))
        self.probe_avg_graph.setLimits(xMin=0, xMax=1074, yMin=0, yMax=16500)


        self.probe_curve = self.probe_avg_graph.plot([], pen='r')

        # vertical, draggable guide-lines 
        self.range_line_left  = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen(color='#C0D5DC', width=1))
        self.labelled_line_left = pg.InfLineLabel(self.range_line_left, text="{value:.0f}", position=0.95, color='black', fill=(255, 255, 255, 180)) 
        self.range_line_right = pg.InfiniteLine(pos=1023, angle=90, movable=True, pen=pg.mkPen(color='#C0D5DC', width=1))
        self.labelled_line_right = pg.InfLineLabel(self.range_line_right, text="{value:.0f}", position=0.95, color='black', fill=(255, 255, 255, 180)) 
        font_size = QFont()
        font_size.setPointSize(7)
        self.labelled_line_right.textItem.setFont(font_size)
        self.labelled_line_left.textItem.setFont(font_size)

        # add guide-lines to probe-graph
        for line in (self.range_line_left, self.range_line_right):
            line.setVisible(False)                             
            line.sigPositionChanged.connect(self.probe_outlier_range_changed)
            self.probe_avg_graph.addItem(line)
   

        self.probe_inputs_avg = []


        # Outlier rejection layout
        outlier_group = QGroupBox()
        outlier_layout = QGridLayout()

        # Checkbox
        self.outlier_checkbox = QCheckBox("Remove bad spectra")
        self.outlier_checkbox.toggled.connect(self.toggle_outlier_rejection) 
        outlier_layout.addWidget(self.outlier_checkbox, 0, 0, 1, 3)

        # Deviation threshold input
        self.deviation_label = QLabel("Remove spectra that deviate more than")
        outlier_layout.addWidget(self.deviation_label, 1, 0, 1, 2)
        self.deviation_spinbox = QDoubleSpinBox()
        self.deviation_spinbox.valueChanged.connect(self.emit_deviation_change)
        self.deviation_spinbox.setRange(0, 100)
        self.deviation_spinbox.setSuffix(" %")
        self.deviation_spinbox.setSingleStep(0.01)
        self.deviation_spinbox.setValue(100)
        outlier_layout.addWidget(self.deviation_spinbox, 1, 2)

        self.rejected_label = QLabel("Rejected shots (%)")
        self.rejected_value = QLineEdit()
        self.rejected_value.setPlaceholderText("--")    
        self.rejected_value.setReadOnly(True)              
        outlier_layout.addWidget(self.rejected_label, 2, 0, 1, 2)
        outlier_layout.addWidget(self.rejected_value, 2, 2)

        outlier_group.setLayout(outlier_layout)
        left_layout.addWidget(outlier_group)

        outlier_group.setLayout(outlier_layout)
        left_layout.addWidget(outlier_group)
        self.toggle_outlier_rejection(False)

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
        move_neg_button.clicked.connect(lambda: self.update_delay_bar(self.delay_bar.value() - 100))  # Update delay bar on button click
        hbox.addWidget(move_neg_button)

        move_pos_button = QPushButton("Move +100ps")
        move_pos_button.clicked.connect(lambda: self.run_command_signal.emit("MovePositive", "ButtonPress", 0, 0))
        move_pos_button.clicked.connect(lambda: self.update_delay_bar(self.delay_bar.value() + 100))  # Update delay bar on button click
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

    def toggle_outlier_rejection(self, selected: bool) -> None:
        self.deviation_label.setVisible(selected)
        self.deviation_spinbox.setVisible(selected)

        self.rejected_label.setVisible(selected)
        self.rejected_value.setVisible(selected)

        self.range_line_left.setVisible(selected)
        self.range_line_right.setVisible(selected)

        if not selected:
            # Ensure the checkbox is unchecked
            self.outlier_checkbox.setChecked(False) 

        self.switch_outlier_rejection.emit(selected)

        if selected:
            # If outlier rejection is enabled, set previous settings
            self.emit_deviation_change(self.deviation_spinbox.value())
            self.probe_outlier_range_changed() 


    def emit_deviation_change(self, value: float):
        self.deviation_threshold_changed.emit(value)

    @Slot()
    def probe_outlier_range_changed(self):
        start = int(round(self.range_line_left.value()))
        end   = int(round(self.range_line_right.value()))
        if start > end:                   
            start, end = end, start
            self.range_line_left, self.range_line_right = self.range_line_right, self.range_line_left

        if start < 0:
            self.range_line_left.setValue(0)
            start = 0
        if end > 1023:
            end = 1023
            self.range_line_right.setValue(1023)

        # forward to the data-processor running in the worker thread
        if self.probe_worker and self.probe_worker.data_processor:
            self.probe_worker.data_processor.update_outlier_range(start, end)
    
    @Slot(float)
    def update_rejected_percentage(self, percent: float) -> None:
        """Fill the read-only box with the latest rejected-spectra percentage."""
        self.rejected_value.setText(f"{percent:.1f}")

    def start_probe_thread(self, shots: int = 1000):
        """Create and launch the single ProbeThread.  
        Call this exactly once from MainApp after all tabs exist."""
        if self.probe_worker is not None:
            return                  
        self.probe_worker = ProbeThread(shots)
        self.dA_window.probe_worker = self.probe_worker   # ← give dA_Window the thread

        self.switch_outlier_rejection.connect(self.probe_worker.data_processor.toggle_outlier_rejection_probe, Qt.QueuedConnection)
        self.dA_window.dA_switch_outlier_rejection.connect(self.probe_worker.data_processor.toggle_outlier_rejection_dA, Qt.QueuedConnection)
        self.deviation_threshold_changed.connect(self.probe_worker.data_processor.deviation_change, Qt.QueuedConnection)
        self.dA_window.dA_deviation_threshold_changed.connect(self.probe_worker.data_processor.dA_deviation_change, Qt.QueuedConnection)

        self.probe_worker.probe_update.connect(self.update_probe_data, Qt.QueuedConnection)
        self.probe_worker.dA_update.connect(self.update_probe_avg_graph, Qt.QueuedConnection)
        self.probe_worker.probe_rejected.connect(self.update_rejected_percentage, Qt.QueuedConnection)
        self.probe_worker.dA_rejected.connect(self.dA_window.update_rejected_percentage, Qt.QueuedConnection)
        self.probe_worker.start()

    def shot_input_entered(self):
        text = self.shot_input.text().strip()
        try:
            shots = int(text)
            if shots <= 3:
                raise ValueError
        except ValueError:
            self.show_error_message("Please enter an integer >= 4.")
            return
        self.restart_probe_thread(shots)

    def restart_probe_thread(self, shots: int):
        outlier_rejection_probe = self.outlier_checkbox.isChecked()
        outlier_rejection_dA = self.dA_window.outlier_checkbox.isChecked()
        self.stop_probe_thread(False)
        self.start_probe_thread(shots)

        if outlier_rejection_probe:
            self.toggle_outlier_rejection(True)
        if outlier_rejection_dA:
            self.dA_window.toggle_outlier_rejection(True)


    def stop_probe_thread(self, hard_stop: bool = True):
        if self.probe_worker is not None:
            # Ensure UI updates (signals) don't reach a dying thread
            self.switch_outlier_rejection.disconnect()    
            self.dA_window.dA_switch_outlier_rejection.disconnect()
            self.deviation_threshold_changed.disconnect()

            if hard_stop:
                # If thread is stopped for a measurement, disable outlier rejection
                self.toggle_outlier_rejection(False)
                self.dA_window.toggle_outlier_rejection(False)

            self.probe_worker.stop()
            self.probe_worker.wait()
            self.probe_worker = None

    def Submitted(self):
        try:
            value = float(self.delay_input.text())
            current_bar_value = self.delay_bar.value()

            if 0 <= current_bar_value + value <= 8672:
                self.run_command_signal.emit(f"MoveRelative {value}", "ButtonPress", 0, 0)
                print(f"Emitting command: MoveRelative {value}")
                self.delay_bar_update.emit(current_bar_value + value)
                self.delay_bar.setFormat(f"{int(current_bar_value + value)}/8672")
            else:
                raise ValueError("Value is out of range.")
        except ValueError as ve:
            self.show_error_message(str(ve))
        except Exception as e:
            self.show_error_message(str(e))

    

    def update_delay_bar(self, value):
        value = max(0, min(value, self.delay_bar.maximum()))
        self.delay_bar.setValue(int(value))
        self.delay_bar.setFormat(f"{int(value)}/8672")
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
    def update_probe_data(self, avg_row):
        self.probe_inputs_avg = avg_row
        self.probe_curve.setData(self.probe_inputs_avg)       

    @Slot(object, object)
    def update_probe_avg_graph(self, avg_row):
        self.window().dA_window.update_dA_graph(avg_row)


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