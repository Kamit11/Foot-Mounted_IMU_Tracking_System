import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al

N = 9999999
prefix = "initial_walk_test"
header = "t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed"

# csv_filepath = al.collect_serial_data(header = header, file_prefix=prefix, num_samples=N, port='COM3')
csv_filepath = "data/temp_data/initial_walk_test_10-08-2026_18-01-41_awkward_walk_carpet.csv"


d = np.loadtxt(csv_filepath, delimiter=',', skiprows=1)
t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed = d.T

mag = np.sqrt(ax**2 + ay**2 + az**2)
avg_mag = mag.mean()
fig, axs = plt.subplots(2, 1, figsize=(12
                                       , 8), sharex=True)

# Top Plot: Individual Axes
axs[0].plot(t_us, ax, label='Accel X', alpha=0.7)
axs[0].plot(t_us, ay, label='Accel Y', alpha=0.7)
axs[0].plot(t_us, az, label='Accel Z', alpha=0.7)
axs[0].axhline(16, color='r', linestyle='--', label='+16g Limit')
axs[0].axhline(-16, color='r', linestyle='--', label='-16g Limit')
axs[0].set_ylabel("Acceleration (g)")
axs[0].set_title("Walk Test: Raw Accelerometer Axes")
axs[0].legend()

# Bottom Plot: Total Magnitude
axs[1].plot(t_us, mag, label='Magnitude', color='purple')
axs[1].axhline(16, color='r', linestyle='--', label='+16g Limit')
axs[1].set_xlabel("Time (us)")
axs[1].set_ylabel("Acceleration (g)")
axs[1].set_title("Walk Test: Total Magnitude")
axs[1].axhline(avg_mag, color='y', linestyle='--', label=f"Mean: {avg_mag:.4f} g")
axs[1].axhline(mag.max(), color='g', linestyle='--', label=f"Max: {mag.max():.4f} g")
axs[1].legend()

plt.tight_layout()
plt.savefig(f"{csv_filepath.replace('.csv', '.png')}", dpi=120)

plt.show()