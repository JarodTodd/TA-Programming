from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel
)
from PySide6.QtCore import Qt
import subprocess
import sys

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

class ShotDelayApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera interface")
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout()

        self.form_layout = QFormLayout()
        self.shots_input = QLineEdit()
        self.delays_input = QLineEdit()

        self.shots_input.setPlaceholderText("Enter number of shots")
        self.delays_input.setPlaceholderText("Enter number of delays")

        self.form_layout.addRow("Number of Shots:", self.shots_input)
        self.form_layout.addRow("Number of Delays:", self.delays_input)

        self.run_button = QPushButton("Run")
        self.run_button.setEnabled(False)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)

        # Matplotlib figure and canvas
        # self.figure, self.ax = plt.subplots()
        # self.canvas = FigureCanvas(self.figure)

        # add all widgets 
        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.run_button)
        self.layout.addWidget(self.status_label)
        # self.layout.addWidget(self.canvas) 

        self.setLayout(self.layout)

        self.shots_input.textChanged.connect(self.validate_inputs)
        self.delays_input.textChanged.connect(self.validate_inputs)
        self.run_button.clicked.connect(self.run_external_script)

    def validate_inputs(self):
        try:
            shots = int(self.shots_input.text())
            delays = int(self.delays_input.text())
            valid = shots > 0 and delays > 0
        except ValueError:
            valid = False
        self.run_button.setEnabled(valid)

    def run_external_script(self):
        shots = self.shots_input.text()
        delays = self.delays_input.text()
        try:
            subprocess.run(
                [sys.executable, "main.py", shots, delays],
                check=True
            )
            self.status_label.setText("Script ran successfully!")
        except subprocess.CalledProcessError as e:
            self.status_label.setText(f"Error running script: {e}")

if __name__ == "__main__":
    app = QApplication([])
    window = ShotDelayApp()
    window.show()
    sys.exit(app.exec())
