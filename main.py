import sys
from camera import *
import numpy as np

def repeat_measurement():
    number_of_shots = int(sys.argv[1])
    number_of_delays = int(sys.argv[2])

    blocks = []
    for i in range(number_of_delays):
       block_buffer = camera(number_of_shots, i)
       
       block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)

       blocks.append(block_2d_array)
    
    return blocks

# Collects the data from one picture in a given range for a given block. Standard range is the full length 
def get_picture(block, scan_idx, start_pixel = 0, end_pixel = 1088):
    PIXEL = 1088
    start = scan_idx * PIXEL + start_pixel
    end = scan_idx * PIXEL + end_pixel

    scan_result = block[scan_idx, start:end]
    return scan_result

# Calculates the delta A for each pixel of a given block in the given range
def delta_a_block(block, start_pixel = 12, end_pixel = 1086):
    PIXEL = 1088
    pump_off = []
    pump_on = []

    for i in range(int(sys.argv[1])):
        if block[i, 2] < 49152:
            pump_off.append(block[i, start_pixel: end_pixel])
        else:
            pump_on.append(block[i, start_pixel: end_pixel])

    avg_pump_off = np.mean(pump_off, axis=0)  # Average across rows (scans) for pump_off

    avg_pump_on = np.mean(pump_on, axis=0)  # Average across rows (scans) for pump_on

    # Print or return the results (optional)
    print(f"Avg Pump Off: {avg_pump_off}")
    print(f"Avg Pump On: {avg_pump_on}")

    with np.errstate(divide='ignore', invalid='ignore'):
        delta_A_block = -np.log(np.divide(avg_pump_on, avg_pump_off))

    
    print(delta_A_block)


# Run main()
if __name__ == "__main__":
    blocks = repeat_measurement()
    delta_a_block(blocks)