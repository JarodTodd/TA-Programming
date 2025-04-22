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

def delta_a_block(block, start_pixel = 12, end_pixel = 1086):
    """
    Splits the shots based on pump_off/pump_on state
    and calcutates the probe spectrum and delta A for a given block
    """
    pump_off = []
    pump_on = []
    print(len(block))
    #Splits the mshots based on pump_off/pump_on state
    for i in range(len(block)):
        if block[i, 2] < 49152:
            pump_off.append(block[i, start_pixel: end_pixel])
        else:
            pump_on.append(block[i, start_pixel: end_pixel])

    #Calculates average pump_off and pump_on across rows
    pump_off_avg = np.mean(pump_off, axis=0)  
    pump_on_avg = np.mean(pump_on, axis=0)
    #Calculates median pump_off and pump_on across rows
    pump_off_median = np.median(pump_off, axis=0)
    pump_on_median = np.median(pump_on, axis = 0)

    #Append probe_spectrum
    probe_spectrum_avg.append(pump_off_avg)
    probe_spectrum_median.append(pump_off_median)

    #Calculates delta A
    with np.errstate(divide='ignore', invalid='ignore'):
        delta_A_avg = -np.log(np.divide(pump_on_avg, pump_off_avg))
        delta_A_median = -np.log(np.divide(pump_on_median, pump_off_median))

    # Save delta A
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