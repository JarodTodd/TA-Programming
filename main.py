import sys
from camera import *
import numpy as np

#stores the 2d arrays of each delay measurement
blocks = []
#stores the probe spectra of each delay measurement
probe_spectrum_avg = []
probe_spectrum_median = []
#Stores the array of each delay delta_A
delta_A_matrix_avg = []
delta_A_matrix_median = []

#The probe_spectrum for the first functioning pixel is found by probespectrum[0][0]. 
#The delta_a for the first funcioning pixel is found by delta_A_matrix[0][0]
#The whole probe_spectrum or delta_A for the first measurement can be requestion by probe_sprectrum[0] or delta_A_matrix[0]

def repeat_measurement():
    """
    Loops over all delay_stages 
    """
    number_of_shots = int(sys.argv[1])
    number_of_delays = int(sys.argv[2])

    for i in range(number_of_delays):
       block_buffer = camera(number_of_shots, i)
       block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
       blocks.append(block_2d_array)

def reject_outliers(block, percentage=50, range_start = 0, range_end = None):
    """
    Returns an array that contains only the rows
    whose average lies inside the chosen percentage bound
    around the mean.
    """

    if percentage >= 100:
        return np.array(block)
    if (range_end == None):
        block_region = block
    else:
        block_region = block[:,range_start:range_end]

    #Calculate overal average of the block
    average = np.mean(block_region)

    #Calculate the average of each row
    row_sums = np.sum(block_region, axis=1)
    row_averages = row_sums / len(block_region[0])

    #Create a list with acceptable rows
    allowed_deviation = (percentage / 100.0) * average
    good_shots = []
    for i, row in enumerate(block):
        if abs(row_averages[i] - average) <= allowed_deviation:
            good_shots.append(row)

    #Turn the list back into a NumPy array and return
    clean_block = np.array(good_shots)
    return clean_block

def delta_a_block(block, start_pixel=12, end_pixel=1086, percentage = 50):
    #Boolean masks for pump state
    pump_off = block[block[:, 2] < 49152,  start_pixel:end_pixel]
    pump_on  = block[block[:, 2] >= 49152, start_pixel:end_pixel]

    n_pairs = min(len(pump_off), len(pump_on))
    if n_pairs == 0:
        raise ValueError("No pump_off/pump_on pairs found.")

    #Pair shots and compute delta A
    with np.errstate(divide='ignore', invalid='ignore'):
        delta_A = -np.log(np.divide(pump_on[:n_pairs], pump_off[:n_pairs]))

    #Reject outlier delta A values
    delta_A_clean = reject_outliers(delta_A, percentage=percentage)

    #Average and median delta_A
    delta_A_avg = np.mean(delta_A_clean, axis=0)
    delta_A_median = np.median(delta_A_clean, axis=0)

    # Probe spectra from pump‑off state
    pump_off_avg = np.mean(pump_off, axis=0)
    pump_off_median = np.median(pump_off, axis=0)

    probe_spectrum_avg.append(pump_off_avg)
    probe_spectrum_median.append(pump_off_median)
    delta_A_matrix_avg.append(delta_A_avg)
    delta_A_matrix_median.append(delta_A_median)

    return probe_spectrum_avg, probe_spectrum_median, delta_A_matrix_avg, delta_A_matrix_median

def display_probe(probe_spectrum):
    """
    Plots the probe_spectrum
    """
    plt.plot(probe_spectrum)
    plt.show()

# Run main()
if __name__ == "__main__":
    repeat_measurement()
    delta_a_block(blocks[0])
    delta_a_block(blocks[1])
    print(probe_spectrum_avg[1][28])
    print(probe_spectrum_median[1][28])
    print(delta_A_matrix_avg[1][28])
    print(delta_A_matrix_median[1][28])