import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al


prefix = "IMU_reading_times_I2C_400kHz"
header = "t_us,seq,cost_a_avail_us,cost_a_read_us,cost_g_avail_us,cost_g_read_us,t_imu_us,t_serial_us,missed"

# csv_filepath = al.collect_serial_data(header = header, file_prefix=prefix)
csv_filepath = "data/IMU_Reading_Times/IMU_reading_times_I2C_400KHz_06-08-2026_17-16-01.csv"
newfilename = "data/IMU_Reading_Times/IMU_reading_times_I2C_400KHz_06-08-2026_17-16-01_2.csv"

d = np.loadtxt(csv_filepath, delimiter=',', skiprows=1)
t_us, seq, cost_a_avail_us, cost_a_read_us, cost_g_avail_us, cost_g_read_us, t_imu_us, t_serial_us, missed = d.T

a_avail_mean = cost_a_avail_us.mean()
a_read_mean = cost_a_read_us.mean()
g_avail_mean = cost_g_avail_us.mean()
g_read_mean = cost_g_read_us.mean()

valid_a_reads = cost_a_read_us[cost_a_read_us > 1000]
valid_g_reads = cost_g_read_us[cost_g_read_us > 1000]
true_a_read_mean = valid_a_reads.mean()
true_g_read_mean = valid_g_reads.mean()

print(f"Average a_avail time: {a_avail_mean:.1f} us")
print(f"Average a_read time: {a_read_mean:.1f} us")
print(f"Average g_avail time: {g_avail_mean:.1f} us")
print(f"Average g_read time: {g_read_mean:.1f} us")
print(f"Average valid a_read time: {true_a_read_mean:.1f} us")
print(f"Average valid g_read time: {true_g_read_mean:.1f} us")

print("\n=== IMU DATA ANALYSIS ===")
print(f"Missed deadline counter: {missed[-1]}")
print(f"I2C read cost (t_imu): mean={t_imu_us.mean():.1f} (us) | max={t_imu_us.max():.0f} (us)")
print(f"Serial write cost (t_serial): mean={t_serial_us.mean():.1f} (us) | max={t_serial_us.max():.0f} (us)")
print("===========================")

# Define the mosaic layout: 
# A (a_read hist), B (g_read hist)
# C (t_imu line), D (t_serial line)
layout = """
AB
CD
"""

# Increase figsize to 12x8 to comfortably fit the new row
fig, axs = plt.subplot_mosaic(layout, figsize=(12, 8))

# Histograms (A & B)
axs['A'].hist(valid_a_reads, bins=50, log=True)
axs['A'].axvline(true_a_read_mean, color='r', ls='--', label=f'mean: {true_a_read_mean:.0f} (us)')
axs['A'].set_xlabel("a_read (us) [Filtered]")
axs['A'].set_title("Accelerometer Read Distribution")
axs['A'].legend()

axs['B'].hist(valid_g_reads, bins=50, log=True)
axs['B'].axvline(true_g_read_mean, color='r', ls='--', label=f'mean: {true_g_read_mean:.0f} (us)')
axs['B'].set_xlabel("g_read (us) [Filtered]")
axs['B'].set_title("Gyroscope Read Distribution")
axs['B'].legend()


# Reading Times Over Sequence (C & D)
axs['C'].plot(seq, t_imu_us, lw=0.8, color='purple', alpha=0.8)
axs['C'].axhline(t_imu_us.mean(), color='r', ls='--', label=f'mean: {t_imu_us.mean():.0f} (us)')
axs['C'].set_xlabel("Sample Index (seq)")
axs['C'].set_ylabel("t_imu (us)")
axs['C'].set_title("I2C Reading Time (Timeline)")
axs['C'].legend()

axs['D'].plot(seq, t_serial_us, lw=0.8, color='green', alpha=0.8)
axs['D'].axhline(t_serial_us.mean(), color='r', ls='--', label=f'mean: {t_serial_us.mean():.0f} (us)')
axs['D'].set_xlabel("Sample Index (seq)")
axs['D'].set_ylabel("t_serial (us)")
axs['D'].set_title("Serial Write Time (Timeline)")
axs['D'].legend()


plt.tight_layout()
plt.savefig(f"{newfilename.replace('.csv', '.png')}", dpi=120)

plt.show()