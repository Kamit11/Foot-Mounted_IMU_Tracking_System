import serial
import time
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

PORT, N = 'COM5', 10000

rows = []
timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

print(f"Listening on {PORT} for {N} samples, saving to jitter_{timestamp}.csv...")
with serial.Serial(PORT, 115200, timeout=2) as s, open(f"jitter_{timestamp}.csv", "w", encoding='utf-8') as f:
    time.sleep(2)                 # Allow Arduino to reset
    s.reset_input_buffer()

    f.write("seq,t,dt,work,missed\n")

    rows_collected = 0
    while rows_collected < N:
        line = s.readline().decode(errors='ignore').strip()

        # Only write lines that contain data (skip empty lines and the Arduino's header)
        if line and not line.startswith('seq'):
            f.write(line + "\n")
            rows_collected += 1

            if rows_collected % 1000 == 0:
                print(f"Saved {rows_collected}/{N} samples.")

print("Data collection complete. Serial port closed.")
print("Saving to:", os.getcwd())

d = np.loadtxt(f"jitter_{timestamp}.csv", delimiter=',', skiprows=1)
seq, t, dt, work, missed = d.T
dt = dt[1:] # First sample is always 0, so ignore it

print(f"n={len(dt)}  mean={dt.mean():.1f}  sd={dt.std():.1f}")
print(f"min={dt.min()}  max={dt.max()}  p99={np.percentile(dt,99):.0f}")
print(f"missed deadlines: {missed[-1]}")
print(f"gaps in seq: {np.sum(np.diff(seq) != 1)}")

fig, ax = plt.subplots(1, 2, figsize=(11,4))

ax[0].hist(dt, bins=np.arange(dt.min()-0.5, dt.max()+1.5), log=True)
ax[0].axvline(5000, color='r', ls='--')
ax[0].set_xlabel("dt (us)")

ax[1].plot(dt, lw=0.4)
ax[1].axhline(5000, color='r', ls='--')
ax[1].set_xlabel("sample")
ax[1].set_ylabel("dt (us)")

plt.tight_layout()
plt.savefig(f"jitter_{timestamp}.png", dpi=120)
plt.show()