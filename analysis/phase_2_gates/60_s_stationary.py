import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al
import pandas as pd
import detectors as det
import filters as filt

N = 999999

prefix = "60_s_stationary_mahony_filter"
header = "t_us, seq, ax, ay, az, gx, gy, gz, valid, t_imu_us, t_serial_us, missed"
port = 'COM3'

# csv_filepath = al.collect_serial_data(header=header, file_prefix=prefix, num_samples=N, port=port)


csv_filepath = 'data/temp_data/60_s_stationary_log_17-08-2026_15-17-25.csv'
df = pd.read_csv(csv_filepath, skipinitialspace=True)

ax = df['ax']
ay = df['ay']
az = df['az']
gx = df['gx']
gy = df['gy']
gz = df['gz']

dt_array = np.diff(df['t_us'] - df['t_us'].iloc[0]) / 1e6
# Add a mean value at the beginning
dt_array = np.insert(dt_array, 0, dt_array.mean())

zvw_mask = det.detect_zvw(df=df)
masked_quats = filt.mahony_filter(ax, ay, az, gx, gy, gz, dt_array, zvw_mask)
masked_roll, masked_pitch, masked_yaw = filt.quaternions_to_euler(masked_quats)

time_sec = (df['t_us'] - df['t_us'].iloc[0]) / 1e6


settled_mask = time_sec > 10.0

roll_mean = np.mean(masked_roll[settled_mask])
roll_std = np.std(masked_roll[settled_mask])

pitch_mean = np.mean(masked_pitch[settled_mask])
pitch_std = np.std(masked_pitch[settled_mask])


# plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)

# Styling parameters for the metadata text box
bbox_props = dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray", alpha=0.85)

# roll
ax1.plot(time_sec, masked_roll, color='tab:blue', label='Roll', linewidth=1.2)
ax1.set_title('Roll (X-Axis Tilt) - Stationary Stability')
ax1.set_ylabel('Angle (deg)')
ax1.grid(True, linestyle='--', alpha=0.5)

roll_text = f"Settled ($t > 10$s):\nMean: {roll_mean:+.3f}°\nStd:  {roll_std:.4f}°"
ax1.text(0.98, 0.08, roll_text, transform=ax1.transAxes, fontsize=10,
         verticalalignment='bottom', horizontalalignment='right', bbox=bbox_props)

# Pitch
ax2.plot(time_sec, masked_pitch, color='tab:red', label='Pitch', linewidth=1.2)
ax2.set_title('Pitch (Y-Axis Tilt) - Stationary Stability')
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Angle (deg)')
ax2.grid(True, linestyle='--', alpha=0.5)

pitch_text = f"Settled ($t > 10$s):\nMean: {pitch_mean:+.3f}°\nStd:  {pitch_std:.4f}°"
ax2.text(0.98, 0.08, pitch_text, transform=ax2.transAxes, fontsize=10,
         verticalalignment='bottom', horizontalalignment='right', bbox=bbox_props)

plt.tight_layout()
plt.savefig('data/orientation_mahony/60_s_stationary_stability.png', dpi=120)
plt.show()


