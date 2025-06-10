from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
from camera_gui import *
from DLSWindow import *
from dAwindow import *
import time
ironpython_executable = r"C:\Users\PC026453\Documents\TA-Programming\IronPython 3.4\ipy.exe"
script_path = r"C:\Users\PC026453\Documents\TA-Programming\IronPythonDLS.py"


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HamburgerPresserWorks (tm)")
        self.setGeometry(100, 100, 800, 600)

        # Create a QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.dA_window = dA_Window()
        self.dls_window = DLSWindow(self.dA_window)
        self.shot_delay_app = ShotDelayApp(self.dls_window, self.dA_window)

        # Add tabs    
        self.tabs.addTab(self.shot_delay_app, "Main Window")
        self.tabs.addTab(self.dls_window, "Probe Spectrum")
        self.tabs.addTab(self.dA_window, "dA Spectrum")

        self.dls_window.start_probe_thread()

if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    worker = MeasurementWorker("", "StartUp", 0, 0, 'localhost', 9999)
    output_signal = Signal(str)

    """These connections update the heatmap, and the two corresponding graphs."""
    worker.plot_row_update.connect(main_app.shot_delay_app.ta_widgets.update_row, Qt.QueuedConnection)
    worker.measurement_data_updated.connect(main_app.shot_delay_app.update_graph, Qt.QueuedConnection)
    main_app.shot_delay_app.bottomright.parsed_content_signal.connect(main_app.shot_delay_app.ta_widgets.update_delay_stages, Qt.QueuedConnection)

    """These connections are responsible for the probe spectrum in the DLSWindow and keep it updated."""
    worker.started.connect(main_app.dls_window.stop_probe_thread, Qt.QueuedConnection)
    worker.update_probe.connect(main_app.dls_window.update_probe_data, Qt.QueuedConnection)
    worker.finished.connect(main_app.dls_window.start_probe_thread, Qt.QueuedConnection)
    
    """These connections are responsible for the dA spectrum in the dAWindow and keep it updated."""
    main_app.dls_window.probe_worker.dA_update.connect(main_app.dA_window.update_dA_graph, Qt.QueuedConnection)
    worker.update_dA.connect(main_app.dA_window.update_dA_graph, Qt.QueuedConnection)

    """These connections update sliders and progress bars to display the correct delay time."""
    worker.update_delay_bar_signal.connect(main_app.shot_delay_app.update_current_delay)
    worker.update_delay_bar_signal.connect(main_app.dls_window.update_delay_bar)
    worker.update_ref_signal.connect(main_app.shot_delay_app.update_t0)
    main_app.dls_window.delay_bar_update.connect(main_app.shot_delay_app.update_current_delay)
    worker.current_step_signal.connect(main_app.shot_delay_app.update_current_step)

    """This connection handles error messages from all applications/functions."""
    worker.error_occurred.connect(main_app.shot_delay_app.show_error_message)


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

            if worker.process and worker.process.state() == QProcess.Running:
                try:
                    worker.process.finished.disconnect()
                except RuntimeError:
                    print("Signal 'finished' was already disconnected or not connected.")
                
            worker.process.readyReadStandardOutput.connect(worker.handle_process_output)
            worker.process.readyReadStandardError.connect(worker.handle_process_error)
            worker.process.finished.connect(lambda: print("Process finished.", time.time()))

    worker.start_process_signal.connect(start_process)

    def handle_button_press(content, orientation, shots, scans):
        if len(content) == 1:
            content = content[0]
        worker.update_command(content, orientation, shots, scans)
        start_process(content)


    """These connections handle button presses and measurement starts."""
    main_app.dls_window.run_command_signal.connect(handle_button_press)
    main_app.shot_delay_app.bottomright.trigger_worker_run.connect(handle_button_press)
    main_app.dA_window.run_command_signal.connect(handle_button_press)



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
        # stop the probe thread
        main_app.dls_window.stop_probe_thread() 

        QCoreApplication.processEvents()
        print("Application exit cleanup complete.")
        app.aboutToQuit.disconnect(stop_worker)
        app.quit()

    worker.start()
    app.aboutToQuit.connect(stop_worker)
    app.exec()
