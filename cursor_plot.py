import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import *
from dAwindow import *
pg.setConfigOptions(useOpenGL=True, imageAxisOrder='row-major')


class TAPlotWidget(QObject):

    def __init__(self, delay_times, pixel_indices, parent=None):
        super().__init__(parent)
        self.dA_window = dA_Window()

        # start data
        self.delay_times   = np.asarray(delay_times,  dtype=float)
        self.pixel_indices = np.asarray(pixel_indices, dtype=int)

        self.delta_A_matrix_avg = np.zeros((self.delay_times.size, self.pixel_indices.size))
        self.delta_A_matrix_med = np.zeros((self.delay_times.size, self.pixel_indices.size))
        self.mode          = "avg"
        self.active_matrix = self.delta_A_matrix_avg


        # HEATMAP
        self.canvas_heatmap = pg.PlotWidget(parent)
        self.delay_axis = pg.AxisItem(orientation='left')
        self.canvas_heatmap.setAxisItems({'left': self.delay_axis})
        self.canvas_heatmap.setLabels(left="Delay / ps", bottom="Pixel index")
        self.canvas_heatmap.getViewBox().setMouseEnabled(x=False, y=False)  

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
        self.cbar.setLevels((0, 1))
        plot_item.layout.addItem(self.cbar, 2, 2)     
                           
        # cursor layout for the heatmap and secondary plots
        self.cursor_heatmap   = pg.mkPen('r', width=1)
        self.cursor_secondary = pg.mkPen('lightgray', width=1)

        # cursor for the heatmap
        self.vline_heatmap = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_heatmap)
        self.hline_heatmap = pg.InfiniteLine(angle=0,  movable=True, pen=self.cursor_heatmap)
        self.canvas_heatmap.addItem(self.vline_heatmap)
        self.canvas_heatmap.addItem(self.hline_heatmap)
        self.vline_heatmap.setZValue(10)
        self.hline_heatmap.setZValue(10)
        self.vb = self.canvas_heatmap.getViewBox()


        # Secondary plots
        self.canvas_plot1 = pg.PlotWidget(parent)
        self.canvas_plot1.setLabels(left="ΔA at pixel", bottom="Delay / ps")
        self.plot1 = self.canvas_plot1.plot([], [])
        self.vline_pl1 = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_secondary)
        self.canvas_plot1.addItem(self.vline_pl1)
        self.canvas_plot1.scene().sigMouseClicked.connect(lambda event: self.dA_window.on_click(event, self.canvas_plot1))

        self.canvas_plot2 = pg.PlotWidget(parent)
        self.canvas_plot2.setLabels(left="ΔA at delay", bottom="Pixel index")
        self.plot2 = self.canvas_plot2.plot([], [])
        self.vline_pl2 = pg.InfiniteLine(angle=90, movable=True, pen=self.cursor_secondary)
        self.canvas_plot2.addItem(self.vline_pl2)
        self.canvas_plot2.scene().sigMouseClicked.connect(lambda event: self.dA_window.on_click(event, self.canvas_plot2))
        

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


    # External helper functions
    def set_mode(self, mode: str):
        if mode not in ("avg", "med"):
            raise ValueError("mode must be 'avg' or 'med'")
        self.mode = mode
        self.active_matrix = (self.delta_A_matrix_avg if mode == "avg" else self.delta_A_matrix_med)
        self.refresh_heatmap()

    def update_row(self, delay_time, row_avg, row_med):
        row_idx = (np.abs(self.delay_times - float(delay_time))).argmin()
        self.delta_A_matrix_avg[row_idx, :] = row_avg
        self.delta_A_matrix_med[row_idx, :] = row_med
        self.active_matrix[row_idx, :] = (row_avg if self.mode == "avg" else row_med)
        self.refresh_heatmap_update()

    def update_delay_stages(self, parsed_content):
        self.delay_times = np.sort(np.asarray(parsed_content, dtype=float))
        self.delay_to_index = {float(d): i for i, d in enumerate(self.delay_times)}

        nz = (self.delay_times.size, self.pixel_indices.size)
        self.delta_A_matrix_avg = np.zeros(nz)
        self.delta_A_matrix_med = np.zeros_like(self.delta_A_matrix_avg)
        self.active_matrix = (self.delta_A_matrix_avg if self.mode == "avg" else self.delta_A_matrix_med)

        self.canvas_heatmap.setYRange(self.delay_times.min(), self.delay_times.max())
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
        self.hline_heatmap.setValue(self.vline_pl1.value())

    def on_pixel_line_moved(self):
        self.vline_heatmap.setValue(self.vline_pl2.value())

    def update_secondary(self):
        pixel_idx = int(round(self.vline_heatmap.value()))
        pixel_idx = int(np.clip(pixel_idx, self.pixel_indices.min(), self.pixel_indices.max())) # handles input out of bounds

        delay_val = self.hline_heatmap.value()
        delay_idx = np.abs(self.delay_times - delay_val).argmin()

        self.plot1.setData(self.delay_times, self.active_matrix[:, pixel_idx])
        self.canvas_plot1.setTitle(f"pixel {pixel_idx}")
        self.vline_pl1.setValue(self.delay_times[delay_idx])

        self.plot2.setData(self.pixel_indices, self.active_matrix[delay_idx, :])
        self.canvas_plot2.setTitle(f"delay {self.delay_times[delay_idx]:g}")
        self.vline_pl2.setValue(pixel_idx)

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
        # fastest update – send only the new Z (image) values
        self.mesh.setImage(self.active_matrix, autoLevels=False, autoRange=False)

    
    
