from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
import pyqtgraph as pg


class dA_Window(QWidget):
    run_command_signal = Signal(str, str, int, int)
    dA_switch_outlier_rejection = Signal(bool)
    dA_deviation_threshold_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.t_0 = 0
        self.setWindowTitle("Camera Interface")

        self.setupUi(self)
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)
        
        self.probe_worker = None


    def setupUi(self, Form):
        Form.setWindowTitle("dA Window")
        main_layout = QHBoxLayout(Form)

        # Left vertical layout with spacer
        self.left_layout = QVBoxLayout()
        main_layout.addLayout(self.left_layout)

        #dA plot
        self.dA_plot = pg.PlotWidget()
        self.dA_plot.setTitle("dA Spectrum")
        self.dA_plot.setLabel('left', 'Intensity (counts)')
        self.dA_plot.setLabel('bottom', 'Wavelength (nm)')
        self.dA_plot.setBackground('w')
        self.dA_plot.getViewBox().enableAutoRange(False, False)
        self.dA_plot.setContentsMargins(0, 0, 0, 0)
        self.dA_plot.scene().sigMouseClicked.connect(lambda event: self.on_click(event, self.dA_plot))
        # self.dA_plot.setLimits(xMin=0, xMax=1074, yMin=0, yMax=16500)

        # vertical, draggable guide-lines 
        self.range_line_left  = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen(color='#C0D5DC', width=1))
        self.labelled_line_left = pg.InfLineLabel(self.range_line_left, text="{value:.0f}", position=0.95, color='black', fill=(255, 255, 255, 180)) 
        self.range_line_right = pg.InfiniteLine(pos=1023, angle=90, movable=True, pen=pg.mkPen(color='#C0D5DC', width=1))
        self.labelled_line_right = pg.InfLineLabel(self.range_line_right, text="{value:.0f}", position=0.95, color='black', fill=(255, 255, 255, 180)) 
        font_size = QFont()
        font_size.setPointSize(7)
        self.labelled_line_right.textItem.setFont(font_size)
        self.labelled_line_left.textItem.setFont(font_size)

        # add guide-lines to dA-graph
        for line in (self.range_line_left, self.range_line_right):
            line.setVisible(False)                             
            line.sigPositionChanged.connect(self.dA_outlier_range_changed)
            self.dA_plot.addItem(line)

        self.left_layout.addWidget(self.dA_plot)
        self.dA_curve = self.dA_plot.plot([], pen='r')

        # Combo box for selecting Average or Median
        self.dA_inputs_avg = []
        self.dA_inputs_med = []

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
        self.left_layout.addWidget(outlier_group)

        outlier_group.setLayout(outlier_layout)
        self.left_layout.addWidget(outlier_group)
        self.toggle_outlier_rejection(False)

        # Save button
        self.save_data_button = QPushButton("Save Intensity Data")
        self.left_layout.addWidget(self.save_data_button)
        # Right layout
        right_layout = QHBoxLayout()
        main_layout.addLayout(right_layout)


        self.verticalSlider = QSlider(Qt.Vertical)
        if self.t_0 == 0:
            self.verticalSlider.setRange(0, 8672666)
        else:
            self.verticalSlider.setRange(-250000, 8672666 - self.t_0 * 1000)
        self.verticalSlider.setSingleStep(2)
        self.verticalSlider.setTickInterval(250000)
        self.verticalSlider.setTickPosition(QSlider.TicksLeft)
        self.verticalSlider.setInvertedAppearance(True)
        self.verticalSlider.sliderReleased.connect(self.emit_slider_signal)
        self.verticalSlider.valueChanged.connect(self.update_abs_rel)
        right_layout.addWidget(self.verticalSlider)

        # Grid layout for controls
        vbox = QVBoxLayout()
        right_layout.addLayout(vbox)

        self.label = QLabel("Move to target, ps")
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        vbox.addWidget(self.label)
        self.move_target_box = QDoubleSpinBox()
        self.move_target_box.setRange(-8672.66, 8672.66)
        vbox.addWidget(self.move_target_box)
        self.label_2 = QLabel("Current absolute position, ps")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        vbox.addWidget(self.label_2)
        self.abs_pos_line = QLineEdit()
        self.abs_pos_line.setEnabled(False)
        vbox.addWidget(self.abs_pos_line)
        self.label_3 = QLabel("Time Zero, ps")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        vbox.addWidget(self.label_3)
        self.t0_spinbox = QDoubleSpinBox()
        self.t0_spinbox.setRange(0, 8672.66)
        vbox.addWidget(self.t0_spinbox)
        self.set_current_button = QPushButton("Set current")
        self.set_current_button.clicked.connect(self.set_current)
        vbox.addWidget(self.set_current_button)
        self.label_4 = QLabel("Current relative position, ps")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        vbox.addWidget(self.label_4)
        self.rel_pos_line = QLineEdit()
        self.rel_pos_line.setEnabled(False)
        vbox.addWidget(self.rel_pos_line)

    def toggle_outlier_rejection(self, selected: bool) -> None:
        self.deviation_label.setVisible(selected)
        self.deviation_spinbox.setVisible(selected)

        self.rejected_label.setVisible(selected)
        self.rejected_value.setVisible(selected)

        self.range_line_left.setVisible(selected)
        self.range_line_right.setVisible(selected)

        self.dA_switch_outlier_rejection.emit(selected)

    def emit_deviation_change(self, value: float):
        self.dA_deviation_threshold_changed.emit(value)

    @Slot()
    def dA_outlier_range_changed(self):
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

    def set_current(self):
        self.run_command_signal.emit("SetReference", "ButtonPress", 0, 0)
        self.t_0 = round(float(self.abs_pos_line.text()),2)
        self.rel_pos_line.setText("0")
        self.t0_spinbox.setValue(self.t_0)
        self.verticalSlider.setRange(-250000, 8672666 - self.t_0 * 1000)
        self.verticalSlider.setValue(0)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self.verticalSlider.setValue(self.verticalSlider.value() + 1000)
                return True
            elif event.key() == Qt.Key_Down:
                self.verticalSlider.setValue(self.verticalSlider.value() - 1000)
                return True
        return super().eventFilter(obj, event)
    

    def emit_slider_signal(self):
        # Add a dummy variable to the function so it doesn't emit signals everytime the slider is updated 
        # because now it updates when a measurement is being done and emits doubled movement signals causing errors
        value = self.verticalSlider.value()
        print(f"emitting now: {value}")
        self.run_command_signal.emit(f"MoveRelative {value/1000:.3f}", "ButtonPress", 0, 0)

    def update_abs_rel(self, value):
        value = value/1000
        self.move_target_box.setValue(round(value + self.t_0, 2))
        self.abs_pos_line.setText(str(round(value + self.t_0, 2)))
        self.rel_pos_line.setText(str(round(value, 2)))



    def redraw_dA_plot(self):
        self.update_dA_graph(self.dA_inputs_avg, self.dA_inputs_med)

    @Slot(object, object)
    def update_dA_graph(self, avg_list, med_list):
        self.dA_inputs_avg = avg_list
        self.dA_inputs_med = med_list
        
        self.dA_curve.setData(self.dA_inputs_avg)     

    def on_click(self, event, plot_widget):
        pos = event.scenePos()
        vb = plot_widget.getViewBox()
        view_rect = vb.sceneBoundingRect()

        # Check if click is close to the left side (minimum X)
        if 0 < (pos.x() - view_rect.left()) < 20 and 0 < (pos.y() - view_rect.bottom()) < 20:
            new_min, ok = QInputDialog.getDouble(self, "Set Minimum x-axis", "Enter new x-minimum:")
            if ok:
                max_x = plot_widget.viewRange()[0][1]  # Get current max
                plot_widget.setXRange(new_min, max_x, padding=0)

        
        # Check if click is close to the right side (maximum X)
        if abs(pos.x() - view_rect.right()) < 20 and abs(pos.y() - view_rect.bottom()) < 20:
            new_max, ok = QInputDialog.getDouble(self, "Set Maximum x-axis", "Enter new x-maximum:")
            if ok:
                min_x = plot_widget.viewRange()[0][0]
                plot_widget.setXRange(min_x, new_max, padding=0)
        
        # Check if click is close to the top side (maximum Y)
        if abs(pos.y() - view_rect.top()) < 20 and abs(pos.x() - view_rect.left()) < 20:
            new_max, ok = QInputDialog.getDouble(self, "Set Maximum y-axis", "Enter new y-maximum:")
            if ok:
                max_y = plot_widget.viewRange()[1][1]
                plot_widget.setYRange(max_y, new_max, padding=0)
        
        # Check if click is close to the bottom side (minimum Y)
        if -20 < (pos.y() - view_rect.bottom()) < 0 and -20 < (pos.x() - view_rect.left()) < 0:
            new_min, ok = QInputDialog.getDouble(self, "Set Minimum y-axis", "Enter new y-minimum:")
            if ok:
                min_y = plot_widget.viewRange()[1][0]
                plot_widget.setYRange(new_min, min_y, padding=0)

        print(plot_widget.viewRange())






if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = dA_Window()
    ui.show()
    sys.exit(app.exec())
    sys.exit(app.exec())