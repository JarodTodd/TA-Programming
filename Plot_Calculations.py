from camera import *
import numpy as np

class ComputeData():
    """
    Class to compute the probe spectra, dA spectra and handle outlier rejection.
    """

    def __init__(self):
        # Initialize variables for delta_a_block
        self.blocks = None
        self.probe_spectrum = None
        self.delta_A = None

        # Initialize variables for outlier rejection
        self.outlier_rejection_dA = False      # toggle outlier rejection on/off
        self.outlier_rejection_probe = False

        self.deviation_threshold_dA = 100      # deviation threshold for outlier rejection in %
        self.deviation_threshold_probe = 100

        self.range_start_dA = 0                # start pixel for outlier rejection range
        self.range_start_probe = 0
        self.range_end_dA = 1023               # end pixel for outlier rejection range
        self.range_end_probe = 1023
    
        self.rejected_dA = 0                   # percentage of rejected shots
        self.rejected_probe = 0

        self.dark_noise_correction = None

    def OutlierRejection_probe(self, block, range_start: int | None = None, range_end:   int | None = None):
        """
        Rejects outliers for the real-time probe specrtra in the DLSWindow. 
        """
        block = np.asarray(block)

        if self.deviation_threshold_probe >= 100:
            return block
        
        # Get rejection range
        range_start = self.range_start_probe if range_start is None else range_start
        range_end   = self.range_end_probe   if range_end   is None else range_end
        block_region = block[:,range_start:range_end] 

        # If range is 0 reject all rows
        if range_start == range_end:
            self.rejected_probe = 100
            return np.zeros_like(block)

        # Calculate the mean of the specified regions in the block
        row_means = block_region.mean(axis = 1)       # mean per row/shot
        overall_mean = np.mean(block_region)          # mean of all rows 

        # Determine the maximum allowed deviation
        allowed_deviation = (self.deviation_threshold_probe / 100.0) * overall_mean
        
        # Identify rows that are within the allowed deviation
        accaptable_rows = np.abs(row_means - overall_mean) <= allowed_deviation

        # Filter the block to keep only the acceptable rows
        block_clean = block[accaptable_rows]

        # Calculate the percentage of rejected rows
        self.rejected_probe = (len(block) -len(block_clean)) / len(block) * 100

        return block_clean
        
    def OutlierRejection_dA(self, block1, block2 = None , range_start: int | None = None, range_end:   int | None = None):
        """
        Rejects outliers for the real-time dA spectra in the dAWindow. 
        """
        block1 = np.asarray(block1)
        block2 = np.asarray(block2)

        if self.deviation_threshold_dA >= 100:
            return block1, block2
        
        # Get rejection range
        range_start = self.range_start_dA if range_start is None else range_start
        range_end   = self.range_end_dA   if range_end   is None else range_end
        block1_region = block1[:, range_start:range_end] 
        block2_region = block2[:, range_start:range_end] 
        
        # If range is 0 reject all rows
        if range_start == range_end:
            self.rejected_dA = 100
            return np.zeros_like(block1), np.zeros_like(block2)

        # Calculate the mean of the specified regions in the block
        block1_row_mean = block1_region.mean(axis=1)  # means per row/shot
        block2_row_mean = block2_region.mean(axis=1) 
        block1_mean =  np.mean(block1_region)         # overall means
        block2_mean =  np.mean(block2_region) 

        # Determine the maximum allowed deviations
        block1_allowed_deviation = (self.deviation_threshold_dA / 100.0) * block1_mean
        block2_allowed_deviation = (self.deviation_threshold_dA / 100.0) * block2_mean

        # Identify rows that are within the allowed deviation
        block1_acceptable_rows = np.abs(block1_row_mean - block1_mean) <= block1_allowed_deviation
        block2_acceptable_rows = np.abs(block2_row_mean - block2_mean) <= block2_allowed_deviation

        # Keep only paired "good" shots
        keep_mask = block1_acceptable_rows & block2_acceptable_rows
        block1_clean = block1[keep_mask]
        block2_clean = block2[keep_mask]

        # Calculate the percentage of rejected rows
        self.rejected_dA = (len(block1) - np.sum(keep_mask)) / len(block1) * 100

        return block1_clean, block2_clean

    """Helper functions that transfer values from the GUI to the outlier rejection functions"""
    # Toggle outlier rejection on/off
    def toggle_outlier_rejection_probe(self, selected):
        self.outlier_rejection_probe = selected
    def toggle_outlier_rejection_dA(self, selected):
        self.outlier_rejection_dA = selected

    # Sets deviation threshold from GUI 
    def deviation_change(self, value: float):
        self.deviation_threshold_probe = value
    def dA_deviation_change(self, value: float):
        self.deviation_threshold_dA = value

    # Sets outlier rejection range from GUI
    def update_outlier_range(self, start: int, end: int) -> None:
        self.range_start_probe, self.range_end_probe = sorted((int(start), int(end)))
    def update_outlier_range_dA(self, start: int, end: int) -> None:
        self.range_start_dA, self.range_end_dA = sorted((int(start), int(end)))


    def compute_spectra(self, block, start_pixel=12, end_pixel=1035):
        """
        Function for computing probe spectra and dA spectra
        """
        block = np.asarray(block)

        #Boolean masks for seperating states
        probe = block[block[:, 2] < 49152,  start_pixel:end_pixel]

        pump_off_dA = block[block[:, 2] < 49152,  start_pixel:end_pixel]
        pump_on_dA = block[block[:, 2] >= 49152, start_pixel:end_pixel]

        if self.dark_noise_correction is not None:
            probe = probe - self.dark_noise_correction
            pump_off_dA = pump_off_dA - self.dark_noise_correction
            pump_on_dA = pump_on_dA - self.dark_noise_correction

        # Probe spectra
        if self.outlier_rejection_probe == True:
            probe = self.OutlierRejection_probe(probe)

        if len(probe) == 0: # all shots got rejected
            self.probe_spectrum = np.zeros_like(self.probe_spectrum)
        else:
            self.probe_spectrum = np.mean(probe, axis=0)


        # dA calulations from pump‑on and pump‑off states
        if self.outlier_rejection_dA == True:
            pump_off_dA, pump_on_dA = self.OutlierRejection_dA(pump_off_dA, pump_on_dA)

        if len(pump_off_dA) == 0 or len(pump_on_dA) == 0:
            self.delta_A = np.zeros_like(self.delta_A)
            return self.probe_spectrum, self.delta_A
            
        # warn for mismatched pump-off and pump-on states
        if len(pump_off_dA) != len(pump_on_dA):
            print("Pump-off pump-on shots not of equal size")
        
        # pair shots and compute delta A
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = np.divide(pump_on_dA, pump_off_dA)
            ratio[ratio <= 0] = np.nan  # Avoid -inf from log(0) or log(negative)
            delta_A = -np.log(ratio)
          
        # average delta_A per shot
        self.delta_A = np.mean(delta_A, axis=0)
        
        return self.probe_spectrum, self.delta_A