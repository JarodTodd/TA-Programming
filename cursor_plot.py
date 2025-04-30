import numpy as np
import matplotlib.pyplot as plt

vline_pl1 = None
vline_pl2 = None
vline_heatmap_mv =None
hline_heatmap_mv = None
vline_heatmap =None
hline_heatmap = None
draggable_line =None
drag_status = 0
draggable_pltline = None

def kinetic_cursor(delay_times, pixel_indexes, delta_A_matrix):


    # Create figures
    fig, (ax_heatmap, ax_plot1, ax_plot2) = plt.subplots(3, 1, figsize=(8, 9), gridspec_kw={'height_ratios': [2, 1, 1]})

    # Heatmap
    c = ax_heatmap.pcolormesh(pixel_indexes, delay_times, delta_A_matrix, shading='auto')
    ax_heatmap.set_title("TA heatmap")
    ax_heatmap.set_xlabel("Pixel index")
    ax_heatmap.set_ylabel("Delay time")
    fig.colorbar(c, ax=ax_heatmap, label="ΔA")

    # Plot1
    plot1, = ax_plot1.plot([], [], marker='o')
    ax_plot1.set_xlabel("Delay time")
    ax_plot1.set_ylabel("ΔA at pixel")
    ax_plot1.set_xlim(np.min(delay_times), np.max(delay_times))
    ax_plot1.set_ylim(np.min(delta_A_matrix), np.max(delta_A_matrix))

    # Plot2
    plot2, = ax_plot2.plot([], [], marker='o')
    ax_plot2.set_xlabel("Pixel index")
    ax_plot2.set_ylabel("ΔA at pixel")
    ax_plot2.set_xlim(np.min(pixel_indexes), np.max(pixel_indexes))
    ax_plot2.set_ylim(np.min(delta_A_matrix), np.max(delta_A_matrix))

    #Updates the secondary plots 
    def secondary_plots_update():
        global vline_pl1, vline_pl2

        if vline_heatmap is None or hline_heatmap is None:
            return                       # nothing to show yet

        # Find the values that the two red lines define 
        pixel_value = int(round(vline_heatmap.get_xdata()[0]))
        delay_val   = hline_heatmap.get_ydata()[0]
        delay_idx   = int(np.abs(delay_times - delay_val).argmin())

        # Updates the data in the secondary plots
        plot1.set_data(delay_times, delta_A_matrix[:, pixel_value])
        ax_plot1.set_title(f"pixel {pixel_value}")

        plot2.set_data(pixel_indexes, delta_A_matrix[delay_idx, :])
        ax_plot2.set_title(f"delay {delay_times[delay_idx]:g}")

        # Update grey guide lines
        if vline_pl1 is not None:
            vline_pl1.remove()
        if vline_pl2 is not None:
            vline_pl2.remove()

        vline_pl1 = ax_plot1.axvline(delay_times[delay_idx], color="lightgrey")
        vline_pl2 = ax_plot2.axvline(pixel_value,           color="lightgrey")

        fig.canvas.draw_idle()



    def cursor_moving(event):
        if drag_status == 1:
            return
        
        global vline_heatmap_mv
        global hline_heatmap_mv
        global hline_heatmap
        global draggable_line

        # If the cursor is outside the heatmap, remove the position pointer
        if event.inaxes is not ax_heatmap:
            if vline_heatmap_mv is not None:
                vline_heatmap_mv.remove()
                vline_heatmap_mv = None
            if hline_heatmap_mv is not None:
                hline_heatmap_mv.remove()
                hline_heatmap_mv = None
            fig.canvas.draw_idle()
            return
        
        pixel_value = event.xdata
        delay_value = event.ydata

        if vline_heatmap_mv is not None:
            vline_heatmap_mv.remove()
        if hline_heatmap_mv is not None:
            hline_heatmap_mv.remove()

        # Draw new vertical line and save reference
        hline_heatmap_mv = ax_heatmap.axhline(delay_value, color="salmon")
        vline_heatmap_mv = ax_heatmap.axvline(pixel_value, color="salmon")

        # Determine if the line is draggable
        if hline_heatmap is not None and hline_heatmap_mv is not None:
            if abs(hline_heatmap.get_ydata()[0]-hline_heatmap_mv.get_ydata()[0]) < 0.1 and abs(vline_heatmap.get_xdata()[0]-vline_heatmap_mv.get_xdata()[0]) < 0.1:
                draggable_line = 'hv'
            elif abs(vline_heatmap.get_xdata()[0]-vline_heatmap_mv.get_xdata()[0]) < 0.1:
                draggable_line = 'v'
            elif abs(hline_heatmap.get_ydata()[0]-hline_heatmap_mv.get_ydata()[0]) < 0.1:
                draggable_line = 'h'
            elif abs(vline_heatmap.get_xdata()[0]-vline_heatmap_mv.get_xdata()[0]) < 0.1:
                draggable_line = 'v'
            else:
                draggable_line = None

        fig.canvas.draw_idle()


    def cursor_position(event):
        if event.inaxes is not ax_heatmap:
            return
        global draggable_line
        if draggable_line is not None:
            return
        
        global vline_heatmap
        global hline_heatmap
        
        pixel_value = int(round(event.xdata))

        #https://www.geeksforgeeks.org/find-the-nearest-value-and-the-index-of-numpy-array/
        delay_value = event.ydata
        delay_idx = int(np.abs(delay_times - delay_value).argmin())

        if vline_heatmap is not None:
            vline_heatmap.remove()
        if hline_heatmap is not None:
            hline_heatmap.remove()

        # Draw new line and save reference
        hline_heatmap = ax_heatmap.axhline(delay_times[delay_idx], color="red")
        vline_heatmap = ax_heatmap.axvline(pixel_value, color="red")

        secondary_plots_update()

    # Removes the position pointer when dragging is acive
    def drag(event):
        if draggable_line is None:
            return
        
        global vline_heatmap_mv, hline_heatmap_mv, drag_status

        drag_status = 1

        if vline_heatmap_mv is not None:
            vline_heatmap_mv.remove()
            vline_heatmap_mv = None
        if hline_heatmap_mv is not None:
            hline_heatmap_mv.remove()
            hline_heatmap_mv = None

    def drag_do(event):
        if drag_status == 0:
            return
        if event.inaxes is not ax_heatmap:
            return
        
        global vline_heatmap
        global hline_heatmap

        if vline_heatmap is None or hline_heatmap is None:
            return
        
        pixel_value = int(round(event.xdata))

        #https://www.geeksforgeeks.org/find-the-nearest-value-and-the-index-of-numpy-array/
        delay_value = event.ydata
        delay_idx = int(np.abs(delay_times - delay_value).argmin())

        if vline_heatmap is not None and draggable_line == 'v':
            vline_heatmap.set_xdata([pixel_value, pixel_value])
        if hline_heatmap is not None and draggable_line == 'h':
            hline_heatmap.set_ydata([delay_times[delay_idx], delay_times[delay_idx]])
        if hline_heatmap is not None and vline_heatmap is not None and draggable_line == 'hv':
            vline_heatmap.set_xdata([pixel_value, pixel_value])
            hline_heatmap.set_ydata([delay_times[delay_idx], delay_times[delay_idx]])
        secondary_plots_update() # update the secondary charts

        # Draw new line and save reference
        fig.canvas.draw_idle()

    #Stops the dragging actions when button is released
    def drag_stop(event):

        global drag_status, draggable_pltline
        
        drag_status = 0
        draggable_pltline = None

    def drag_secondairy_plots(event):
        if event.inaxes is not ax_plot1 and event.inaxes is not ax_plot2:
            return
        
        global vline_pl1, vline_pl2, draggable_pltline
        
        x = event.xdata

        if event.inaxes is ax_plot1:
            if vline_pl1 is not None and abs(vline_pl1.get_xdata()[0]-x) < 0.01:
                draggable_pltline = 'plt1'
        elif event.inaxes is ax_plot2:
            if vline_pl2 is not None and abs(vline_pl2.get_xdata()[0]-x) < 0.1:
                draggable_pltline = 'plt2'

    def drag_secondary_do(event):
        global vline_heatmap, hline_heatmap

        if draggable_pltline is None:
            return
        if event.inaxes not in [ax_plot1, ax_plot2]:
            return

        x = event.xdata

        if draggable_pltline == 'plt1':  # moving delay time
            delay_idx = int(np.abs(delay_times - x).argmin())
            if hline_heatmap is not None:
                hline_heatmap.set_ydata([delay_times[delay_idx], delay_times[delay_idx]])

        elif draggable_pltline == 'plt2':  # moving pixel index
            pixel_value = int(round(x))
            if vline_heatmap is not None:
                vline_heatmap.set_xdata([pixel_value, pixel_value])

        secondary_plots_update()
        fig.canvas.draw_idle()


    # Start events
    # cid = fig.canvas.mpl_connect('button_press_event', secondary_plots)
    cid = fig.canvas.mpl_connect('motion_notify_event', cursor_moving)
    cid = fig.canvas.mpl_connect('button_press_event', cursor_position)
    cid = fig.canvas.mpl_connect('button_press_event', drag)
    cid = fig.canvas.mpl_connect('button_release_event', drag_stop)
    cid = fig.canvas.mpl_connect('motion_notify_event', drag_do)
    cid = fig.canvas.mpl_connect('motion_notify_event', drag_secondairy_plots)
    cid = fig.canvas.mpl_connect('motion_notify_event', drag_secondary_do)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":

    delay_times = np.array([-0.2, 0.0, 0.2, 0.5, 1.0])
    pixel_indexes = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    delta_A_matrix_start = np.zeros((len(delay_times), len(pixel_indexes)))
    delta_A_matrix = np.array([
        [0.001, 0.002, 0.001, 0.000, -0.001, -0.002, -0.001, 0.000, 0.001, 0.002],
        [0.002, 0.003, 0.002, 0.001,  0.000, -0.001, -0.002, -0.001, 0.000, 0.001],
        [0.003, 0.004, 0.003, 0.002,  0.001,  0.000, -0.001, -0.002, -0.001, 0.000],
        [0.004, 0.005, 0.004, 0.003,  0.002,  0.001,  0.000, -0.001, -0.002, -0.001],
        [0.005, 0.006, 0.005, 0.004,  0.003,  0.002,  0.001,  0.000, -0.001, -0.002],
    ])
    probe_spectrum = np.array([1000, 1005, 1010, 1008, 1002, 995, 990, 993, 998, 1001])

    secondary_plot_updates = kinetic_cursor(delay_times, pixel_indexes, delta_A_matrix_start)      

    for i, row in enumerate(delta_A_matrix):
        delta_A_matrix_start[i, :] = delta_A_matrix[i, :]
        kinetic_cursor(delay_times, pixel_indexes, delta_A_matrix_start)
