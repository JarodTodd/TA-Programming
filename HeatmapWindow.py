from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import pyqtgraph as pg
from WorkerThread import *
from HeatmapInterface import *
from dAwindow import *
import numpy as np                      
from heatmap import TAPlotWidget

class HeatmapWindow(QWidget):
    """
    Window for displaying and interacting with the heatmap and related controls.
    """

    def __init__(self, dls_window, dA_Window):
        """
        Initialize the HeatmapWindow.

        Args:
            dls_window: Reference to the DLS window.
            dA_Window: Reference to the dA window.
        """
        super().__init__()
        self.setWindowTitle("Camera Interface")
        self.DLSWindow = dls_window
        self.worker = MeasurementWorker("", "StartUp", 0, 0, 'localhost', 9999)
        self.interface = Heatmap_Interface()
        self.dAwindow = dA_Window
        self.pos = 0
        self.setup_ui()

    def setup_ui(self):
        """
        Set up the user interface components and layout.
        """
        self.t_0 = 0
        self.layout = QVBoxLayout()
        # Main layout as a grid
        self.grid_layout = QGridLayout()

        # TAPlotWidget initialization with demo data
        delay_times   = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]) # demo delays for initial empty draw
        pixel_indices = np.arange(1023)
        self.ta_widgets = TAPlotWidget(delay_times, pixel_indices) 
        self.ta_widgets.canvas_heatmap.setBackground('w')
        self.ta_widgets.canvas_plot1.setBackground('w')
        self.ta_widgets.canvas_plot2.setBackground('w')

        # Adding interaction elements to GUI
        bottom_right_layout = QVBoxLayout()
        self.interface_widget = QWidget()
        self.interface = Heatmap_Interface()
        self.interface.setupUi(self.interface_widget)
        bottom_right_layout.addWidget(self.interface_widget)

        # Combo box for heatmap mode selection
        self.heatmap_combo = QComboBox()
        self.heatmap_combo.addItems(["Average of all scans", "Current scan"])
        self.heatmap_combo.currentIndexChanged.connect(self.on_combo_changed)

        # Heatmap display box
        self.heatmapbox = QWidget()
        heatmap_layout = QVBoxLayout()                      
        self.heatmapbox.setLayout(heatmap_layout)  
        heatmap_layout.addWidget(self.heatmap_combo)
        heatmap_layout.addWidget(self.ta_widgets.canvas_heatmap)

        # Placing widgets in the grid layout
        self.grid_layout.addWidget(self.heatmapbox, 0, 0)
        self.grid_layout.addWidget(self.ta_widgets.canvas_plot1, 0, 1)
        self.grid_layout.addWidget(self.ta_widgets.canvas_plot2, 1, 0)
        self.grid_layout.addWidget(self.interface_widget, 1, 1)

        self.setLayout(self.grid_layout)

        
    def update_current_delay(self, value):
        """
        Update the current delay value and synchronize related UI elements.

        Args:
            value (float): The new delay value.
        """
        value = round(value, 2)
        self.pos = value
        self.interface.current_delay.setText(f"{value}")
        slider_value = int(value * 1000 - self.t_0 * 1000)
        self.dAwindow.verticalSlider.setValue(slider_value)
        max_range = int(8672666 - self.t_0 * 1000)
        if slider_value > 0:
            self.dAwindow.verticalSlider.setRange(-250000, max_range)
        elif max_range - slider_value < 8672666:
            self.dAwindow.verticalSlider.setRange(slider_value - 250000, max_range)
        else:
            self.dAwindow.verticalSlider.setRange(0, max_range)

        self.dAwindow.abs_pos_line.setText(f"{value}")
        self.dAwindow.rel_pos_line.setText(f"{round(value-self.t_0, 2)}")
        self.dAwindow.move_target_box.setValue(value)
        self.DLSWindow.delay_bar.setValue(value)
        self.interface.progressbar.setValue(value)

    def update_current_step(self, step, scans):
        """
        Update the current step and scan count in the interface.

        Args:
            step (int): The current step.
            scans (int): The current scan count.
        """
        self.interface.current_step.setText(str(step))
        self.interface.current_scan.setText(str(scans))

    def update_t0(self, t_0):
        """
        Update the t_0 (zero delay) value and synchronize related UI elements.

        Args:
            t_0 (float): The new t_0 value.
        """
        self.t_0 = round(t_0, 2)
        self.interface.t0_line.setText(f"{self.t_0}")
        self.dAwindow.t_0 = self.t_0
        self.dAwindow.t0_spinbox.setValue(self.t_0)
        slider_value = int(self.pos * 1000 - self.t_0 * 1000)
        if self.pos == self.t_0:
            self.dAwindow.verticalSlider.setValue(0)
            self.dAwindow.rel_pos_line.setText(f"{0}")

        if self.pos - self.t_0 < 0:
            self.dAwindow.verticalSlider.setRange(slider_value-250000, int(8672666 - self.t_0 * 1000))
            self.dAwindow.verticalSlider.setValue(slider_value)
            self.dAwindow.rel_pos_line.setText(str(round(slider_value/1000, 2)))
            self.dAwindow.abs_pos_line.setText(str(round(self.pos, 2)))
            self.dAwindow.move_target_box.setValue(round(self.pos, 2))
        else:
            self.dAwindow.verticalSlider.setRange(-250000, int(8672666 - self.t_0 * 1000))
            self.dAwindow.abs_pos_line.setText(f"{self.t_0}")
            self.dAwindow.rel_pos_line.setText(f"{0}")

    def show_error_message(self, error_message):
        """
        Display an error message dialog.

        Args:
            error_message (str): The error message to display.
        """
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Error")
        msgbox.setText("An error occurred:")
        msgbox.setInformativeText(error_message)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec()

    @Slot(float, float, float)
    def update_graph(self, delaytimes, dA_inputs_avg):
        """
        Update the graph with new delaytimes and dA_inputs.

        Args:
            delaytimes (float): New delay time value.
            dA_inputs_avg (float): New average dA input value.
        """
        self.delaytimes.append(delaytimes)
        self.dA_inputs_avg.append(dA_inputs_avg)

    def on_combo_changed(self):
        """
        Handle changes in the heatmap mode combo box.
        """
        selected = self.heatmap_combo.currentText()
        self.ta_widgets.set_mode(selected)
