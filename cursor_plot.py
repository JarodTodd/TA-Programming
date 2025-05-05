# ta_widget.py
import sys
import numpy as np
import matplotlib.pyplot as plt

from PySide6.QtCore    import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg


class TAPlotWidget(QWidget):

    def __init__(self, delay_times, pixel_indexes, parent=None):
        super().__init__(parent)

        # experiment data
        self.delay_times    = np.asarray(delay_times)
        self.pixel_indexes  = np.asarray(pixel_indexes)
        self.delta_A_matrix = np.zeros((delay_times.size, pixel_indexes.size))

        # create figure area 
        self.canvas = FigureCanvasQTAgg(plt.Figure(figsize=(8, 9)))
        self.fig    = self.canvas.figure
        self.ax_heatmap, self.ax_plot1, self.ax_plot2 = (
            self.fig.subplots(
                3, 1,
                gridspec_kw={"height_ratios": [2, 1, 1]},
            )
        )
        lay = QVBoxLayout(self)
        lay.addWidget(self.canvas)

        # create heatmap
        self.c = self.ax_heatmap.pcolormesh(
            self.pixel_indexes,
            self.delay_times,
            self.delta_A_matrix,
            shading="auto",
        )
        self.fig.colorbar(self.c, ax=self.ax_heatmap, label="ΔA")
        self.ax_heatmap.set(
            title="TA heat‑map",
            xlabel="Pixel index",
            ylabel="Delay time",
        )

        # create secondary plots 
        (self.plot1,) = self.ax_plot1.plot([], [], marker="o")
        self.ax_plot1.set(
            xlabel="Delay time",
            ylabel="ΔA at pixel",
            xlim=(self.delay_times.min(), self.delay_times.max()),
            ylim=(self.delta_A_matrix.min(), self.delta_A_matrix.max()),
        )

        (self.plot2,) = self.ax_plot2.plot([], [], marker="o")
        self.ax_plot2.set(
            xlabel="Pixel index",
            ylabel="ΔA at delay",
            xlim=(self.pixel_indexes.min(), self.pixel_indexes.max()),
            ylim=(self.delta_A_matrix.min(), self.delta_A_matrix.max()),
        )

        # state variables for verticle and horizontal lines
        self.vline_heatmap = self.hline_heatmap = None
        self.vline_cursor  = self.hline_cursor  = None
        self.vline_pl1 = self.vline_pl2 = None
        self.draggable_line = None
        self.drag_status = 0
        self.draggable_pltline = None

        # Matplotlib events
        self.canvas.mpl_connect("motion_notify_event", self.cursor)
        self.canvas.mpl_connect("button_press_event",  self.position_pointer)
        self.canvas.mpl_connect("button_press_event",  self.drag_heatmap_enable)
        self.canvas.mpl_connect("button_release_event", self.drag_stop)
        self.canvas.mpl_connect("motion_notify_event", self.drag_heatmap_do)
        self.canvas.mpl_connect("button_press_event", self.drag_secondairy_enable)
        self.canvas.mpl_connect("motion_notify_event", self.drag_secondary_do)

        self.fig.tight_layout()

    # update delta_A matrix and refresh plots
    def update_row(self, row_idx: int, new_values):
        self.delta_A_matrix[row_idx, :] = new_values

        # update heatmap
        self.c.set_array(self.delta_A_matrix.ravel())
        self.c.autoscale()

        # update secondary plot y‑limits
        self.ax_plot1.set_ylim(self.delta_A_matrix.min(), self.delta_A_matrix.max())
        self.ax_plot2.set_ylim(self.delta_A_matrix.min(), self.delta_A_matrix.max())

        self.fig.canvas.draw_idle()

    # update secondary plots when heatmap cross-hair is moved
    def secondary_plots_update(self):
        if self.vline_heatmap is None or self.hline_heatmap is None:
            return

        pixel_value = int(round(self.vline_heatmap.get_xdata()[0]))
        delay_val   = self.hline_heatmap.get_ydata()[0]
        delay_idx   = int(np.abs(self.delay_times - delay_val).argmin())

        # update secondary plots
        self.plot1.set_data(self.delay_times, self.delta_A_matrix[:, pixel_value])
        self.ax_plot1.set_title(f"pixel {pixel_value}")

        self.plot2.set_data(self.pixel_indexes, self.delta_A_matrix[delay_idx, :])
        self.ax_plot2.set_title(f"delay {self.delay_times[delay_idx]:g}")

        # update vertical lines in secondary plots
        if self.vline_pl1:
            self.vline_pl1.remove()
        if self.vline_pl2:
            self.vline_pl2.remove()
        self.vline_pl1 = self.ax_plot1.axvline(self.delay_times[delay_idx], color="lightgrey")
        self.vline_pl2 = self.ax_plot2.axvline(pixel_value, color="lightgrey")

        self.fig.canvas.draw_idle()

    # current position of the mouse cursor for the heatmap
    def cursor(self, event):
        if self.drag_status:
            return
        # remove cursor if not in heatmap
        if event.inaxes is not self.ax_heatmap:
            if self.vline_cursor :
                self.vline_cursor .remove()
                self.vline_cursor  = None
            if self.hline_cursor :
                self.hline_cursor .remove()
                self.hline_cursor  = None
            self.fig.canvas.draw_idle()
            return

        pixel_value = event.xdata
        delay_value = event.ydata

        # redraw cursor lines
        if self.vline_cursor :
            self.vline_cursor .remove()
        if self.hline_cursor :
            self.hline_cursor .remove()
        self.hline_cursor  = self.ax_heatmap.axhline(delay_value, color="salmon")
        self.vline_cursor  = self.ax_heatmap.axvline(pixel_value, color="salmon")

        # decide if a position line is draggable
        if (self.hline_heatmap and self.vline_heatmap and
            abs(self.hline_heatmap.get_ydata()[0] - delay_value) < 0.1 and
            abs(self.vline_heatmap.get_xdata()[0] - pixel_value)   < 0.1):
            self.draggable_line = "hv"
        elif self.vline_heatmap and abs(self.vline_heatmap.get_xdata()[0] - pixel_value) < 0.1:
            self.draggable_line = "v"
        elif self.hline_heatmap and abs(self.hline_heatmap.get_ydata()[0] - delay_value) < 0.1:
            self.draggable_line = "h"
        else:
            self.draggable_line = None

        self.fig.canvas.draw_idle()

    # draw cross-hair lines on heatmap for selected pixel and delay
    def position_pointer(self, event):
        if event.inaxes is not self.ax_heatmap or self.draggable_line:
            return

        pixel_value = int(round(event.xdata))
        delay_value = event.ydata
        delay_idx   = int(np.abs(self.delay_times - delay_value).argmin())

        # draw cross-hair lines when new pixel or delay is selected
        if self.vline_heatmap:
            self.vline_heatmap.remove()
        if self.hline_heatmap:
            self.hline_heatmap.remove()
        self.hline_heatmap = self.ax_heatmap.axhline(self.delay_times[delay_idx], color="red")
        self.vline_heatmap = self.ax_heatmap.axvline(pixel_value, color="red")

        # update secondary plots for new pixel and delay values
        self.secondary_plots_update()

    # enable dragging for heatmap on mouse-button press
    def drag_heatmap_enable(self, event):
        if not self.draggable_line or event.inaxes is not self.ax_heatmap:
            return
        
        # activate drag_status and remove cursor lines
        self.drag_status = 1
        if self.vline_cursor :
            self.vline_cursor .remove()
            self.vline_cursor  = None
        if self.hline_cursor :
            self.hline_cursor .remove()
            self.hline_cursor  = None

    # updates cross-hair when dragged over plot
    def drag_heatmap_do(self, event):
        if not self.drag_status or event.inaxes is not self.ax_heatmap:
            return

        pixel_value = int(round(event.xdata))
        delay_value = event.ydata
        delay_idx   = int(np.abs(self.delay_times - delay_value).argmin())

        # update cross-hair 
        if self.vline_heatmap is not None and self.draggable_line == 'v':
            self.vline_heatmap.set_xdata([pixel_value, pixel_value])
        if self.hline_heatmap is not None and self.draggable_line == 'h':
            self.hline_heatmap.set_ydata([delay_times[delay_idx], delay_times[delay_idx]])
        if self.hline_heatmap is not None and self.vline_heatmap is not None and self.draggable_line == 'hv':
            self.vline_heatmap.set_xdata([pixel_value, pixel_value])
            self.hline_heatmap.set_ydata([delay_times[delay_idx], delay_times[delay_idx]])

        self.secondary_plots_update()
        self.fig.canvas.draw_idle()

    # determine if and which verticle lines in secondary plots are draggable
    def drag_secondairy_enable(self, event):
        x = event.xdata
        if event.inaxes is self.ax_plot1:
            if self.vline_pl1 is not None and abs(self.vline_pl1.get_xdata()[0] - x) < 0.01:
                self.draggable_pltline = "plt1"
        elif event.inaxes is self.ax_plot2:
            if self.vline_pl2 is not None and abs(self.vline_pl2.get_xdata()[0] - x) < 0.1:
                self.draggable_pltline = "plt2"
        else:
            self.draggable_pltline = None

    #updates verticle line of secondary plots when dragged
    def drag_secondary_do(self, event):
        if self.draggable_pltline is None:
            return
        if event.inaxes not in [self.ax_plot1, self.ax_plot2]:
            return

        x = event.xdata

        # determine which verticle line of the secondary plots is draggable
        if self.draggable_pltline == "plt1":  # dragging delay time marker
            delay_idx = int(np.abs(self.delay_times - x).argmin())
            if self.hline_heatmap is not None:
                self.hline_heatmap.set_ydata([self.delay_times[delay_idx]] * 2)
        elif self.draggable_pltline == "plt2":  # dragging pixel index marker
            pixel_value = int(round(x))
            if self.vline_heatmap is not None:
                self.vline_heatmap.set_xdata([pixel_value] * 2)

        self.secondary_plots_update()

    # stop dragging when mouse button is released
    def drag_stop(self, _event):
        self.drag_status = 0
        self.draggable_line = None
        self.draggable_pltline = None

if __name__ == "__main__":
    delay_times   = np.array([-0.2, 0.0, 0.2, 0.5, 1.0])
    pixel_indexes = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    app = QApplication(sys.argv)
    win = QMainWindow()
    widget = TAPlotWidget(delay_times, pixel_indexes)
    win.setCentralWidget(widget)
    win.resize(900, 850)
    win.show()

    # simulate one new measurement row per 10 second 
    def _fake_measurement():
        zeros = np.where(np.all(widget.delta_A_matrix == 0, axis=1))[0]
        if zeros.size:
            row = zeros[0]
            widget.update_row(
                row,
                np.random.uniform(-0.002, 0.006, size=pixel_indexes.size),
            )
        else:
            timer.stop()   # all rows filled ‑‑ stop the demo

    timer = QTimer()
    timer.timeout.connect(_fake_measurement)
    timer.start(10000)  # 1 s per fake cycle

    app.exec()
