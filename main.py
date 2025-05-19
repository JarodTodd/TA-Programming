import sys
from camera import *
import numpy as np

class ComputeData():

    def __init__(self):
        """
        #The probe_spectrum for the first functioning pixel is found by probespectrum[0][0]. 
        #The delta_a for the first funcioning pixel is found by delta_A_matrix[0][0]
        #The whole probe_spectrum or delta_A for the first measurement can be requestion by probe_sprectrum[0] or delta_A_matrix[0]
        """
        #stores the 2d arrays of each delay measurement
        self.blocks = []
        #stores the probe spectra of each delay measurement
        self.probe_spectrum_avg = []
        self.probe_spectrum_median = []
        #Stores the array of each delay delta_A
        self.delta_A_matrix_avg = []
        self.delta_A_matrix_median = []

        self.outlier_rejection = True

    def repeat_measurement(self):
        """
        Loops over all delay_stages 
        """
        number_of_shots = int(100)
        number_of_delays = int(5)

        for i in range(number_of_delays):
            block_buffer = camera(number_of_shots, i)
            block_2d_array = np.array(block_buffer).reshape(number_of_shots, 1088)
            self.blocks.append(block_2d_array)

    def reject_outliers(self, block, percentage=50, range_start = 0, range_end = None):
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
            # else:
            #     print("bad spectra found", flush=True)

        #Turn the list back into a NumPy array and return
        clean_block = np.array(good_shots)

        return clean_block

    def delta_a_block(self, block, start_pixel=12, end_pixel=1086, percentage = 110):
        #Boolean masks for pump state
        pump_off = block[block[:, 2] < 49152,  start_pixel:end_pixel]
        pump_on  = block[block[:, 2] >= 49152, start_pixel:end_pixel]
        # print(len(pump_off), len(pump_off))

        if self.outlier_rejection == True:
            pump_off = self.reject_outliers(pump_off, 110)
            pump_on = self.reject_outliers(pump_on, 110)

            # print(len(pump_off), len(pump_on))
        
        if len(pump_off) == 0 and len(pump_on) == 0:
            return None, None, None, None
        elif pump_off.size == 0:
            return None, None, None, None
            
        n_pairs = min(len(pump_off), len(pump_on))
        if n_pairs == 0:
            print("No pump-on/pump-off pairs found in this block.")
            pump_off_avg = np.mean(pump_off, axis=0)
            pump_off_median = np.median(pump_off, axis=0)

            self.probe_spectrum_avg.append(pump_off_avg)
            self.probe_spectrum_median.append(pump_off_median)
            zeros = np.zeros(end_pixel - start_pixel, dtype=float)
            self.delta_A_matrix_avg.append(zeros)
            self.delta_A_matrix_median.append(zeros)

            return self.probe_spectrum_avg, self.probe_spectrum_median, self.delta_A_matrix_avg, self.delta_A_matrix_median

        #Pair shots and compute delta A
        with np.errstate(divide='ignore', invalid='ignore'):
            delta_A = -np.log(np.divide(pump_on[:n_pairs], pump_off[:n_pairs]))

        #Average and median delta_A
        delta_A_avg = np.mean(delta_A, axis=0)
        delta_A_median = np.median(delta_A, axis=0)

        # Probe spectra from pump‑off state
        pump_off_avg = np.mean(pump_off, axis=0)
        pump_off_median = np.median(pump_off, axis=0)

        self.probe_spectrum_avg.append(pump_off_avg)
        self.probe_spectrum_median.append(pump_off_median)
        self.delta_A_matrix_avg.append(delta_A_avg)
        self.delta_A_matrix_median.append(delta_A_median)
        
        return self.probe_spectrum_avg, self.probe_spectrum_median, self.delta_A_matrix_avg, self.delta_A_matrix_median

    def display_probe(self, probe_spectrum):
        """
        Plots the probe_spectrum
        """
        plt.plot(probe_spectrum)
        plt.show()

# Run main()
if __name__ == "__main__":
    data_processor = ComputeData()
    print("aKESJf")
    data_processor.repeat_measurement()
    print("aa")
    data_processor.delta_a_block(data_processor.blocks[0])
    data_processor.delta_a_block(data_processor.blocks[1])

    print(data_processor.probe_spectrum_avg[1][28])
    print(data_processor.probe_spectrum_median[1][28])
    print(data_processor.delta_A_matrix_avg[1][28])
    print(data_processor.delta_A_matrix_median[1][28])
    data_processor.display_probe(data_processor.probe_spectrum_avg[1])