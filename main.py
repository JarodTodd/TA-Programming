import sys
from camera import *
import numpy as np

#stores the 2d arrays of each delay measurement
blocks = []
#stores the probe spectra of each delay measurement
probe_spectrum = []
#Stores the array of each delay delta_A
delta_A_matrix = []

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

    #Splits the mshots based on pump_off/pump_on state
    for i in range(int(sys.argv[1])):
        if block[i, 2] < 49152:
            pump_off.append(block[i, start_pixel: end_pixel])
        else:
            pump_on.append(block[i, start_pixel: end_pixel])

    #Calculates the probe spectrum
    avg_pump_off = np.mean(pump_off, axis=0)  
    probe_spectrum.append(avg_pump_off)
    # Calculates avg_pump_on across rows
    avg_pump_on = np.mean(pump_on, axis=0)

    #calculates delta A
    with np.errstate(divide='ignore', invalid='ignore'):
        delta_A_block = -np.log(np.divide(avg_pump_on, avg_pump_off))

    # Save delta A
    delta_A_matrix.append(delta_A_block)

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
    print(probe_spectrum[0][0])
    print(delta_A_matrix[1][28])