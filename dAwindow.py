from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *


class dA_Window(QWidget):

    def __init__(self):
        super().__init__()
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
        left_layout = QVBoxLayout()
        left_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        main_layout.addLayout(left_layout)

        # Right layout
        right_layout = QHBoxLayout()
        main_layout.addLayout(right_layout)

        # Vertical slider
        slider_ticks = QVBoxLayout()
        tick_values = list(range(0, 8627, 250))
        for i in tick_values:
            label = QLabel(f"{i}-")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            label.setFixedHeight(22)
            slider_ticks.addWidget(label)

        right_layout.addLayout(slider_ticks)
        self.verticalSlider = QSlider(Qt.Vertical)
        self.verticalSlider.setRange(0, 8627)
        self.verticalSlider.setInvertedAppearance(True)
        self.verticalSlider.valuechanged.connect()
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
        self.verticalSlider.setValue(value)
        self.abs_pos_line.setText(f"{value}")
        self.rel_pos_line.setText(f"{0}")

    def update_time_zero(self, value):
        value = round(value, 2)
        self.verticalSlider.setValue(value)
        self.t0_spinbox.setValue(value)
        self.abs_pos_line.setText(f"{value}")
        self.rel_pos_line.setText(f"{0}")


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    ui = dA_Window()
    ui.show()
    sys.exit(app.exec())
    sys.exit(app.exec())