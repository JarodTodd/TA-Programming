from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import pyqtgraph as pg
from WorkerThread import *
from Heatmap_Interface import *
from dAwindow import *
import numpy as np                      
from heatmap import TAPlotWidget

class HeatmapWindow(QWidget):

    def __init__(self, dls_window, dA_Window):
        super().__init__()
        self.setWindowTitle("Camera Interface")
        self.DLSWindow = dls_window
        self.worker = MeasurementWorker("", "StartUp", 0, 0, 'localhost', 9999)
        self.interface = Ui_Bottom_right()
        self.dAwindow = dA_Window
        self.setup_ui()


    def setup_ui(self):
        self.t_0 = 0
        self.layout = QVBoxLayout()
        # Main layout as a grid
        self.grid_layout = QGridLayout()

        # TAPlotWidget 
        delay_times   = np.array([0.0, 0.2, 0.5, 1.0])
        pixel_indices = np.arange(1023)
        self.ta_widgets = TAPlotWidget(delay_times, pixel_indices) 
        self.ta_widgets.canvas_heatmap.setBackground('w')
        self.ta_widgets.canvas_plot1.setBackground('w')
        self.ta_widgets.canvas_plot2.setBackground('w')

        # Adding interaction elements to GUI
        bottom_right_layout = QVBoxLayout()
        # bottom_right_layout.addLayout(self.form_layout)
        # bottom_right_layout.addWidget(self.status_label)
        self.interface_widget = QWidget()
        self.interface = Ui_Bottom_right()
        self.interface.setupUi(self.interface_widget)
        bottom_right_layout.addWidget(self.interface_widget)

        self.heatmap_combo = QComboBox()
        self.heatmap_combo.addItems(["current scan", "average off all scans"])
        self.heatmap_combo.currentIndexChanged.connect(self.on_combo_changed)

        self.heatmapbox = QWidget()
        heatmap_layout = QVBoxLayout()                      
        self.heatmapbox.setLayout(heatmap_layout)  
       
        heatmap_layout.addWidget(self.heatmap_combo)
        heatmap_layout.addWidget(self.ta_widgets.canvas_heatmap)

        # Putting GUI elements in correct spaces
        self.grid_layout.addWidget(self.heatmapbox, 0, 0)
        self.grid_layout.addWidget(self.ta_widgets.canvas_plot1, 0, 1)
        self.grid_layout.addWidget(self.ta_widgets.canvas_plot2, 1, 0)
        self.grid_layout.addWidget(self.interface_widget, 1, 1)

        self.setLayout(self.grid_layout)

    def update_current_delay(self, value):
        """Update the current delay values."""
        value = round(value, 2)
        self.interface.current_delay.setText(f"{value}")
        self.dAwindow.verticalSlider.setValue(value*1000)
        self.dAwindow.verticalSlider.setRange(-250000, (8672666 - value*1000))
        self.dAwindow.abs_pos_line.setText(f"{value}")
        self.DLSWindow.delay_bar.setValue(value)

    def update_current_step(self, step, scans):
        self.interface.current_step.setText(str(step))
        self.interface.current_scan.setText(str(scans))

    def update_t0(self, t_0):
        """Update the t_0 value."""
        self.t_0 = round(t_0,2)
        self.interface.t0_line.setText(f"{self.t_0}")
        self.dAwindow.t_0 = self.t_0
        self.dAwindow.t0_spinbox.setValue(self.t_0)
        self.dAwindow.verticalSlider.setValue(0)
        self.dAwindow.verticalSlider.setRange(-250000, (8672666 - self.t_0*1000))
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

    def on_combo_changed(self):
        selected = self.heatmap_combo.currentText()
        self.ta_widgets.set_mode(selected)



