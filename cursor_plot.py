import numpy as np
import matplotlib.pyplot as plt

delay_times = np.array([-0.2, 0.0, 0.2, 0.5, 1.0])
pixel_indexes = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

delta_A_matrix = np.array([
    [0.001, 0.002, 0.001, 0.000, -0.001, -0.002, -0.001, 0.000, 0.001, 0.002],
    [0.002, 0.003, 0.002, 0.001,  0.000, -0.001, -0.002, -0.001, 0.000, 0.001],
    [0.003, 0.004, 0.003, 0.002,  0.001,  0.000, -0.001, -0.002, -0.001, 0.000],
    [0.004, 0.005, 0.004, 0.003,  0.002,  0.001,  0.000, -0.001, -0.002, -0.001],
    [0.005, 0.006, 0.005, 0.004,  0.003,  0.002,  0.001,  0.000, -0.001, -0.002],
])

probe_spectrum = np.array([1000, 1005, 1010, 1008, 1002, 995, 990, 993, 998, 1001])

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

vline_pl1 = None
vline_pl2 = None
# Updates every mouse movement
def move_cursor(event):
    if event.inaxes is not ax_heatmap:
        return
    if event.xdata is None or event.ydata is None:
        return

    global vline_pl1
    global vline_pl2

    pixel_value = int(round(event.xdata))
    
    #https://www.geeksforgeeks.org/find-the-nearest-value-and-the-index-of-numpy-array/
    delay_value = event.ydata
    delay_idx = int(np.abs(delay_times - delay_value).argmin())

    delta_A_values_pixel = delta_A_matrix[:, pixel_value]
    delta_A_values_delay = delta_A_matrix[delay_idx, :]

    #update charts 
    plot1.set_data(delay_times, delta_A_values_pixel)
    plot2.set_data(pixel_indexes, delta_A_values_delay)

    ax_plot1.set_title(f"chart specific for pixel: {pixel_value}")
    ax_plot2.set_title(f"chart specific for delay time: {delay_times[delay_idx]}")

    if vline_pl1 is not None:
        vline_pl1.remove()
    if vline_pl2 is not None:
        vline_pl2.remove()

    # Draw new vertical line and save reference
    vline_pl1 = ax_plot1.axvline(delay_times[delay_idx], color="lightgrey")
    vline_pl2 = ax_plot2.axvline(pixel_value, color="lightgrey")

    fig.canvas.draw_idle()

vline_heatmap_mv =None
hline_heatmap_mv = None
def cursor_moving(event):
    if event.inaxes is not ax_heatmap:
        return
    
    global vline_heatmap_mv
    global hline_heatmap_mv
    
    pixel_value = event.xdata
    delay_value = event.ydata

    if vline_heatmap_mv is not None:
        vline_heatmap_mv.remove()
    if hline_heatmap_mv is not None:
        hline_heatmap_mv.remove()

    # Draw new vertical line and save reference
    hline_heatmap_mv = ax_heatmap.axhline(delay_value, color="salmon")
    vline_heatmap_mv = ax_heatmap.axvline(pixel_value, color="salmon")

    fig.canvas.draw_idle()

vline_heatmap =None
hline_heatmap = None
def cursor_position(event):
    if event.inaxes is not ax_heatmap:
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


# Start events
cid = fig.canvas.mpl_connect('button_press_event', move_cursor)
cid = fig.canvas.mpl_connect('motion_notify_event', cursor_moving)
cid = fig.canvas.mpl_connect('button_press_event', cursor_position)

plt.tight_layout()
plt.show()