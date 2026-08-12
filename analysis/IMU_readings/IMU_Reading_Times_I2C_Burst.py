import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al

N = 60000

prefix = "IMU_reading_times_I2C_Optimized_Burst"
header = "t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed"

csv_filepath = al.collect_serial_data(header = header, file_prefix=prefix, num_samples=N)

# filepath = "data/temp_data/IMU_reading_times_I2C_Optimized_Burst_07-08-2026_17-57-48.csv"

d = np.loadtxt(csv_filepath, delimiter=',', skiprows=1)
t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed = d.T

t_imu_mean = t_imu_us.mean()
t_serial_mean = t_serial_us.mean()


# Stack the 6 physical data columns into a single 2D array
sensor_data = np.column_stack((ax,ay,az,gx,gy,gz))

# Calculate the difference between consecutive rows
# np.diff subtracts row[i-1] from row[i]
diffs = np.diff(sensor_data, axis=0)

# A frame is a duplicate (ZOH) ONLY if the difference across ALL 6 axes is exactly 0
is_duplicate = np.all(diffs == 0, axis=1)

duplicate_count = np.sum(is_duplicate)
duplicate_fraction = (duplicate_count/len(ax))*100

zoh_count = np.sum(valid == 0)
zoh_fraction = (zoh_count/len(ax))*100


print("\n=== IMU GENRAL DATA ANALYSIS ===")
print(f"Total Samples: {len(ax)}")
print(f"Duplicate Events: {duplicate_count} ({duplicate_fraction:.1f}%)")
print(f"ZOH Events: {zoh_count} ({zoh_fraction:.1f}%)")
print(f"Missed deadline counter: {missed[-1]}")
print(f"I2C read cost (t_imu): mean={t_imu_mean:.1f} (us) | max={t_imu_us.max():.0f} (us)")
print(f"Serial write cost (t_serial): mean={t_serial_mean:.1f} (us) | max={t_serial_us.max():.0f} (us)")
print("===========================")

print("\n=== 5-MIN STATIC LOGIC REPORT===")
print("\n--- 1. Accelerometer Axes ---")
print(f"Accel X: Mean = {ax.mean():.5f} g | Std Dev = {ax.std():.5f} g")
print(f"Accel Y: Mean = {ay.mean():.5f} g | Std Dev = {ay.std():.5f} g")
print(f"Accel Z: Mean = {az.mean():.5f} g | Std Dev = {az.std():.5f} g")

mag = np.sqrt(ax**2 + ay**2 + az**2)
print("\n--- 2. Accelerometer Magnitude ---")
print(f"Magnitude: Mean = {mag.mean():.5f} g | Std Dev = {mag.std():.5f} g")

# 3. Gyroscope Bias (Mean only)
print("\n--- 3. Gyroscope Bias (ZARU) ---")
print(f"Gyro X Bias: {gx.mean():.5f} dps")
print(f"Gyro Y Bias: {gy.mean():.5f} dps")
print(f"Gyro Z Bias: {gz.mean():.5f} dps")


fig, axs = plt.subplots(1, 2, figsize=(12, 4))
axs[0].hist(t_imu_us, bins = np.arange(t_imu_us.min()-0.5, t_imu_us.max()+1.5), log=True)
axs[0].axvline(t_imu_mean, color='r', ls='--', label=f'mean: {t_imu_mean:.0f} (us)')
axs[0].set_xlabel("t_imu (us)")
axs[0].legend()

axs[1].hist(t_serial_us, bins = np.arange(t_serial_us.min()-0.5, t_serial_us.max()+1.5), log=True)
axs[1].axvline(t_serial_mean, color='r', ls='--', label=f'mean: {t_serial_mean:.0f} (us)')
axs[1].set_xlabel("t_serial (us)")
axs[1].legend()


plt.tight_layout()
plt.savefig(f"{csv_filepath.replace('.csv', '.png')}", dpi=120)

plt.show()