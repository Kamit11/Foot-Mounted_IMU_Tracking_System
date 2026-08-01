import serial
import time
import os
import numpy as np
import matplotlib.pyplot as plt

PORT, N = 'COM5', 10000

rows = []

with serial.Serial(PORT, 115200, timeout=2) as s:
    time.sleep(2)                 # Allow Arduino to reset
    s.reset_input_buffer()

    while len(rows) < N:
        line = s.readline().decode(errors='ignore').strip()

        if line and not line.startswith('seq'):
            try:
                rows.append([int(x) for x in line.split(',')])

                if len(rows) % 1000 == 0:
                    print(f"Received {len(rows)} samples")

            except ValueError:
                pass

print("Saving to:", os.getcwd())

d = np.array(rows)
seq, t, dt, work, missed = d.T
dt = dt[1:]

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
plt.savefig("jitter.png", dpi=120)
plt.show()