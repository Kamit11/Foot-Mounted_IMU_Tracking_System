import serial
import time
import numpy as np
import matplotlib.pyplot as plt

port = 'COM5'
N = 2000
FRS_Limit = 4.0 #g

timestamp = time.strftime("%d-%m-%Y_%H-%M-%S")
filename = f"data/temp_data/IMU_reading_times_I2C_400kHz_{timestamp}.csv"

with serial.Serial(port, 115200, timeout=2) as s, open(filename, "w") as f:
    time.sleep(2) # Allow Arduino to reset
    s.reset_input_buffer()

    # Discard the first two reads to clear out any chopped half-lines
    # s.readline() 
    # s.readline()

    # Send a single byte to break the Arduino out of its while loop
    s.write(b'S')
    s.flush() # Ensure the byte is sent out immediately
    
    print(f"Listening on {port} for {N} samples, saving to {filename}...")
    for i in range(N):
        line = s.readline().decode(errors='ignore').strip()

        if line and not line.startswith('seq'):
            f.write(line + "\n")
            if (i + 1) % 100 == 0:
                print(f"Saved {i + 1}/{N} samples.")

    print(f"Saved {N} samples to {filename}")


d = np.loadtxt(filename, delimiter=',', skiprows=1)
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
plt.savefig(f"{filename.replace('.csv', '.png')}", dpi=120)

plt.show()