import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
from camera_gui import *

ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tab-Based Application")
        self.setGeometry(100, 100, 800, 600)

        # Create a QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.dls_window = DLSWindow()
        self.shot_delay_app = ShotDelayApp(self.dls_window)

        # Add tabs    
        self.tabs.addTab(self.shot_delay_app, "Shot Delay App")
        self.tabs.addTab(self.dls_window, "DLS Window")


if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    worker = Measurementworker("", "StartUp", 0)
    output_signal = Signal(str)


    def start_process(argument):
        if worker.process is None:
            worker.process = QProcess()

        if worker.process.state() == QProcess.Running:
            print("Terminating existing process...")
            worker.process.terminate()
            worker.process.waitForFinished()

        worker.process.setProgram(ironpython_executable)
        if isinstance(argument, list):  # Handle list arguments
            worker.run()
        elif isinstance(argument, str):  # Handle string arguments
            worker.process.setArguments([script_path, argument])
            worker.process.start()

            try:
                worker.process.finished.disconnect()
            except RuntimeError:
                print("Signals already disconnected.")
                
            worker.process.readyReadStandardOutput.connect(lambda: print(worker.process.readAllStandardOutput().data().decode('utf-8').strip()))
            worker.process.readyReadStandardError.connect(lambda: print(worker.process.readAllStandardError().data().decode('utf-8').strip()))
            worker.process.finished.connect(lambda: print("Process finished."))

    worker.start_process_signal.connect(start_process)

    def handle_button_press(content, orientation, shots):
        parsed_content = [item.strip() for item in content.split(",") if item.strip()]

        if len(parsed_content) == 1:
            parsed_content = parsed_content[0]

        worker.update_command(parsed_content, orientation, shots)
        start_process(parsed_content)

    main_app.dls_window.run_command_signal.connect(handle_button_press)
    main_app.shot_delay_app.trigger_worker_run.connect(handle_button_press)

    cleanup_done = False
    import traceback

    def stop_worker():
        global cleanup_done
        traceback.print_stack()
        if cleanup_done:
            print("Cleanup already done. Skipping redundant call to stop_worker.")
            return

        if worker.process:
            try:
                worker.process.readyReadStandardOutput.disconnect()
                worker.process.readyReadStandardError.disconnect()
                worker.process.finished.disconnect()
            except RuntimeError:
                print("Signals already disconnected.")

            if worker.process.state() == QProcess.Running:
                worker.process.terminate()
                worker.process.waitForFinished()

        worker.stop()
        QCoreApplication.processEvents()
        print("Application exit cleanup complete.")
        app.aboutToQuit.disconnect(stop_worker)
        app.quit()

        # Mark cleanup as done
        cleanup_done = True

    worker.start()
    app.aboutToQuit.connect(stop_worker)
    app.exec()
