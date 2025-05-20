import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
from camera_gui import *
from dAwindow import *

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
        self.dA_window = dA_Window()
        self.dls_window.probe_worker.dA_update.connect(self.dA_window.update_dA_graph,Qt.QueuedConnection)

        # Add tabs    
        self.tabs.addTab(self.shot_delay_app, "Shot Delay App")
        self.tabs.addTab(self.dls_window, "DLS Window")
        self.tabs.addTab(self.dA_window, "dA Window")

if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    worker = Measurementworker("", "StartUp", 0, 0)
    probe = ProbeThread()
    output_signal = Signal(str)


    worker.started.connect(main_app.dls_window.stop_probe_thread, Qt.QueuedConnection)
    worker.parsed_content_signal.connect(main_app.shot_delay_app.ta_widgets.update_delay_stages, Qt.BlockingQueuedConnection)
    worker.plot_row_update.connect(main_app.shot_delay_app.ta_widgets.update_row, Qt.QueuedConnection)
    worker.measurement_data_updated.connect(main_app.shot_delay_app.update_graph, Qt.QueuedConnection)
    worker.update_probe.connect(main_app.dls_window.update_probe_graph, Qt.QueuedConnection)

    worker.error_occurred.connect(main_app.shot_delay_app.show_error_message)
    
    worker.error_occurred.connect(main_app.dls_window.show_error_message)  # Optional error handler
    worker.update_delay_bar_signal.connect(main_app.shot_delay_app.update_progress_bar)
    worker.update_delay_bar_signal.connect(main_app.dls_window.update_delay_bar)

    worker.finished.connect(main_app.dls_window.start_probe_thread, Qt.QueuedConnection)
    
    
    def start_process(argument):
        if worker.process is None:
            worker.process = QProcess()

        if worker.process.state() == QProcess.Running:
            print("Terminating existing process...")
            worker.process.terminate()
            worker.process.waitForFinished()
        print(type(argument))
        worker.process.setProgram(ironpython_executable)
        if isinstance(argument, list):  # Handle list arguments
            worker.start()
        elif isinstance(argument, str):  # Handle string arguments
            worker.process.setArguments([script_path, argument])
            worker.process.start()

            try:
                worker.process.finished.disconnect()
            except Exception:
                print("Signals already disconnected.")
                
            worker.process.readyReadStandardOutput.connect(worker.handle_process_output)
            worker.process.readyReadStandardError.connect(worker.handle_process_error)
            worker.process.finished.connect(lambda: print("Process finished."))

    worker.start_process_signal.connect(start_process)

    def handle_button_press(content, orientation, shots, scans):
        if len(content) == 1:
            content = content[0]
        worker.update_command(content, orientation, shots, scans)
        start_process(content)

    main_app.dls_window.run_command_signal.connect(handle_button_press)
    main_app.shot_delay_app.bottomright.trigger_worker_run.connect(handle_button_press)



    def stop_worker():
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
        probe.stop()
        QCoreApplication.processEvents()
        print("Application exit cleanup complete.")
        app.aboutToQuit.disconnect(stop_worker)
        app.quit()

    worker.start()
    app.aboutToQuit.connect(stop_worker)
    app.exec()
