from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
import pyqtgraph as pg


class dA_Window(QWidget):

    def __init__(self):
        super().__init__()
        self.t_0 = 0
        self.setWindowTitle("Camera Interface")

        self.worker = Measurementworker("", "", 0, 0)
        self.setupUi(self)
        self.worker.update_ref_signal.connect(self.update_time_zero, Qt.QueuedConnection)
        self.worker.update_delay_bar_signal.connect(self.update_slider, Qt.QueuedConnection)


    def setupUi(self, Form):
        Form.setWindowTitle("dA Window")
        Form.resize(640, 623)
        main_layout = QHBoxLayout(Form)

        # Left vertical layout with spacer
        self.left_layout = QVBoxLayout()
        main_layout.addLayout(self.left_layout)

        

        #dA plot
        self.dA_plot = pg.PlotWidget()
        self.dA_plot.setTitle("Intensity (counts)")
        self.dA_plot.setLabel('left', 'Probe')
        self.dA_plot.setLabel('bottom', 'Wavelength (nm)')
        self.dA_plot.setBackground('w')
        self.left_layout.addWidget(self.dA_plot)

        # Combo box for selecting Average or Median
        self.dA_inputs_avg = []
        self.dA_inputs_med = []

        self.dA_plot_combobox = QComboBox()
        self.dA_plot_combobox.addItems(["Average", "Median"])
        self.dA_plot_combobox.setCurrentText("Average")
        self.left_layout.addWidget(self.dA_plot_combobox)
        self.dA_plot_combobox.currentIndexChanged.connect(lambda _=0: self.redraw_dA_plot())

        # Save button
        self.save_data_button = QPushButton("Save Intensity Data")
        self.left_layout.addWidget(self.save_data_button)
        # Right layout
        right_layout = QHBoxLayout()
        main_layout.addLayout(right_layout)

        # Vertical slider
        slider_ticks = QVBoxLayout()
        tick_values = list(range(0, 8672, 250))
        for i in tick_values:
            label = QLabel(f"{i}-")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            label.setFixedHeight(22)
            slider_ticks.addWidget(label)

        right_layout.addLayout(slider_ticks)
        self.verticalSlider = QSlider(Qt.Vertical)
        self.verticalSlider.setRange(0, 8672666)
        self.verticalSlider.setSingleStep(0.01)
        self.verticalSlider.setInvertedAppearance(True)
        self.verticalSlider.valueChanged.connect(lambda: self.update_abs_rel(self.verticalSlider.value()))
        right_layout.addWidget(self.verticalSlider)

        # Grid layout for controls
        grid = QGridLayout()
        right_layout.addLayout(grid)

        self.label = QLabel("Move to target, ps")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        grid.addWidget(self.label, 0, 0)
        self.move_target_box = QDoubleSpinBox()
        self.move_target_box.setRange(-8626.66, 8626.66)
        grid.addWidget(self.move_target_box, 1, 0)
        self.label_2 = QLabel("Current absolute position, ps")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        grid.addWidget(self.label_2, 2, 0)
        self.abs_pos_line = QLineEdit()
        self.abs_pos_line.setEnabled(False)
        grid.addWidget(self.abs_pos_line, 3, 0)
        self.label_3 = QLabel("Time Zero, ps")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        grid.addWidget(self.label_3, 4, 0)
        self.t0_spinbox = QDoubleSpinBox()
        self.t0_spinbox.setRange(0, 8626.66)
        grid.addWidget(self.t0_spinbox, 5, 0)
        self.setcurrentbutton = QPushButton("Set current")
        grid.addWidget(self.setcurrentbutton, 6, 0)
        self.label_4 = QLabel("Current relative position, ps")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        grid.addWidget(self.label_4, 7, 0)
        self.rel_pos_line = QLineEdit()
        self.rel_pos_line.setEnabled(False)
        grid.addWidget(self.rel_pos_line, 8, 0)

    def update_slider(self, value):
        value = round(value, 2)
        self.verticalSlider.setValue(value*1000)
        self.abs_pos_line.setText(f"{value}")
        self.rel_pos_line.setText(f"{0}")

    def update_abs_rel(self, value):
        value = round(value/1000, 2)
        self.abs_pos_line.setText(str(value))
        self.rel_pos_line.setText(str(value - self.t_0))

    def update_time_zero(self, value):
        value = round(value, 2)
        self.verticalSlider.setValue(value*1000)
        self.t0_spinbox.setValue(value)
        self.abs_pos_line.setText(f"{value}")
        self.rel_pos_line.setText(f"{0}")

    def redraw_dA_plot(self):
        self.update_dA_graph(self.probe_inputs_avg, self.probe_inputs_med)

    @Slot(object, object)
    def update_dA_graph(self, avg_list, med_list):
        self.dA_plot.clear()
        self.probe_inputs_avg = avg_list
        self.probe_inputs_med = med_list
        if self.dA_plot_combobox.currentText() == "Average":
            self.dA_plot.plot(range(len(avg_list)), avg_list, pen='r')
        else:
            self.dA_plot.plot(range(len(med_list)), med_list, pen='b')


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = dA_Window()
    ui.show()
    sys.exit(app.exec())
    sys.exit(app.exec())