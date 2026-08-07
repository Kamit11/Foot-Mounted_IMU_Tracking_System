import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al

N = 10000

prefix = "jitter"
header = "seq, t_us, dt_us, work_us, missed"

csv_filepath = al.collect_serial_data(header=header, file_prefix=prefix, N=N)

d = np.loadtxt(f"{csv_filepath}", delimiter=',', skiprows=1)
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
plt.savefig(f"{csv_filepath.replace('.csv', '.png')}", dpi=120)
plt.show()