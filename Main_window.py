from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
from HeatmapWindow import *
from DLSWindow import *
from dAwindow import *
import time

# Paths of the IronPython parts; command prompt file and our command file.
ironpython_executable = r"C:\Users\PC032230\Documents\GitHub\TA-Programming\IronPython 3.4.2\net462\ipy.exe"
script_path = r"C:\Users\PC032230\Documents\GitHub\TA-Programming\IronPythonDLS.py"


class MainApp(QMainWindow):
    # Initialize all the necessary parts of the code
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HamburgerPresserWorks (tm)")
        self.setGeometry(100, 100, 800, 600)

        # Create a QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.dA_window = dA_Window()
        self.dls_window = DLSWindow(self.dA_window)
        self.shot_delay_app = HeatmapWindow(self.dls_window, self.dA_window)

        # Add tabs    
        self.tabs.addTab(self.shot_delay_app, "Main Window")
        self.tabs.addTab(self.dls_window, "Probe Spectrum")
        self.tabs.addTab(self.dA_window, "dA Spectrum")

        # Start the graph thread
        self.dls_window.start_probe_thread()

# Execute the entire GUI from a central location.
if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    # Initialize the worker thread
    worker = MeasurementWorker("", "StartUp", 0, 0, 'localhost', 9999)

    """These connections update the heatmap, and the two corresponding graphs."""
    worker.plot_row_update.connect(main_app.shot_delay_app.ta_widgets.update_row, Qt.QueuedConnection)
    worker.reset_currentMatrix.connect(main_app.shot_delay_app.ta_widgets.reset_currentMatrix, Qt.QueuedConnection)
    main_app.shot_delay_app.interface.parsed_content_signal.connect(main_app.shot_delay_app.ta_widgets.update_delay_stages, Qt.QueuedConnection)

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
    worker.update_delay_bar_signal.connect(main_app.shot_delay_app.interface.update_progress_bar)
    worker.update_ref_signal.connect(main_app.shot_delay_app.update_t0)
    main_app.dls_window.delay_bar_update.connect(main_app.shot_delay_app.update_current_delay)
    worker.current_step_signal.connect(main_app.shot_delay_app.update_current_step)
    main_app.dA_window.pos_change_signal.connect(main_app.shot_delay_app.update_current_delay)

    """This connection handles error messages from all applications/functions."""
    worker.error_occurred.connect(main_app.shot_delay_app.show_error_message)

    """This connection makes sure the stop button is pressable at the right time."""
    worker.stop_button.connect(main_app.shot_delay_app.interface.disable_stop_button)

    def start_process(argument):
        # Start the process if it doesn't yet exist. This makes sure that there is only one process at a time
        if worker.process is None:
            worker.process = QProcess()

        # Have the newest command be the one that is executed
        if worker.process.state() == QProcess.Running:
            print("Terminating existing process...")
            worker.process.terminate()
            worker.process.waitForFinished()

        # Make sure the commands are being ran in IronPython
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
                
            """These connections are for outputs; mostly used for debugging if you have errors."""
            worker.process.readyReadStandardOutput.connect(worker.handle_process_output)
            worker.process.readyReadStandardError.connect(worker.handle_process_error)
            worker.process.finished.connect(lambda: print("Process finished.", time.time()))

    worker.start_process_signal.connect(start_process)

    # Function to handle button presses instead of delaytime lists.
    def handle_button_press(content, orientation, shots, scans):
        print("Signal received")
        if len(content) == 1:
            content = content[0]
        worker.update_command(content, orientation, shots, scans)
        start_process(content)


    """These connections handle button presses and measurement starts."""
    main_app.dls_window.run_command_signal.connect(handle_button_press)
    main_app.shot_delay_app.interface.trigger_worker_run.connect(handle_button_press)
    main_app.dA_window.run_command_signal.connect(handle_button_press)
    main_app.shot_delay_app.interface.metadata_signal.connect(worker.update_metadata)


    """This function stops the worker thread when the GUI is closed."""
    def stop_worker():
        # Make sure that all signals are disconnected
        if worker.process:
            try:
                worker.process.readyReadStandardOutput.disconnect()
                worker.process.readyReadStandardError.disconnect()
                worker.process.finished.disconnect()
            except RuntimeError:
                print("Signals already disconnected.")

            # Make sure that the worker process isn't stopped prematurely
            if worker.process.state() == QProcess.Running:
                worker.process.terminate()
                worker.process.waitForFinished()

        worker.stop()
        # Stop the probe thread
        main_app.dls_window.stop_probe_thread() 

        # Process GUI events to keep updated and subsequently close the application
        QCoreApplication.processEvents()
        app.aboutToQuit.disconnect(stop_worker)
        app.quit()

    """This connects the stop button to the stop function for the worker thread."""
    main_app.shot_delay_app.interface.stop_measurement_signal.connect(stop_worker)

    # Start the worker thread
    worker.start()

    # When the GUI is closed execute stop_worker
    app.aboutToQuit.connect(stop_worker)

    # Start the application
    app.exec()
