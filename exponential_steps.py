import numpy as np
import matplotlib.pyplot as plt

def generate_timepoints(t_start, t_end, num_points, t0=0):
    pre_dense = []
    if t_start < t0:
        time = t_start
        while time < -5:
            pre_dense.append(time)
            time += 1
        while -5 <= time <= -1:
            pre_dense.append(time)
            time += 0.5
    pre_dense = np.array(pre_dense)

    # If you want to remove the recalculation with the "background" steps remove the len
    remaining = num_points - len(pre_dense)

    log_post = np.logspace(np.log10(1), np.log10(t_end + 1), remaining, endpoint=False) - 1
    times = log_post
    while True:
        duplicated_section = -np.flip(times[(times > 0) & (times <= 0.99)])
        new_list = np.concatenate((times, duplicated_section))

        if len(new_list) == num_points:
            False
            timepoints = np.concatenate((pre_dense, new_list))
            timepoints.sort()
            timepoints = [f"{value} ps" for value in timepoints]
            print(timepoints)
            np.savetxt("time_points.txt", timepoints, fmt="%s")
            return timepoints

        remaining_length = num_points - len(duplicated_section)
        log_post = np.logspace(np.log10(1), np.log10(t_end + 1), remaining_length) - 1 if t_end > t0 else np.array([])

        times = log_post  

# generate_timepoints(-10, 3000, 2000)