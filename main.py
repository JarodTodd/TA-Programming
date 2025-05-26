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
        self.deviation_threshold = 100

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

    def reject_outliers(self, block1, block2 = None , range_start = 0, range_end = None):
        """
        Returns an array that contains only the rows
        whose average lies inside the chosen percentage bound
        around the mean.
        """
        if block2 == None:
            block1 = np.array(block1)

            if self.deviation_threshold >= 100 or self.outlier_rejection == False:
                return np.array(block1)
            else:
                block_region = block1[:,range_start:range_end]

            #Calculate overal average of the block
            average = np.mean(block_region)

            #Calculate the average of each row
            row_sums = np.sum(block_region, axis=1)
            row_averages = row_sums / len(block_region[0])

            #Create a list with acceptable rows
            allowed_deviation = (self.deviation_threshold / 100.0) * average
            good_shots = []
            for i, row in enumerate(block1):
                if abs(row_averages[i] - average) <= allowed_deviation:
                    good_shots.append(row)
                # else:
                #     print("bad spectra found", flush=True)

            #Turn the list back into a NumPy array and return
            clean_block = np.array(good_shots)

            return clean_block
        
        else:
            block1 = np.array(block1)
            block2 = np.array(block2)

            if percentage >= 100 or self.outlier_rejection == False:
                return np.array(block1), np.array(block2)
            else:
                block1_region = block1[:,range_start:range_end]
                block2_region = block2[:,range_start:range_end]

            #Calculate overal average
            block1_average = np.mean(block1_region)
            block2_average = np.mean(block2_region)

            #Calculate the average of each row
            block1_row_sums = np.sum(block1_region, axis=1)
            block1_row_averages = block1_row_sums / len(block1_region[0])

            block2_row_sums = np.sum(block2_region, axis=1)
            block2_row_averages = block2_row_sums / len(block2_region[0])

            #Allowed deviation
            block1_allowed_deviation = (self.deviation_threshold / 100.0) * block1_average
            block2_allowed_deviation = (self.deviation_threshold / 100.0) * block2_average

            # Identify rejected row indices
            block1_rejected_rows = []
            for i, row in enumerate(block1):
                if abs(block1_row_averages[i] - block1_average) > block1_allowed_deviation:
                    block1_rejected_rows.append(i)
            block2_rejected_rows = []
            for i, row in enumerate(block2):
                if abs(block2_row_averages[i] - block2_average) > block2_allowed_deviation:
                   block2_rejected_rows.append(i)

            # combined_rejected = list(set(block1_rejected_rows + block2_rejected_rows))

            for item in block2_rejected_rows:
                if item in range(len(block1)) and item not in block1_rejected_rows:
                    block1_rejected_rows.append(item)
            for item in block1_rejected_rows:
                if item in range(len(block2)) and item not in block2_rejected_rows:
                    block2_rejected_rows.append(item)

            #Turn the list back into a NumPy array and return
            block1_clean = np.delete(block1, block1_rejected_rows, axis=0)
            block2_clean = np.delete(block2, block2_rejected_rows, axis=0)


            return block1_clean, block2_clean
        
    def toggle_outlier_rejection(self, selected):
        self.outlier_rejection = selected

    def deviation_change(self, value: int):
        self.deviation_threshold = value


    def delta_a_block(self, block, start_pixel=12, end_pixel=1086, percentage = 110):
        #Boolean masks for pump state
        pump_off = block[block[:, 2] < 49152,  start_pixel:end_pixel]
        pump_on  = block[block[:, 2] >= 49152, start_pixel:end_pixel]
        # print(len(pump_off), len(pump_off))

        if self.outlier_rejection == True:
            pump_off = self.reject_outliers(pump_off)
            pump_on = self.reject_outliers(pump_on)

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