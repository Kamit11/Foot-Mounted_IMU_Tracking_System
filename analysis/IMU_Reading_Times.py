import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al

FRS_Limit = 4.0 #g

prefix = "IMU_reading_times_I2C_400kHz"
header = "t_us,seq,cost_a_avail_us,cost_a_read_us,cost_g_avail_us,cost_g_read_us,t_imu_us,t_serial_us,missed"

csv_filepath = al.collect_serial_data(header = header, file_prefix=prefix)


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


fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].hist(valid_a_reads, bins=50, log=True)
ax[0].axvline(true_a_read_mean, color='r', ls='--', label=f'mean: {true_a_read_mean:.0f} (us)')
ax[0].set_xlabel("a_read (us) [Filtered]")
ax[0].legend()

ax[1].hist(valid_g_reads, bins=50, log=True)
ax[1].axvline(true_g_read_mean, color='r', ls='--', label=f'mean: {true_g_read_mean:.0f} (us)')
ax[1].set_xlabel("g_read (us) [Filtered]")
ax[1].legend()


plt.tight_layout()
plt.savefig(f"{csv_filepath.replace('.csv', '.png')}", dpi=120)

plt.show()