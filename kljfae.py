import numpy as np

timepoints = np.linspace(400, 1500, 1022)
with open("WAFJELKavelength_test.txt", "w") as f:
    f.write("Wavelengths\n")
    np.savetxt(f, timepoints, fmt="%s")