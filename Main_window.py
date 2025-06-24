from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from WorkerThread import *
from HeatmapWindow import *
from Probewindow import *
from dAwindow import *
from error_popup import *
import time

# Paths of the IronPython parts; command prompt file and our command file
ironpython_executable = r"C:\Users\PC032230\Documents\GitHub\TA-Programming\IronPython 3.4.2\net462\ipy.exe"
script_path = r"C:\Users\PC032230\Documents\GitHub\TA-Programming\IronPythonDLS.py"

class MainApp(QMainWindow):
    """
    Main application window for TA Measurements.
    This class initializes the main GUI window, sets up the tabbed interface,
    and manages the integration of sub-windows for different application features:
    - Main Window (HeatmapWindow)
    - Probe Spectrum (DLSW)
    - dA Spectrum (dA_Window)
    It also starts a background thread to update the probe spectrum in real time.
    Attributes:
        tabs (QTabWidget): The main tab widget containing all sub-windows.
        dA_window (dA_Window): The window for dA Spectrum analysis.
        probe_window (Probe_Window): The window for Probe Spectrum analysis.
        heatmap_window (Heatmap_Window): The main window for heatmap visualization.

    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HamburgerPresserWorks (tm)")
        self.setWindowIcon(QIcon("hamburger.ico"))

        # Set up main tab widget and sub-windows
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.dA_window = dAwindow()
        self.probe_window = Probewindow(self.dA_window)
        self.heatmap_window = Heatmapwindow(self.probe_window, self.dA_window)

        # Add application tabs
        self.tabs.addTab(self.heatmap_window, "Heat map Window")
        self.tabs.addTab(self.probe_window, "Probe Window")
        self.tabs.addTab(self.dA_window, "dA Window")

        # Start background thread for probe spectrum updates
        self.probe_window.start_graph_thread()

        # Show maximized after all widgets are set up
        self.showMaximized()

# Execute the entire GUI from a central location
if __name__ == "__main__":
    app = QApplication([])
    main_app = MainApp()
    main_app.show()
    main_app.setWindowIcon(QIcon("hamburger.ico"))


    # Initialize worker thread for measurements and communication
    worker = MeasurementWorker("", "StartUp", 0, 0, 'localhost', 9999)

    # --- Signal connections for updating UI and data ---

    # Update heatmap and graphs when new data arrives
    worker.plot_row_update.connect(main_app.heatmap_window.ta_widgets.update_row, Qt.QueuedConnection)
    worker.reset_currentMatrix.connect(main_app.heatmap_window.ta_widgets.reset_currentMatrix, Qt.QueuedConnection)
    main_app.heatmap_window.interface.parsed_content_signal.connect(main_app.heatmap_window.ta_widgets.update_delay_stages, Qt.QueuedConnection)

    # Control probe spectrum thread and update probe data during measurements
    worker.started.connect(main_app.probe_window.stop_graph_thread, Qt.QueuedConnection)
    worker.update_probe.connect(main_app.probe_window.update_probe_data, Qt.QueuedConnection)
    worker.finished.connect(main_app.probe_window.start_graph_thread, Qt.QueuedConnection)
  
    # Keep dA spectrum updated in dAWindow
    main_app.probe_window.graph_worker.dA_update.connect(main_app.dA_window.update_dA_graph, Qt.QueuedConnection)
    worker.update_dA.connect(main_app.dA_window.update_dA_graph, Qt.QueuedConnection)

    # Update delay sliders, progress bars, and reference time
    worker.update_delay_bar_signal.connect(main_app.heatmap_window.update_current_delay)
    worker.update_delay_bar_signal.connect(main_app.probe_window.update_delay_bar)
    worker.update_ref_signal.connect(main_app.heatmap_window.update_t0)
    main_app.probe_window.delay_bar_update.connect(main_app.heatmap_window.update_current_delay)
    worker.current_step_signal.connect(main_app.heatmap_window.update_current_step)
    main_app.dA_window.pos_change_signal.connect(main_app.heatmap_window.update_current_delay)

    # Display error messages from any part of the application
    worker.error_occurred.connect(show_error_message)

    # Enable/disable stop button appropriately
    worker.stop_button.connect(main_app.heatmap_window.interface.disable_stop_button)

    # --- Process management for IronPython commands ---

    def start_process(argument):
        """
        Start or restart the IronPython process with the given argument.
        Ensures only one process runs at a time.
        """
        if worker.process is None:
            worker.process = QProcess()

        # Terminate any running process before starting a new one
        if worker.process.state() == QProcess.Running:
            print("Terminating existing process...")
            worker.process.terminate()
            worker.process.waitForFinished()

        worker.process.setProgram(ironpython_executable)

        if isinstance(argument, list):
            # If argument is a list, start the worker thread (used for batch operations)
            worker.data_processor.dark_noise_correction = main_app.probe_window.dark_noise #set dark noise level in the data_processor
            worker.start()
        elif isinstance(argument, str):
            # If argument is a string, run the IronPython script with the argument
            worker.process.setArguments([script_path, argument])
            worker.process.start()

            # Disconnect previous finished signal if necessary
            if worker.process and worker.process.state() == QProcess.Running:
                try:
                    worker.process.finished.disconnect()
                except RuntimeError:
                    print("Signal 'finished' was already disconnected or not connected.")

            # Connect process output/error for debugging
            worker.process.readyReadStandardOutput.connect(worker.handle_process_output)
            worker.process.readyReadStandardError.connect(worker.handle_process_error)
            worker.process.finished.connect(lambda: print("Process finished.", time.time()))

    worker.start_process_signal.connect(start_process)

    # Function to handle button presses instead of delaytime lists
    def handle_button_press(content, orientation, shots, scans):
        """
        Handle measurement button presses, update worker command, and start process.
        """
        if len(content) == 1:
            content = content[0]
        if content == "GoToReference":
            main_app.heatmap_window.update_current_delay(main_app.heatmap_window.t_0)
        worker.update_command(content, orientation, shots, scans)
        start_process(content)

    # Connect measurement start signals from all relevant UI components
    main_app.probe_window.run_command_signal.connect(handle_button_press)
    main_app.heatmap_window.interface.trigger_worker_run.connect(handle_button_press)
    main_app.dA_window.run_command_signal.connect(handle_button_press)
    main_app.heatmap_window.interface.metadata_signal.connect(worker.update_metadata)

    # this function calls the set_wavelength_mapping for both the Heatmap window and the Probe window.
    def set_wavelength_calibration(wavelengths, unit):
        main_app.heatmap_window.ta_widgets.set_wavelength_mapping(wavelengths, unit)
        main_app.probe_window.set_wavelength_mapping(wavelengths, unit)
        worker.wavelength_change(wavelengths)

    #connect the wavelength popup window with the heatmap plots
    main_app.heatmap_window.interface.wavelengthpopup.wavelength_signal.connect(set_wavelength_calibration, Qt.QueuedConnection)
    
    def stop_worker():
        """
        Cleanly stop the worker thread and any running processes when the GUI closes.
        """

        worker.stop()

        # Disconnect process signals and terminate process if running
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


        # Stop probe spectrum thread
        main_app.probe_window.stop_graph_thread()

        # Process remaining GUI events and quit application
        QCoreApplication.processEvents()
        app.aboutToQuit.disconnect(stop_worker)
        app.quit()

    """This connects the stop button to the stop function for the worker thread."""
    main_app.heatmap_window.interface.stop_measurement_signal.connect(lambda: worker.stop())

    # Start the worker thread
    worker.start()

    # Ensure worker and threads are stopped when application exits
    app.aboutToQuit.connect(stop_worker)

    # Run the application
    app.exec()
