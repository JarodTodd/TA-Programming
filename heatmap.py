import numpy as np
from dAwindow import *
import pyqtgraph as pg
from PySide6.QtCore import *
from PySide6.QtWidgets import QCheckBox
pg.setConfigOptions(useOpenGL=True, imageAxisOrder='row-major')

class ScaledAxis(pg.AxisItem):
    """
    AxisItem that, when `self.values` is None, shows raw x-values;
    otherwise rounds each tick to an int, clips to [0..len(values)-1],
    and uses values[idx] as the label.
    """
    def __init__(self, orientation="bottom"):
        super().__init__(orientation=orientation)
        self.values = None

    def set_values(self, array):
        """Supply a 1D array / list of physical values, same length as pixels."""
        self.values = np.asarray(array, float)
        # force a redraw by pyqtgrap
        self.update()

    def clear_values(self):
        """Returns to pixel labeling."""
        self.values = None
        self.update()

    def tickStrings(self, tick_positions, scale, spacing):
        """Sets pixel or wavelength ticks"""
        x = np.asarray(tick_positions)
        if self.values is None: # no wavelenghts lavel each tick by pixel
            labels = x
        else: # apply pixel to wavelength transformation
            idx = np.clip(np.rint(x).astype(int), 0, len(self.values)-1)
            labels = self.values[idx]
        return [f"{v:.0f}" for v in labels]


class TAPlotWidget(QObject):
    """
    This class creates and updates the heatmap and its secondary plots in the Main Window. 
    """

    def __init__(self, delay_times, pixel_indices, parent=None):
        """
        Creates both the Heatmap and secondary plots 
        and does an initial draw.
        Result is a heatmap filled with zeros that is visible in the GUI
        """
        super().__init__(parent)
        
        self.sync_from_hline = False
        self.sync_from_pixel = False

        #pixel to wavelenght calibration
        self.wavelenghts = None

        # data at inital heatmap draw
        self.delay_times   = np.asarray(delay_times,  dtype=float)
        self.pixel_indices = np.asarray(pixel_indices, dtype=int)

        # create matrixes that hold data for the current scan and average over all scans
        self.delta_A_matrix_current = np.zeros((self.delay_times.size, self.pixel_indices.size))
        self.delta_A_matrix_avg = np.zeros((self.delay_times.size, self.pixel_indices.size))
        self.mode          = "Average of all scans"
        self.active_matrix = self.delta_A_matrix_avg

        # cursor layout for the heatmap and secondary plots
        self.cursor_heatmap   = pg.mkPen('r', width=1)
        self.cursor_secondary = pg.mkPen('r', width=1)


        #==Heatmap creation===
        self.canvas_heatmap = pg.PlotWidget(parent)
        self.delay_axis = pg.AxisItem(orientation='left')
        self.delay_axis.setStyle(showValues=False, tickLength=-5)
        self.delay_axis.setPen(None)

        # wavelength calibration
        self.heatmap_wavelength_axis = ScaledAxis(orientation='bottom')
        self.canvas_heatmap.setAxisItems({'left': self.delay_axis, 'bottom': self.heatmap_wavelength_axis}) 

        # bottom axis: start in pixel units
        self.canvas_heatmap.setLabels(left="Delay / ps", bottom="Pixel index")
        self.canvas_heatmap.getViewBox().setMouseEnabled(x=True, y=True)
        self.canvas_heatmap.setLimits(xMin=0, xMax=1024, yMin=-0, yMax=1)
 
        # create heatmap ImageItem
        self.mesh = pg.ImageItem(self.active_matrix, axisOrder='row-major')
        self.mesh.setRect(QRectF(self.pixel_indices.min(), self.delay_times.min(),self.pixel_indices.size, self.delay_times.max() - self.delay_times.min()))
        cmap = pg.colormap.get('viridis')
        self.mesh.setColorMap(cmap)
        self.mesh.setZValue(0)  
        self.canvas_heatmap.addItem(self.mesh)

        # create a color bar (requires pyqtgraph ≥ 0.13.1)
        plot_item = self.canvas_heatmap.getPlotItem()  
        self.cbar = pg.ColorBarItem(values=(0, 1))
        self.cbar.setColorMap(cmap)
        self.cbar.setImageItem(self.mesh) 
        plot_item.layout.addItem(self.cbar, 2, 2)     

        # create cursor for the heatmap
        self.vline_heatmap = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_heatmap)
        self.hline_heatmap = pg.InfiniteLine(angle=0,  movable=True, pen=self.cursor_heatmap)
        self.canvas_heatmap.addItem(self.vline_heatmap)
        self.canvas_heatmap.addItem(self.hline_heatmap)
        self.vline_heatmap.setZValue(10)
        self.hline_heatmap.setZValue(10)
        self.vb = self.canvas_heatmap.getViewBox()


        #==Secondary plots creation==
        # plot1
        self.canvas_plot1 = HoverPlotWidget(parent)
        self.canvas_plot1.setLabels(left="ΔA", bottom="Delay / ps")
        self.canvas_plot1.setLimits(xMin=-8700, xMax=8700, yMin = -1, yMax=1)
        self.plot1_avg = self.canvas_plot1.plot([], [], pen=pg.mkPen('r', width=1), name="Avg")
        self.plot1_cur = self.canvas_plot1.plot([], [], pen=pg.mkPen(width=1), name="Current")

        # plot2
        self.canvas_plot2 = HoverPlotWidget(parent)

        # wavelength calibration
        self.plot2_wavelength_axis = ScaledAxis(orientation='bottom')
        self.canvas_plot2.setAxisItems({'bottom': self.plot2_wavelength_axis})

        self.canvas_plot2.setLabels(left="ΔA", bottom="Pixel index")
        self.canvas_plot2.setLimits(xMin=0, xMax=1024, yMin=-1, yMax=1)
        self.plot2_avg = self.canvas_plot2.plot([], [], pen=pg.mkPen('r', width=1), name="Avg")
        self.plot2_cur = self.canvas_plot2.plot([], [], pen=pg.mkPen(width=1), name="Current")

        # add plots their vertical cursors
        self.vline_pl1 = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_secondary)
        self.vline_pl2 = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_secondary)
        self.canvas_plot1.addItem(self.vline_pl1)
        self.canvas_plot2.addItem(self.vline_pl2)

        # connect checkbox toggles to plot updates
        self.canvas_plot1._checkbox1.stateChanged.connect(self.update_secondary)
        self.canvas_plot1._checkbox2.stateChanged.connect(self.update_secondary)
        self.canvas_plot2._checkbox1.stateChanged.connect(self.update_secondary)
        self.canvas_plot2._checkbox2.stateChanged.connect(self.update_secondary)

        # initially make both the average and current scan visible 
        self.canvas_plot1._checkbox1.setChecked(True)
        self.canvas_plot1._checkbox2.setChecked(True)
        self.canvas_plot2._checkbox1.setChecked(True)
        self.canvas_plot2._checkbox2.setChecked(True)

        # Connections for interaction with the plots
        self.canvas_heatmap.scene().sigMouseClicked.connect(self.on_mouse_clicked)
        # draggin any of the 4 cursor lines keeps them in sync
        self.vline_heatmap.sigPositionChanged.connect(self.update_secondary)
        self.hline_heatmap.sigPositionChanged.connect(self.update_secondary)
        self.vline_pl1.sigPositionChanged.connect(self.on_delay_line_moved)
        self.vline_pl2.sigPositionChanged.connect(self.on_pixel_line_moved)

        #determines the positions of the delay times in the delta_a_matrices
        self.delay_to_index = {float(d): i for i, d in enumerate(self.delay_times)}

        # first draw
        self.refresh_heatmap()


    """Helper functions that update and display data"""

    def set_mode(self, mode: str):
        """
        Sets the correct selection from the combobox above the heatmap
        """
        if mode not in ("Current scan", "Average of all scans"):
            raise ValueError("mode must be 'current scan' or 'average of all scans'")
        self.mode = mode
        self.active_matrix = (self.delta_A_matrix_current if mode == "Current scan" else self.delta_A_matrix_avg)
        self.refresh_heatmap()

    def update_row(self, delay_time, row, scan):
        """
        New data from a measurement is set to the correct rows in the delta_A matrixes
        """

        # determine the correct row index to place the data in 
        row_idx = (np.abs(self.delay_times - float(delay_time))).argmin()

        # update the correct rows in the delta_A matrices
        self.delta_A_matrix_current[row_idx, :] = row
        self.delta_A_matrix_avg[row_idx, :] = (self.delta_A_matrix_avg[row_idx, :] * (scan - 1) + row) / scan

        # update the heatmap and secondary plots to display the new values
        self.refresh_heatmap_update()
        self.update_secondary()

    def update_delay_stages(self, parsed_content):
        """
        The size of the delta_A matrices and the heatmap depend on the number of delay stages given by the user in the GUI.
        This function updates the matrices and heatmap to have the correct sizes and positions. 
        """

        # sort delay stages and save their corresponding position index
        self.delay_times = np.sort(np.asarray(parsed_content, dtype=float))
        self.delay_to_index = {float(d): i for i, d in enumerate(self.delay_times)}

        # set the delta_A matrices to the correct size
        nz = (self.delay_times.size, self.pixel_indices.size)
        self.delta_A_matrix_current = np.zeros(nz)
        self.delta_A_matrix_avg = np.zeros(nz)
        self.active_matrix = self.delta_A_matrix_avg

        # set the heatmap to the correct size and limits
        self.canvas_heatmap.setYRange(self.delay_times.min(), self.delay_times.max())
        self.canvas_heatmap.setLimits(xMin = 0, xMax = 1024, yMin = self.delay_times.min(), yMax = self.delay_times.max())
        self.canvas_plot1.setLimits(xMin = self.delay_times.min(), xMax = self.delay_times.max(), yMin= -1, yMax = 1)
        self.mesh.setRect(QRectF(self.pixel_indices.min(), self.delay_times.min(), self.pixel_indices.size, self.delay_times.max() - self.delay_times.min()))

        # refresh heatmap 
        self.refresh_heatmap()
        # create correct axis ticks for the heatmap
        self.update_delay_axis_labels()
    
    def update_delay_axis_labels(self):
        """
        Updates the tick positions and labels for the delay axis in the heatmap based given delay times.
        This function ensures tick labels are centered within their corresponding intervals,
        """
        # determine number of delays
        n = len(self.delay_times)
        if n < 2:
            return

        # create n evenly spaced positions from min to max delay times
        y_positions = np.linspace(self.delay_times.min(), self.delay_times.max(), n, endpoint=False)
        
        # calculate the verticle spacing between ticks
        dy = (self.delay_times.max() - self.delay_times.min()) / n

        # shift each y position to the center of its interval
        tick_positions = y_positions + dy / 2

        # create a list of (position, label) pairs for tick marks
        ticks = [(y, f"{t:.0f}") for y, t in zip(tick_positions, self.delay_times)]
        
        # Apply the computed ticks to the delay axis
        self.delay_axis.setTicks([ticks])

    def update_secondary(self):
        """
        Updates secondary plots
        """

        # get the ycoordinate (delay) from the horizontal line on the heatmap
        y = self.hline_heatmap.value()

        # calculate tick positions centered within each delay interval
        n = len(self.delay_times)
        dy = (self.delay_times.max() - self.delay_times.min()) / n
        tick_positions = np.linspace(self.delay_times.min(), self.delay_times.max(), n, endpoint=False) + dy / 2

        # find the index of the tick closest to the selected y value
        tick_idx = np.abs(tick_positions - y).argmin()
        matched_delay_value = self.delay_times[tick_idx]
        matched_tick_pos = tick_positions[tick_idx]
        
        # get the selected x coordinate (pixel index) from the vertical line on the heatmap
        pixel_idx = int(np.floor(self.vline_heatmap.value()))
        pixel_idx = int(np.clip(pixel_idx, self.pixel_indices.min(), self.pixel_indices.max()))

        # find delay index that most closely matches the selected delay value
        delay_idx = np.abs(self.delay_times - matched_delay_value).argmin()

        # prevent feedback loops during this update
        self.sync_from_hline = True 
        self.sync_from_pixel = True

        # update plot 1: delay dependent spectra at selected pixel index
        self.plot1_avg.setData(self.delay_times, self.delta_A_matrix_avg[:, pixel_idx])
        self.plot1_cur.setData(self.delay_times, self.delta_A_matrix_current[:, pixel_idx])
        self.vline_pl1.setValue(self.delay_times[delay_idx])
        if self.wavelenghts is None:
            self.canvas_plot1.setTitle(f"pixel: {pixel_idx}")
        else:
            wavelength = self.wavelenghts[pixel_idx]
            self.canvas_plot1.setTitle(f"λ: {float(wavelength):.0f} nm")

        # update plot 2: pixel dependent spectra at selected delay index
        self.plot2_avg.setData(self.pixel_indices, self.delta_A_matrix_avg[delay_idx, :])
        self.plot2_cur.setData(self.pixel_indices, self.delta_A_matrix_current[delay_idx, :])
        self.canvas_plot2.setTitle(f"delay: {self.delay_times[delay_idx]:g} ps")
        self.vline_pl2.setValue(pixel_idx)

        # updates visibility of current and average plots for plot1 based on the checkbox
        show_cur_1 = self.canvas_plot1._checkbox1.isChecked()
        show_avg_1 = self.canvas_plot1._checkbox2.isChecked()
        self.plot1_cur.setVisible(show_cur_1)
        self.plot1_avg.setVisible(show_avg_1)

        # updates visibility of current and average plots for plot2 based on the checkbox
        show_cur_2 = self.canvas_plot2._checkbox1.isChecked()
        show_avg_2 = self.canvas_plot2._checkbox2.isChecked()
        self.plot2_cur.setVisible(show_cur_2)
        self.plot2_avg.setVisible(show_avg_2)

        # re-enable syncing
        self.sync_from_hline = False 
        self.sync_from_pixel = False

    def refresh_heatmap(self):
        """
        Refreshes the heatmap display by clearing old data and redrawing the active matrix.
        """

        # check if there is any data to display
        if self.active_matrix.size == 0:
            print("No data to display.")
            return

        # compute color scale bounds from the data range
        vmin, vmax = float(self.active_matrix.min()), float(self.active_matrix.max())
        if vmin == vmax:
            # avoid zero range for color scaling
            vmax = vmin + 1e-12

        # remove old mesh if it exists
        if self.mesh in self.canvas_heatmap.items():
            self.canvas_heatmap.removeItem(self.mesh)

        # create new image item
        self.mesh = pg.ImageItem(self.active_matrix, axisOrder='row-major')
        self.mesh.setRect(QRectF(self.pixel_indices.min(), self.delay_times.min(), self.pixel_indices.size, self.delay_times.max() - self.delay_times.min()))
        cmap = pg.colormap.get('viridis')
        self.mesh.setColorMap(cmap)
        self.mesh.setZValue(0)
        self.canvas_heatmap.addItem(self.mesh)

        # update color bar
        self.cbar.setImageItem(self.mesh)
        self.cbar.setLevels((vmin, vmax))
        self.update_delay_axis_labels()

    def refresh_heatmap_update(self):
        """
        Efficiently updates the heatmap image with new data values, avoiding full redraw.
        This method is used for fast updates.
        """

        # compute color scale bounds from the data range
        vmin, vmax = float(self.active_matrix.min()), float(self.active_matrix.max())
        if vmin == vmax:
            # avoid zero range for color scaling
            vmax = vmin + 1e-12

        # fast update: replace only the image data (Z-values), no geometry or layout recalculations
        self.mesh.setImage(self.active_matrix, autoLevels=False, autoRange=False)

        # update the color bar limits to reflect the new data range
        self.cbar.setLevels((vmin, vmax))

    def reset_currentMatrix(self):
        self.delta_A_matrix_current = np.zeros_like(self.delta_A_matrix_current)

        if self.mode == "Current scan":
            self.active_matrix = self.delta_A_matrix_current
        else: 
            self.active_matrix = self.delta_A_matrix_avg

        self.refresh_heatmap()
        self.update_secondary


    """Helper functions for plot interactions"""

    def on_mouse_clicked(self, mouse_event):
        """
        Handles left mouse clicks on the heatmap
        When the user clicks inside the heatmap area, this function updates
        the vertical and horizontal cursors and refreshes the linked secondary plots.
        """

        # only respond to left click events
        if mouse_event.button() != Qt.LeftButton:
            return
        # ignore the click if it's outside the heatmap canvas
        if not self.canvas_heatmap.sceneBoundingRect().contains(mouse_event.scenePos()):
            return
        
        # Convert the mouse position from the click to coordinates
        x, y = self.vb.mapSceneToView(mouse_event.scenePos()).toTuple()

        # move the heatmap cursors to the clicked position
        self.vline_heatmap.setValue(x)
        self.hline_heatmap.setValue(y)

        # update secondary plots based on new crosshair positions
        self.update_secondary()

        mouse_event.accept()

    def on_delay_line_moved(self):
        """
        Syncs the horizontal line (delay) on the heatmap with the vertical line in the delay plot.
        This is triggered when the delay crosshair in plot1 is moved, ensuring the heatmap reflects the change.
        Avoids recursive updates using the `sync_from_hline` variable.
        """

        # prevent updates if already syncing from a heatmap interaction
        if self.sync_from_hline:
            return

        try:

            # get the new y position from the delay plot crosshair
            y = self.vline_pl1.value()

            # compute tick positions centered within delay intervals
            n = len(self.delay_times)
            dy = (self.delay_times.max() - self.delay_times.min()) / n
            tick_positions = np.linspace(self.delay_times.min(), self.delay_times.max(), n, endpoint=False) + dy / 2

            # find the tick position closest to the crosshair value
            tick_idx = np.abs(tick_positions - y).argmin()
            matched_delay_value = self.delay_times[tick_idx]
            matched_tick_pos = tick_positions[tick_idx]

            # update the heatmap horizontal line to match the delay plot
            self.hline_heatmap.setValue(matched_tick_pos)

            # snaps the delay plot crosshair to the exact matched delay value
            self.vline_pl1.blockSignals(True)
            self.vline_pl1.setValue(matched_delay_value)
            self.vline_pl1.blockSignals(False)

            # update secondary plots with correct values
            self.update_secondary()

        finally:
            self.sync_from_hline = False


    def on_pixel_line_moved(self):
        """
        Syncs the vertical line (pixel index) on the heatmap with the vertical line in the pixel plot.
        Triggered when the pixel crosshair in plot2 is moved.
        Avoids recursive updates using the `sync_from_hline` variable.
        """
         
        # prevent updates if already syncing from a heatmap interaction
        if self.sync_from_pixel:
            return

        # update the vertical line on the heatmap to match the pixel plot
        self.vline_heatmap.setValue(self.vline_pl2.value())

        # update secondary plots with correct values
        self.update_secondary()

    """Helper functions: wavelenght calibration"""
    def set_wavelength_mapping(self, wavelengths, label="Wavelength / nm"):
        """
        Switch both x-axes to show `wavelengths[i]` at pixel i.
        """
        self.wavelenghts = wavelengths
        
        self.heatmap_wavelength_axis.set_values(wavelengths)
        self.plot2_wavelength_axis.set_values(wavelengths)
        self.canvas_heatmap.setLabel('bottom', label)
        self.canvas_plot2.setLabel('bottom', label)
        self.update_secondary()        # refresh titles, cursors, etc.

    def reset_to_pixel_axis(self, label="Pixel index"):
        """
        Drop the wavelength lookup, back to raw pixel numbers.
        """

        self.wavelenghts = None

        self.heatmap_wavelength_axis.clear_values()
        self.plot2_wavelength_axis.clear_values()
        self.canvas_heatmap.setLabel('bottom', label)
        self.canvas_plot2.setLabel('bottom', label)
        self.update_secondary()


# ========= HoverPlotWidget Class =========
    
class HoverPlotWidget(pg.PlotWidget):
    """
    A PlotWidget that displays two checkboxes when the mouse hovers over
    the top-right corner of the plot.
    """

    def __init__(self, *args, margin=10, spacing = 4, **kwargs):
        # create the checkboxes before super().__init__
        self._checkbox1 = QCheckBox("Current Scan")
        self._checkbox1.hide()
        self._checkbox2 = QCheckBox("Average of all scans")
        self._checkbox2.hide()

        # control spacing
        self._margin = margin   # spacing from plot
        self._spacing = spacing # spacing between boxes

        super().__init__(*args, **kwargs)
        # parent it and enable mouse tracking
        self._checkbox1.setParent(self)
        self._checkbox2.setParent(self)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        """
        Shows checkboxes when mouse hovers over the top-right corner of the plot.
        The hover sensitive area is defined based on the size of the checkboxes,
        and they are positioned with specified margins and spacing.
        """
        # Get the current width of the widget
        widget_width = self.width()

        # Divine checkboxes
        cb1 = self._checkbox1
        cb2 = self._checkbox2

        # Determine the maximum width and height needed for checkbox layout
        cb_width = max(cb1.sizeHint().width(), cb2.sizeHint().width())
        cb_height = max(cb1.sizeHint().height(), cb2.sizeHint().height())

        # compute checkbox positions
        x0 = widget_width - cb_width - self._margin
        y0 = self._margin

        cb1.move(x0, y0)
        cb2.move(x0, y0 + cb_height + self._spacing)

        cb1.show()
        cb2.show()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """
        This function hides the checkboxes when the mouse leaves a plot
        """
        self._checkbox1.hide()
        self._checkbox2.hide()
        super().leaveEvent(event)