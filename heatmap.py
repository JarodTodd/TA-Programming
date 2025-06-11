import numpy as np
from dAwindow import *
import pyqtgraph as pg
from PySide6.QtCore import *
from PySide6.QtWidgets import QCheckBox
pg.setConfigOptions(useOpenGL=True, imageAxisOrder='row-major')


class TAPlotWidget(QObject):
    """
    This class creates and updates the heatmap and its secondary plots in the Main Window. 
    """

    def __init__(self, delay_times, pixel_indices, parent=None):
        super().__init__(parent)
        # add in __init__
        self.sync_from_hline = False
        self.sync_from_pixel = False

        # start data
        self.delay_times   = np.asarray(delay_times,  dtype=float)
        self.pixel_indices = np.asarray(pixel_indices, dtype=int)

        self.delta_A_matrix_current = np.zeros((self.delay_times.size, self.pixel_indices.size))
        self.delta_A_matrix_avg = np.zeros((self.delay_times.size, self.pixel_indices.size))
        self.mode          = "avg"
        self.active_matrix = self.delta_A_matrix_avg


        # HEATMAP
        self.canvas_heatmap = pg.PlotWidget(parent)
        self.delay_axis = pg.AxisItem(orientation='left')
        self.delay_axis.setStyle(showValues=False, tickLength=-5)
        self.delay_axis.setPen(None) 
        self.canvas_heatmap.setAxisItems({'left': self.delay_axis})
        self.canvas_heatmap.setLabels(left="Delay / ps", bottom="Pixel index")
        self.canvas_heatmap.getViewBox().setMouseEnabled(x=True, y=True)
        self.canvas_heatmap.setLimits(xMin=0, xMax=1024, yMin=-9000, yMax=9000)  

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
                           
        # cursor layout for the heatmap and secondary plots
        self.cursor_heatmap   = pg.mkPen('r', width=1)
        self.cursor_secondary = pg.mkPen('r', width=1)

        # cursor for the heatmap
        self.vline_heatmap = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_heatmap)
        self.hline_heatmap = pg.InfiniteLine(angle=0,  movable=True, pen=self.cursor_heatmap)
        self.canvas_heatmap.addItem(self.vline_heatmap)
        self.canvas_heatmap.addItem(self.hline_heatmap)
        self.vline_heatmap.setZValue(10)
        self.hline_heatmap.setZValue(10)
        self.vb = self.canvas_heatmap.getViewBox()


        # Secondary plots
        self.canvas_plot1 = HoverPlotWidget(parent)
        self.canvas_plot1.setLabels(left="ΔA", bottom="Delay / ps")
        self.canvas_plot1.setLimits(xMin=-8700, xMax=8700, yMin = -1, yMax=1)
        self.plot1_avg = self.canvas_plot1.plot([], [], pen=pg.mkPen('r', width=1), name="Avg")
        self.plot1_cur = self.canvas_plot1.plot([], [], pen=pg.mkPen(width=1), name="Current")
        self.vline_pl1 = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_secondary)
        self.canvas_plot1.addItem(self.vline_pl1)

        self.canvas_plot2 = HoverPlotWidget(parent)
        self.canvas_plot2.setLabels(left="ΔA", bottom="Pixel index")
        self.canvas_plot2.setLimits(xMin=0, xMax=1024, yMin=-1, yMax=1)
        self.plot2_avg = self.canvas_plot2.plot([], [], pen=pg.mkPen('r', width=2), name="Avg")
        self.plot2_cur = self.canvas_plot2.plot([], [], pen=pg.mkPen(width=1), name="Current")
        self.vline_pl2 = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_secondary)
        self.canvas_plot2.addItem(self.vline_pl2)

        # connect checkbox toggles to plot updates
        self.canvas_plot1._checkbox1.stateChanged.connect(self.update_secondary)
        self.canvas_plot1._checkbox2.stateChanged.connect(self.update_secondary)
        self.canvas_plot2._checkbox1.stateChanged.connect(self.update_secondary)
        self.canvas_plot2._checkbox2.stateChanged.connect(self.update_secondary)

        # enable average scan graph by default
        self.canvas_plot1._checkbox1.setChecked(True)
        self.canvas_plot1._checkbox2.setChecked(True)
        self.canvas_plot2._checkbox1.setChecked(True)
        self.canvas_plot2._checkbox2.setChecked(True)

        # Connections for interaction with the plots
        self.canvas_heatmap.scene().sigMouseClicked.connect(self.on_mouse_clicked)
        # dragging any of the 4 InfiniteLines keeps views in sync
        self.vline_heatmap.sigPositionChanged.connect(self.update_secondary)
        self.hline_heatmap.sigPositionChanged.connect(self.update_secondary)
        self.vline_pl1.sigPositionChanged.connect(self.on_delay_line_moved)
        self.vline_pl2.sigPositionChanged.connect(self.on_pixel_line_moved)

        self.delay_to_index = {float(d): i for i, d in enumerate(self.delay_times)}

        # first draw
        self.refresh_heatmap()

    def update_row(self, delay_time, row, scan):
        row_idx = (np.abs(self.delay_times - float(delay_time))).argmin()

        self.delta_A_matrix_current[row_idx, :] = row
        self.delta_A_matrix_avg[row_idx, :] = (self.delta_A_matrix_avg[row_idx, :] * (scan - 1) + row) / scan

        self.refresh_heatmap_update()
        self.update_secondary()

    def update_delay_stages(self, parsed_content):
        self.delay_times = np.sort(np.asarray(parsed_content, dtype=float))
        self.delay_to_index = {float(d): i for i, d in enumerate(self.delay_times)}

        nz = (self.delay_times.size, self.pixel_indices.size)
        self.delta_A_matrix_current = np.zeros(nz)
        self.active_matrix = self.delta_A_matrix_avg

        self.canvas_heatmap.setYRange(self.delay_times.min(), self.delay_times.max())
        self.canvas_heatmap.setLimits(xMin = 0, xMax = 1024, yMin = self.delay_times.min(), yMax = self.delay_times.max())
        self.canvas_plot1.setLimits(xMin = self.delay_times.min(), xMax = self.delay_times.max(), yMin= -1, yMax = 1)
        self.mesh.setRect(QRectF(self.pixel_indices.min(), self.delay_times.min(), self.pixel_indices.size, self.delay_times.max() - self.delay_times.min()))
        self.refresh_heatmap()
        self.update_delay_axis_labels()
    
    def update_delay_axis_labels(self):
        # Estimate the vertical step size
        n = len(self.delay_times)
        if n < 2:
            return

        y_positions = np.linspace(self.delay_times.min(), self.delay_times.max(), n, endpoint=False)
        dy = (self.delay_times.max() - self.delay_times.min()) / n
        tick_positions = y_positions + dy / 2

        # Create tick labels
        ticks = [(y, f"{t:.0f}") for y, t in zip(tick_positions, self.delay_times)]
        self.delay_axis.setTicks([ticks])


    # Internal helpers for plot interactions
    def on_mouse_clicked(self, mouse_event):
        if mouse_event.button() != Qt.LeftButton:
            return
        if not self.canvas_heatmap.sceneBoundingRect().contains(mouse_event.scenePos()):
            return
        x, y = self.vb.mapSceneToView(mouse_event.scenePos()).toTuple()
        self.vline_heatmap.setValue(x)
        self.hline_heatmap.setValue(y)
        self.update_secondary()
        mouse_event.accept()

    def on_delay_line_moved(self):
        # Update the horizontal line position based on the vertical line position
        if self.sync_from_hline:
            return

        # self.hline_heatmap.setValue(self.vline_pl1.value())
        y = self.vline_pl1.value()
        n = len(self.delay_times)
        dy = (self.delay_times.max() - self.delay_times.min()) / n
        tick_positions = np.linspace(self.delay_times.min(), self.delay_times.max(), n, endpoint=False) + dy / 2

        # Match click to tick position
        tick_idx = np.abs(tick_positions - y).argmin()
        matched_delay_value = self.delay_times[tick_idx]
        matched_tick_pos = tick_positions[tick_idx]
        self.hline_heatmap.setValue(matched_tick_pos)
        self.vline_pl1.setValue(matched_delay_value)


    def on_pixel_line_moved(self):
        if self.sync_from_pixel:
            return

        self.vline_heatmap.setValue(self.vline_pl2.value())

    def update_secondary(self):
        y = self.hline_heatmap.value()
        n = len(self.delay_times)
        dy = (self.delay_times.max() - self.delay_times.min()) / n
        tick_positions = np.linspace(self.delay_times.min(), self.delay_times.max(), n, endpoint=False) + dy / 2

        # Match click to tick position
        tick_idx = np.abs(tick_positions - y).argmin()
        matched_delay_value = self.delay_times[tick_idx]
        matched_tick_pos = tick_positions[tick_idx]
        
        pixel_idx = int(np.floor(self.vline_heatmap.value()))
        pixel_idx = int(np.clip(pixel_idx, self.pixel_indices.min(), self.pixel_indices.max())) # handles input out of bounds

        delay_idx = np.abs(self.delay_times - matched_delay_value).argmin()

        # Disable syncing while updating
        self.sync_from_hline = True 
        self.sync_from_pixel = True

        self.plot1_avg.setData(self.delay_times, self.delta_A_matrix_avg[:, pixel_idx])
        self.plot1_cur.setData(self.delay_times, self.delta_A_matrix_current[:, pixel_idx])
        self.canvas_plot1.setTitle(f"pixel: {pixel_idx}")
        self.vline_pl1.setValue(self.delay_times[delay_idx])

        self.plot2_avg.setData(self.pixel_indices, self.delta_A_matrix_avg[delay_idx, :])
        self.plot2_cur.setData(self.pixel_indices, self.delta_A_matrix_current[delay_idx, :])
        self.canvas_plot2.setTitle(f"delay: {self.delay_times[delay_idx]:g} ps")
        self.vline_pl2.setValue(pixel_idx)

        show_cur_1 = self.canvas_plot1._checkbox1.isChecked()
        show_avg_1 = self.canvas_plot1._checkbox2.isChecked()
        self.plot1_cur.setVisible(show_cur_1)
        self.plot1_avg.setVisible(show_avg_1)

        show_cur_2 = self.canvas_plot2._checkbox1.isChecked()
        show_avg_2 = self.canvas_plot2._checkbox2.isChecked()
        self.plot2_cur.setVisible(show_cur_2)
        self.plot2_avg.setVisible(show_avg_2)

        # Re-enable syncing
        self.sync_from_hline = False 
        self.sync_from_pixel = False

    def refresh_heatmap(self):
        if self.active_matrix.size == 0:
            print("No data to display.")
            return

        # compute levels for color scaling
        vmin, vmax = float(self.active_matrix.min()), float(self.active_matrix.max())
        if vmin == vmax:
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
        # compute levels for color scaling
        vmin, vmax = float(self.active_matrix.min()), float(self.active_matrix.max())
        if vmin == vmax:
            vmax = vmin + 1e-12

        # fastest update – send only the new Z (image) values
        self.mesh.setImage(self.active_matrix, autoLevels=False, autoRange=False)

        self.cbar.setLevels((vmin, vmax))

    def reset_heatmap(self):
        self.delta_A_matrix_current = np.zeros_like(self.delta_A_matrix_current)
        self.refresh_heatmap_update()
    
    
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