import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al

N = 12000
prefix = "g_error_test_flipped"
header = "t_us,seq,ax,ay,az,gx,gy,az,valid,t_imu_us,t_serial_us,missed"

csv_filepath = al.collect_serial_data(header = header, file_prefix=prefix, num_samples=N)
# csv_filepath = "data/temp_data/g_error_test_08-08-2026_21-08-35.csv"

d = np.loadtxt(csv_filepath, delimiter=',', skiprows=1)
t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed = d.T

mean_g = az.mean()
std_dev_g = az.std()

plt.plot(seq, az, lw=0.5)
plt.xlabel("Sample")
plt.ylabel("g (m/s^2)")
plt.axhline(mean_g, color='r', ls='--', label="Mean")
plt.legend()

plt.title(f"Mean: {mean_g:.4f} m/s^2\nStd Dev: {std_dev_g:.4f} m/s^2")

plt.tight_layout()
plt.savefig(f"{csv_filepath.replace('.csv', '.png')}", dpi=120)

plt.show()