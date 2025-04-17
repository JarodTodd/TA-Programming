from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sys
import subprocess
import random
from main import *
from camera import *

ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"

class DLSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Delayline GUI")
        print("I exist")
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layouts
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        hbox = QHBoxLayout()

        initialize_button = QPushButton("Initialize")
        initialize_button.clicked.connect(self.Initialize)
        hbox.addWidget(initialize_button)

        disable_button = QPushButton("Disable/Ready")
        disable_button.clicked.connect(self.Disable_click)
        hbox.addWidget(disable_button)

        move_neg_button = QPushButton("Move -100ps")
        move_neg_button.clicked.connect(self.Move_back_click)
        move_neg_button.clicked.connect(self.Submitted)
        hbox.addWidget(move_neg_button)

        move_pos_button = QPushButton("Move +100ps")
        move_pos_button.clicked.connect(self.Move_click)
        move_pos_button.clicked.connect(self.Submitted)
        hbox.addWidget(move_pos_button)

        layout.addLayout(hbox)

        hbox2 = QHBoxLayout()
        self.delay_input = QLineEdit()
        self.delay_input.setPlaceholderText("Enter delay time")
        self.delay_input.setValidator(QDoubleValidator(-8672000.0, 8672000.0, 20, self))
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


        
        layout.addLayout(hbox2)
        layout.addLayout(hbox3)
        layout.addLayout(hbox4)

    def run_script(self, argument):
        try:
            result = subprocess.Popen(
                [ironpython_executable, script_path, argument],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = result.communicate()
            print(stdout)
            movement = ["Disable", "SetReference", "GetReference", "GetPosition"]
            if argument not in movement:
                stdout, stderr = result.communicate()
                print(self.delay_bar.value())

                # Decode the output
                decoded_output = stdout.decode('utf-8')

                # Strip unwanted characters and convert to float
                clean_output = decoded_output.strip()
                numerical_value = float(clean_output)

                # Update the delay progress bar with the numerical value
                self.update_delay_bar(numerical_value)
                print(self.delay_bar.value())
        except Exception as e:
            print(f"Error executing IronPython script: {e}")
        return stdout

    def Initialize(self):
        self.run_script("Initialize")

    def Disable_click(self):
        self.run_script("Disable")

    def Move_click(self):
        self.run_script("MovePositive")

    def Move_back_click(self):
        self.run_script("MoveNegative")

    def SetReference(self):
        self.run_script("SetReference")

    def GoToReference(self):
        self.run_script("GoToReference")
    
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
            barvalue = self.delay_bar.value()

            if unit == "ns":
                barvalue_ns = self.delay_bar.value() / 1000
                if 0 <= value <= (8.672 - barvalue_ns) or (value < 0 and abs(value) <= barvalue_ns):
                    self.run_script(f"MoveRelative {value}")
                    self.update_delay_bar(barvalue + value*1000)
                else:
                    raise ValueError(f"Value is out of range.")
            elif unit == "ps":
                if 0 <= value <= (8672 - barvalue) or (value < 0 and abs(value) <= barvalue):
                    self.run_script(f"MoveRelative {value/1000}")
                    self.update_delay_bar(barvalue + value)
                else:
                    raise ValueError(f"Value is out of range.")
            elif unit == "fs":
                barvalue_fs = self.delay_bar.value()*1000
                if 0 <= value <= (8672000 - barvalue_fs) or (value < 0 and abs(value) <= barvalue_fs):
                    self.run_script(f"MoveRelative {value/1000000}")
                    self.update_delay_bar(barvalue + value/1000)
                else:
                    raise ValueError(f"Value is out of range.")
        except ValueError as ve:
            self.show_error_message(str(ve))
        except Exception as e:
            self.show_error_message(f"An unexpected error occurred: {str(e)}")

    def update_delay_bar(self, value):
        value = max(0, min(value, self.delay_bar.maximum()))  # Ensure value is within the range
        self.delay_bar.setValue(round(value, 3))
        self.delay_bar.setFormat(f"{int(value)}/8672")

    def show_error_message(self, error_message):
        msgbox = QMessageBox()
        msgbox.setWindowTitle("Error")
        msgbox.setText("An error occurred:")
        msgbox.setInformativeText(error_message)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setStandardButtons(QMessageBox.Ok)
        msgbox.exec()

    def showFileDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Select a .txt File", "", "Text Files (*.txt);;All Files (*)")
        if fileName:
            self.file_label.setText(fileName)
            try:
                with open(fileName, 'r') as file:
                    content = file.read()
                
                self.text_display.setText(content)
            except Exception as e:
                self.show_error_message(f"Failed to load file: {e}")
        return content
    
    def RunMeasurement(self, content, number_of_shots):

        ref = self.run_script("GetReference")
        position = self.run_script("GetPosition")

        ref = float(ref.decode('utf-8').strip())
        position = float(position.decode('utf-8').strip())

        for item in content:
            if item[0]  == 'ns' or item[0] == 'nanosecond' or item[0] == 'nanoseconds':
                if ref + item[1] < 0:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
                if ref + item[1] > 8.672:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
            elif item[0] == 'ps' or item[0] == 'picosecond' or item[0] == 'picoseconds':
                if ref + item[1] < 0:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
                if ref + item[1] > 8672:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
            elif item[0] == 'fs' or item[0] == 'femtosecond' or item[0] == 'femtoseconds':
                if ref + item[1] < 0:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return
                if ref + item[1] > 8672000:
                    self.show_error_message(f"Reference point is out of range. {item[1]}")
                    return

        if round(ref, 3) != round(position, 3):
            self.run_script("GoToReference")
            self.update_delay_bar(ref*1000)

        last_item = 0
        for item in content:
            barvalue = self.delay_bar.value()
            unit = item[0].lower()
            pos = item[1]

            # Convert position to nanoseconds
            if unit in ['ps', 'picosecond', 'picoseconds']:
                pos /= 1000
            elif unit in ['fs', 'femtosecond', 'femtoseconds']:
                pos /= 1000000

            # Adjust position relative to the last item
            pos -= last_item

            print(f"pos: {pos}, last_item: {last_item}, item: {item}, barvalue: {barvalue}")

            # Move and update delay bar
            self.run_script(f"MoveRelative {pos}")
            self.update_delay_bar(barvalue + pos * 1000)

            print(f"Delay is {item[1]}")
            camera(number_of_shots, content.index(item))

            # Update last_item for the next iteration
            if unit in ['ns', 'nanosecond', 'nanoseconds']:
                last_item = item[1]
            elif unit in ['ps', 'picosecond', 'picoseconds']:
                last_item = item[1] / 1000
            elif unit in ['fs', 'femtosecond', 'femtoseconds']:
                last_item = item[1] / 1000000

        return 


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DLSWindow()
    window.show()
    result = subprocess.Popen(
        [ironpython_executable, script_path, "GetPosition"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, _ = result.communicate()
    window.update_delay_bar(float(stdout.decode('utf-8').strip())*1000)
    sys.exit(app.exec())
