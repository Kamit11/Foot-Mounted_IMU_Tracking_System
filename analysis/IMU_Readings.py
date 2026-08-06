import serial
import time
import numpy as np
import matplotlib.pyplot as plt

port = 'COM5'
N = 6000
FRS_Limit = 4.0 #g
file_count = 2

timestamp = time.strftime("%d-%m-%Y_%H-%M-%S")
filename = f"data/temp_data/IMU_readings_{file_count}.csv"

with serial.Serial(port, 115200, timeout=2) as s, open(filename, "w") as f:
    time.sleep(2) # Allow Arduino to reset
    s.reset_input_buffer()

    # Discard the first two reads to clear out any chopped half-lines
    s.readline() 
    s.readline()

    print(f"Listening on {port} for {N} samples, saving to {filename}...")
    f.write("t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu,t_serial,missed\n")
    for i in range(N):
        line = s.readline().decode(errors='ignore').strip()

        if line and not line.startswith('seq'):
            f.write(line + "\n")
            if (i + 1) % 100 == 0:
                print(f"Saved {i + 1}/{N} samples.")

    print(f"Saved {N} samples to {filename}")


d = np.loadtxt(filename, delimiter=',', skiprows=1)
t_us, seq, ax, ay, az, gx, gy, gz, valid, t_imu_us, t_serial_us, missed = d.T

# Calculate max, duplicates and ZOH
max_ax = np.abs(ax).max()
max_ay = np.abs(ay).max()
max_az = np.abs(az).max()
ax_duplicates = np.sum(np.diff(ax) == 0)
ay_duplicates = np.sum(np.diff(ay) == 0)
az_duplicates = np.sum(np.diff(az) == 0)
zoh_count = np.sum(valid == 0);


print("\n=== IMU DATA ANALYSIS ===")
print(f"Duplicate ax readings: {ax_duplicates}")
print(f"Duplicate ay readings: {ay_duplicates}")
print(f"Duplicate az readings: {az_duplicates}")
print(f"ZOH events: {zoh_count}")
print(f"Missed deadline counter: {missed[-1]}")
print(f"I2C read cost (t_imu): mean={t_imu_us.mean():.1f} (us) | max={t_imu_us.max():.0f} (us)")
print(f"Serial write cost (t_serial): mean={t_serial_us.mean():.1f} (us) | max={t_serial_us.max():.0f} (us)")
print("===========================")


fig, accel = plt.subplots(1, 3, figsize=(12, 4))

axes_data = [
    ("X-axis", ax, 'blue', accel[0]),
    ("Y-axis", ay, 'green', accel[1]),
    ("Z-axis", az, 'orange', accel[2])
]

# Create a mask for invalid data
zoh_mask = valid == 0

for label, data, color, subplot in axes_data:
    subplot.plot(seq, data, lw=0.5, color=color)

    if np.any(zoh_mask):
        subplot.scatter(seq[zoh_mask], data[zoh_mask], s=30, color='black', zorder=2, marker='x', label='ZOH (Held)')

    subplot.axhline(FRS_Limit, color='red', ls='--', label=f'FRS Limit: {FRS_Limit:.2f} g')
    subplot.axhline(-FRS_Limit, color='red', ls='--')
    subplot.set_title(f"Acceleration {label}")
    subplot.set_xlabel("Sample Index")
    subplot.set_ylabel("a (g)")
    subplot.legend()
    


fig.tight_layout()
fig.savefig(f"{filename.replace('.csv', '.png')}", dpi=120)

plt.show()