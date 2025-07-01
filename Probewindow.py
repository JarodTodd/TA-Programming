from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import pyqtgraph as pg
from WorkerThread import *
from dAwindow import *
import csv
from heatmap import ScaledAxis, HoverPlotWidget
from error_popup import *

class Probewindow(QMainWindow):
    """
    Main application window for Delay-Line Scan (DLS) control and live probe plotting.

    1. Initialize and layout all UI controls (buttons, delay slider, probe settings).
    2. Start and manage the worker thread that streams probe data.
    3. Route user actions (e.g. “Set Reference”) via run_command_signal.
    4. Handle incoming data and update the real-time plot.
    5. Clean up threads on close.
    """

    run_command_signal = Signal(str, str, int, int)
    run_command_signal = Signal(str, str, int, int)
    delay_bar_update = Signal(float)

    #Probe-related signals:
    # - switch_outlier_rejection: toggle outlier rejection on\off
    # - deviation_threshold_changed: change deviation threshold from spinbox
    switch_outlier_rejection = Signal(bool)
    deviation_threshold_changed = Signal(float)
    

    def __init__(self, dA_Window):
        """
        Qt constructor — build UI, wire signals and launch the GraphThread.
        """
        super().__init__()
        self.setWindowTitle("Delayline GUI")
        self.graph_worker = GraphThread()
        self.dA_window = dA_Window
        self.dark_noise = None

        # Build GUI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)


        #==== LEFT COLUMN: Local shots, Probe plot & outlier rejection =====#
        left_layout = QVBoxLayout()

        # input box: local shots for probe & dA windows
        self.shot_input = QLineEdit()
        self.shot_input.setPlaceholderText("Number of shots")
        self.shot_input.returnPressed.connect(self.shot_input_entered)
        left_layout.addWidget(self.shot_input)  

        # create probe plot
        self.probe_graph = HoverPlotWidget(self)
        left_layout.addWidget(self.probe_graph)
        self.probe_graph.setTitle("Probe")
        self.probe_graph.setLabel('left', 'Intensity (counts)')
        self.probe_graph.setLabel('bottom', 'Pixel index')
        self.probe_graph.setBackground('w')
        self.probe_graph.scene().sigMouseClicked.connect(lambda event: self.dA_window.on_click(event, self.probe_graph))
        self.probe_graph.setLimits(xMin=0, xMax=1074, yMin=0, yMax=16500)
        self.probe_curve = self.probe_graph.plot([], pen='r')

        # hoverbox settings probe plot
        self.probe_graph._checkbox1.setText("pump-off")
        self.probe_graph._checkbox2.setText("pump-off + pump-on")
        self.probe_graph._checkbox1.toggled.connect(self._on_checkbox1_toggled)
        self.probe_graph._checkbox2.toggled.connect(self._on_checkbox2_toggled)
        self.probe_graph._checkbox1.setChecked(True)

        # wavelength calibration probe plot
        self.probe_wavelength_axis = ScaledAxis(orientation='bottom')
        self.probe_graph.setAxisItems({'bottom': self.probe_wavelength_axis}) 

        # vertical, draggable guide-lines that define the outlier rejection range
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
            self.probe_graph.addItem(line)
   
        # saves current probe data for save option
        self.probe_inputs = []

        # Outlier rejection controls
        outlier_group = QGroupBox()
        outlier_layout = QGridLayout()
        # checkbox for toggle on/off
        self.outlier_checkbox = QCheckBox("Remove bad spectra")
        self.outlier_checkbox.toggled.connect(self.toggle_outlier_rejection) 
        outlier_layout.addWidget(self.outlier_checkbox, 0, 0, 1, 3)
        # deviation threshold input
        self.deviation_label = QLabel("Remove spectra that deviate more than")
        outlier_layout.addWidget(self.deviation_label, 1, 0, 1, 2)
        self.deviation_spinbox = QDoubleSpinBox()
        self.deviation_spinbox.valueChanged.connect(self.emit_deviation_change)
        self.deviation_spinbox.setRange(0, 100)
        self.deviation_spinbox.setSuffix(" %")
        self.deviation_spinbox.setSingleStep(0.01)
        self.deviation_spinbox.setValue(100)
        outlier_layout.addWidget(self.deviation_spinbox, 1, 2)
        # box that displays the percentage of rejected shots
        self.rejected_label = QLabel("Rejected shots (%)")
        self.rejected_value = QLineEdit()
        self.rejected_value.setPlaceholderText("--")    
        self.rejected_value.setReadOnly(True)              
        outlier_layout.addWidget(self.rejected_label, 2, 0, 1, 2)
        outlier_layout.addWidget(self.rejected_value, 2, 2)

        # add widgets
        outlier_group.setLayout(outlier_layout)
        left_layout.addWidget(outlier_group)
       
        # initially disable outlier rejection
        self.toggle_outlier_rejection(False)
        
        # start probe thread 
        self.start_graph_thread()

        # Button to save current probe average to CSV
        self.save_probe_button = QPushButton("Save Probe Data")
        self.save_probe_button.clicked.connect(lambda: self.save_probe_data())
        left_layout.addWidget(self.save_probe_button)

        # Button to correct for dark noise
        self.dark_noise_button = QPushButton("Correct dark noise")
        self.dark_noise_button.clicked.connect(lambda: self.correct_dark_noise())
        left_layout.addWidget(self.dark_noise_button)

        # ==== RIGHT COLUMN : Delay‑line control
        right_layout = QVBoxLayout()

        # Row 1
        hbox = QHBoxLayout()
        initialize_button = QPushButton("Initialize")
        initialize_button.setToolTip("To get the delay stage into the ready state; you might have to press this button twice, 10 seconds apart. Check Controller for light.")
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

        # Row 2
        hbox2 = QHBoxLayout()
        self.delay_input = QLineEdit()
        self.delay_input.setPlaceholderText("Enter delay time, ps")
        self.delay_input.setValidator(QDoubleValidator(-8672.666, 8672.666, 20, self))
        self.delay_input.validator().setLocale(QLocale(QLocale.C))
        self.delay_input.returnPressed.connect(self.Submitted)

        hbox2.addWidget(self.delay_input)
        right_layout.addLayout(hbox2)

        # Row 3
        hbox3 = QHBoxLayout()
        self.delay_label = QLabel("Delay (ps):", self)
        hbox3.addWidget(self.delay_label)
        self.delay_bar = MarkedProgressBar()
        self.delay_bar.setMinimum(0)
        self.delay_bar.setMaximum(8672.66)  # max picoseconds delay
        self.delay_bar.setValue(0)
        self.delay_bar.setFormat(f"/8672.66")

        hbox3.addWidget(self.delay_bar)
        right_layout.addLayout(hbox3)

        # Row 4
        hbox4 = QHBoxLayout()
        setref_button = QPushButton("Set Reference")
        setref_button.clicked.connect(self.SetReference)
        hbox4.addWidget(setref_button)

        gotoref_button = QPushButton("Go to Reference")
        gotoref_button.clicked.connect(self.GoToReference)

        hbox4.addWidget(gotoref_button)
        right_layout.addLayout(hbox4)

        # combine columns 
        central_layout = QHBoxLayout()
        central_layout.addLayout(left_layout)
        central_layout.addLayout(right_layout)
        central_widget.setLayout(central_layout)

        # placeholder: worker thread will be created in start_probe_thread()
        self.graph_worker: GraphThread | None = None


    """
    Helper functions: Probe plot
    """

    def shot_input_entered(self):
        """
        Triggered when the user presses Enter in the shot input field.
        Parses and validates the number of shots to average, and restarts
        the probe thread with the new value.
        """

        text = self.shot_input.text().strip()
        try:
            shots = int(text)
            if shots <= 3:
                raise ValueError
        except ValueError:
            show_error_message("Please enter an integer >= 4.")
            return
        self.restart_graph_thread(shots)

    @Slot(object, object)                          
    def update_probe_data(self, avg_row):
        """
        Updates the local veriable probe_input_avg with the latest probe spectrum for export
        and updates the probe plot with the current data
        """
        self.probe_inputs = avg_row
        self.probe_curve.setData(self.probe_inputs)       

    @Slot(object, object)
    def update_dA_graph(self, avg_row):
        """
        Calls the update_dA_graph function in dAWindow to update the dA graph with the latest values
        """
        self.window().dA_window.update_dA_graph(avg_row)

    def save_probe_data(self):
        """
        Saves the currently displayed probe spectrum as a CSV file.
        """
        
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

            # Write the current probe data to the selected file
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Index", "Average"])
                for i, (avg) in enumerate(zip(self.probe_inputs)):
                    writer.writerow([i, avg])

            print(f"Probe data saved successfully to {filename}.")

        except Exception as e:
            show_error_message(f"Failed to save probe data: {e}")

    def correct_dark_noise(self):
        if self.graph_worker.data_processor.dark_noise_correction is None:
            self.dark_noise = self.probe_inputs
            self.graph_worker.data_processor.dark_noise_correction = self.dark_noise
            self.dark_noise_button.setText("Remove dark noise correction")
        else:
            self.dark_noise = None
            self.graph_worker.data_processor.dark_noise_correction = self.dark_noise
            self.dark_noise_button.setText("Correct dark noise")

    # function for checkbox toggle in probe plot
    def _on_checkbox1_toggled(self, checked):
        if checked == False:
            self.probe_graph._checkbox2.setChecked(True)
        if checked:
            self.probe_graph._checkbox2.setChecked(False)
            self.graph_worker.data_processor.probe_toggle = "pump-off"
            print(self.graph_worker.data_processor.probe_toggle)


    def _on_checkbox2_toggled(self, checked):
        if checked == False:
            self.probe_graph._checkbox1.setChecked(True)
        if checked:
            self.probe_graph._checkbox1.setChecked(False)
            self.graph_worker.data_processor.probe_toggle = "pump-off+pump-on"
            print(self.graph_worker.data_processor.probe_toggle)

    """
    Helper functions: outlier rejection
    """

    def toggle_outlier_rejection(self, selected: bool) -> None:
        """
        Toggles the outlier rejection on/off
        """

        # show/hide threshold and output fields
        self.deviation_label.setVisible(selected)
        self.deviation_spinbox.setVisible(selected)

        # show/hide vertical lines that define the pixel range
        self.rejected_label.setVisible(selected)
        self.rejected_value.setVisible(selected)

        self.range_line_left.setVisible(selected)
        self.range_line_right.setVisible(selected)

        if not selected:
            # Ensure the checkbox is unchecked
            self.outlier_checkbox.setChecked(False) 

        # Notify the worker thread to enable or disable outlier rejection
        self.switch_outlier_rejection.emit(selected)

        if selected:
            # If outlier rejection is enabled, set previous settings
            self.emit_deviation_change(self.deviation_spinbox.value())
            self.probe_outlier_range_changed() 

    def emit_deviation_change(self, value: float):
        """
        This method is called when the user adjusts the spinbox controlling
        the outlier rejection threshold.
        """
        self.deviation_threshold_changed.emit(value)

    @Slot()
    def probe_outlier_range_changed(self):
        """
        This method is called when the user adjusts the outlier range on the probe plot
        """

        # Get current positions of the left and right vertical lines
        start = int(round(self.range_line_left.value()))
        end   = int(round(self.range_line_right.value()))

        # keep range sorted
        if start > end:                   
            start, end = end, start
            self.range_line_left, self.range_line_right = self.range_line_right, self.range_line_left

        # divine range limits
        if start < 0:
            self.range_line_left.setValue(0)
            start = 0
        if end > 1023:
            end = 1023
            self.range_line_right.setValue(1023)

        # forward to the data-processor running in the worker thread
        if self.graph_worker and self.graph_worker.data_processor:
            self.graph_worker.data_processor.update_outlier_range(start, end)
    
    @Slot(float)
    def update_rejected_percentage(self, percent: float) -> None:
        """Fill the read-only box with the latest rejected-spectra percentage."""
        self.rejected_value.setText(f"{percent:.1f}")


    """Helper functions: GraphThread"""

    def start_graph_thread(self, shots: int = 1000):
        """Create and launch the single GraphThread.  
        Call this exactly once from MainApp after all tabs exist
        """

        # avoid creating multiple threads — only start if one doesn't exist
        if self.graph_worker is not None:
            return

        # create a new worker thread for probe data acquisition                  
        self.graph_worker = GraphThread(shots)
        # share this thread instance with the dA window (allows dA plot to update)
        self.dA_window.probe_worker = self.graph_worker 

        #set dark noise. shape: None / List
        self.graph_worker.data_processor.dark_noise_correction = self.dark_noise  

        # Signal Wiring:
        # GUI → Worker: user enables/disables outlier rejection for probe/dA
        self.switch_outlier_rejection.connect(self.graph_worker.data_processor.toggle_outlier_rejection_probe, Qt.QueuedConnection)
        self.dA_window.dA_switch_outlier_rejection.connect(self.graph_worker.data_processor.toggle_outlier_rejection_dA, Qt.QueuedConnection)
        # GUI → Worker: threshold value changes
        self.deviation_threshold_changed.connect(self.graph_worker.data_processor.deviation_change, Qt.QueuedConnection)
        self.dA_window.dA_deviation_threshold_changed.connect(self.graph_worker.data_processor.dA_deviation_change, Qt.QueuedConnection)
         # Worker → GUI: send updated probe or dA data to UI
        self.graph_worker.probe_update.connect(self.update_probe_data, Qt.QueuedConnection)
        self.graph_worker.dA_update.connect(self.update_dA_graph, Qt.QueuedConnection)
        # Worker → GUI: update how many shots were rejected by outlier logic
        self.graph_worker.probe_rejected.connect(self.update_rejected_percentage, Qt.QueuedConnection)
        self.graph_worker.dA_rejected.connect(self.dA_window.update_rejected_percentage, Qt.QueuedConnection)
        
        # Start the thread
        self.graph_worker.start()

    def restart_graph_thread(self, shots: int):
        """
        Restart the GraphThread with a new shot value.
        """

        # save current state of outlier rejection checkboxes before stopping thread
        outlier_rejection_probe = self.outlier_checkbox.isChecked()
        outlier_rejection_dA = self.dA_window.outlier_checkbox.isChecked()

        # stop the existing thread, but keep the outlier rejection enabled after restart
        self.stop_graph_thread(False)

        # start thread
        self.start_graph_thread(shots)

         # restore the outlier rejection states
        if outlier_rejection_probe:
            self.toggle_outlier_rejection(True)
        if outlier_rejection_dA:
            self.dA_window.toggle_outlier_rejection(True)

    def stop_graph_thread(self, hard_stop: bool = True):
        """
        Stop the currently running GraphThread
        """

        if self.graph_worker is not None:
            # disconent singals to ensure signals don't reach a dying thread
            self.switch_outlier_rejection.disconnect()    
            self.dA_window.dA_switch_outlier_rejection.disconnect()
            self.deviation_threshold_changed.disconnect()

            if hard_stop:
                # If thread is stopped for a measurement, disable outlier rejection
                self.toggle_outlier_rejection(False)
                self.dA_window.toggle_outlier_rejection(False)

            # stop thread
            self.graph_worker.stop()
            self.graph_worker.wait()
            self.graph_worker = None

    
    """Helper functions: delay line control"""

    def Submitted(self):
        """
        Handle delay stage movement commands from the user.
        """

        try:
            value = float(self.delay_input.text())
            current_bar_value = self.delay_bar.value()

            # calculate target position and validate it
            if 0 <= current_bar_value + value <= 8672:
                self.run_command_signal.emit(f"MoveRelative {value}", "ButtonPress", 0, 0)
                print(f"Emitting command: MoveRelative {value}")

                # update the delay bar visually in the GUI
                self.delay_bar_update.emit(current_bar_value + value)
                self.delay_bar.setFormat(f"{round(current_bar_value + value, 2)}/8672.66")
            else:
                raise ValueError("Value is out of range.")
            
        except ValueError as ve:
            show_error_message(str(ve))
        except Exception as e:
            show_error_message(str(e))

    def update_delay_bar(self, value):
        """
        updates the delay stage progress bar in the GUI.
        """
        value = max(0, min(value, self.delay_bar.maximum()))
        self.delay_bar.setValue(int(value))
        self.delay_bar.setFormat(f"{round(value,2)}/8672.66")
        pass


    def SetReference(self):
        self.run_command_signal.emit("SetReference", "ButtonPress", 0, 0)

    def GoToReference(self):
        self.run_command_signal.emit("GoToReference", "ButtonPress", 0, 0)


    """Helper functions: wavelenght calibration probe plot"""

    def set_wavelength_mapping(self, wavelengths, unit):
        """
        Map pixel index → wavelength for the probe plot.
        """

        self.wavelenghts = wavelengths
        # set label
        self.probe_graph.setLabel('bottom', unit)
        # create ampping
        self.probe_wavelength_axis.set_values(wavelengths)
   

    def reset_to_pixel_axis(self, label="Pixel index"):
        """
        Drop the wavelength lookup, back to raw pixel numbers.
        """

        self.wavelenghts = None
        # clear the mapping
        self.probe_wavelength_axis.clear_values()
        # reset the label
        self.probe_graph.setLabel('bottom', label)
    
class MarkedProgressBar(QProgressBar):
    def __init__(self, *args, marker_value=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.marker_value = marker_value

    def set_marker(self, value):
        self.marker_value = value
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.marker_value is not None:
            painter = QPainter(self)
            pen = QPen(QColor("red"), 2)
            painter.setPen(pen)
            min_val, max_val = self.minimum(), self.maximum()
            if max_val > min_val:
                ratio = (self.marker_value - min_val) / (max_val - min_val)
                x = int(ratio * self.width())
                painter.drawLine(x, 0, x, self.height())
            painter.end()