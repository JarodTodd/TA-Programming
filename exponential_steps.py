import numpy as np

def generate_timepoints(t_start, t_end, num_points, t0=0):
    """
    Generate a sequence of time points with custom density before and after a reference time.
    This function creates a list of time points starting from 't_start' to 't_end', with a total of 'num_points'.
    It generates denser time points in the negative time region (before 't0'), with finer steps between -5 and -1,
    and coarser steps before -5. For times after 't0', it generates points spaced logarithmically up to 't_end'.
    Additionally, it symmetrically duplicates and flips the points between 0 and 1 ps to ensure even coverage.
    Parameters:
        t_start (float): The starting time (can be negative).
        t_end (float): The ending time (must be greater than t_start).
        num_points (int): Total number of time points to generate.
        t0 (float, optional): Reference time separating pre-dense and post-dense regions. Default is 0.
    Returns:
        list: Sorted list of generated time points.
    Side Effects:
        Saves the generated time points to a file named "time_points.txt".
    Notes:
        - The function ensures the total number of points matches 'num_points' by adjusting the log-spaced region.
        - Pre-dense region uses 1 ps steps for times < -5, and 0.5 ps steps for -5 <= time <= -1.
        - Post-dense region uses logarithmic spacing from 't0' to 't_end'.
        - Points between 0 and 1 ps are duplicated and flipped to cover negative times symmetrically.
    """
    pre_dense = []

    # Generate background steps if the start time is smaller than 0
    if t_start < t0:
        time = t_start
        # If the time is smaller than -5ps generate a time point every ps
        while time < -5:
            pre_dense.append(time)
            time += 1
        # If the time is in between -5 and -1 ps generate a time point every 0.5 ps
        while -5 <= time <= -1:
            pre_dense.append(time)
            time += 0.5
    pre_dense = np.array(pre_dense)

    # Remove the background steps from the step total to not generate "extra" steps
    # If you want to remove the recalculation with the "background" steps remove the len
    remaining = num_points - len(pre_dense)

    # Generate the time points from 0 to the end time on a log scale
    # Logspace starts at 1 and ends at end time + 1
    # afterwards it is shifted by -1 to make it start at 0 instead of 1
    log_post = np.logspace(np.log10(1), np.log10(t_end + 1), remaining, endpoint=False) - 1
    times = log_post

    # This converges the list of points to be the given amount of steps after adding the points from -1 to 0 ps
    while True:
        # Duplicate and flip the points from 0 to 1 ps.
        duplicated_section = -np.flip(times[(times > 0) & (times <= 0.99)])
        new_list = np.concatenate((times, duplicated_section))

        # If the length of the list has converged to the necessary time points return the list
        if len(new_list) == remaining:
            False
            timepoints = np.concatenate((pre_dense, new_list)) # Add the background and other steps together into one list
            timepoints.sort()
            timepoints = [value for value in timepoints]
            np.savetxt("time_points.txt", timepoints, fmt="%s")
            return timepoints

        # Recalculate the number of remaining points after duplication and flipping,
        # then regenerate the log-spaced region to try to converge to the desired total number of points.
        remaining_length = num_points - len(duplicated_section)
        log_post = np.logspace(np.log10(1), np.log10(t_end + 1), remaining_length) - 1 if t_end > t0 else np.array([])

        times = log_post  