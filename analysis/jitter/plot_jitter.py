import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al
import pandas as pd

N = 10000

# prefix = "jitter"
# header = "seq, t_us, dt_us, work_us, missed"

# csv_filepath = al.collect_serial_data(header=header, file_prefix=prefix, num_samples=N)

csv_filepath = 'data/IMU_Reading_Times/IMU_reading_times_I2C_Optimized_Burst_07-08-2026_18-53-38.csv'


df = pd.read_csv(csv_filepath, skipinitialspace=True)

# Keep dt in microseconds (us) without redundant offset subtraction
dt = np.diff(df['t_us'])

print(f"n={len(dt)}  mean={dt.mean():.1f} us  sd={dt.std():.1f} us")
print(f"min={dt.min()} us  max={dt.max()} us  p99={np.percentile(dt, 99):.0f} us")

fig, ax = plt.subplots(1, 2, figsize=(11, 4))

# Histogram binned by 1 us increments around your data
bins = np.arange(dt.min() - 0.5, dt.max() + 1.5, 1)
ax[0].hist(dt, bins=bins, log=True, edgecolor='black')
ax[0].axvline(5000, color='r', ls='--', label='Target 200Hz (5000 us)')
ax[0].set_xlabel("dt (us)")
ax[0].set_ylabel("Count (log)")
ax[0].legend()
ax[0].grid(True, linestyle='--', alpha=0.5)

# Time series jitter plot
ax[1].plot(dt, lw=0.4)
ax[1].axhline(5000, color='r', ls='--', label='Target 5000 us')
ax[1].set_xlabel("Sample")
ax[1].set_ylabel("dt (us)")
ax[1].legend()
ax[1].grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig(f"{csv_filepath.replace('.csv', '_jitter.png')}", dpi=120)
plt.show()