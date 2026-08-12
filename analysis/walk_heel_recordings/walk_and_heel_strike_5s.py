import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import arduino_logger as al

N = 3000
prefix = "initial_walk_test"
header = "t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed"

# csv_filepath = al.collect_serial_data(header = header, file_prefix=prefix, num_samples=N, port='COM3')
csv_filepath = "data/walk_and_heel_stike_tests/initial_walk_test_08-08-2026_22-06-42.csv"

df = pd.read_csv(csv_filepath)

# Convert to seconds
time_sec = (df['t_us'] - df['t_us'].iloc[0]) / 1e6 
acc_mag = np.sqrt(df['ax']**2 + df['ay']**2 + df['az']**2)
gyr_mag = np.sqrt(df['gx']**2 + df['gy']**2 + df['gz']**2)


zoom_start = 2
zoom_end = 10 

# Create a boolean mask to slice the exact timeframe
mask = (time_sec >= zoom_start) & (time_sec <= zoom_end)

fig, axs = plt.subplots(figsize=(12, 6))


axs.plot(time_sec[mask], acc_mag[mask], color='b', label='Accel Mag')
axs.set_xlabel("Time (s)")
axs.set_ylabel("Accel Magnitude (g)")
axs.tick_params(axis='y', labelcolor='b')

axs2 = axs.twinx()
axs2.plot(time_sec[mask], gyr_mag[mask], color='r', label='Gyro Mag')
axs2.set_ylabel("Gyro Magnitude (dps)")
axs2.tick_params(axis='y', labelcolor='r')

lines_1, labels_1 = axs.get_legend_handles_labels()
lines_2, labels_2 = axs2.get_legend_handles_labels()
axs.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')


# This dynamically creates tick marks every 0.1 seconds for your specific window
# axs.set_xticks(np.arange(zoom_start, zoom_end + 0.1, 0.1)) 

axs.grid(True)
plt.title(f"Peak Analysis: {zoom_start}s to {zoom_end}s")

plt.tight_layout()
plt.savefig(f"{csv_filepath.replace('.csv', '_zoomed_peak.png')}", dpi=120)

plt.show()