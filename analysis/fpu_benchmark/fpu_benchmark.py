import numpy as np
import matplotlib.pyplot as plt
import arduino_logger as al

N = 120000

prefix = "fpu_enabled_benchmark"
header = "seq,work_time_us,mismatches"

csv_filepath = al.collect_serial_data(header = header, file_prefix=prefix, num_samples=N)

# Load the collected data and analyze it
d = np.loadtxt(f"{csv_filepath}", delimiter=',', skiprows=1)
seq, work, mismatches = d.T

mean_work = work.mean()
total_mismatches = mismatches[-1]
dropped_lines = np.sum(np.diff(seq) != 1)

print("\n=== BENCHMARK RESULTS ===")
print(f"Total Samples:    {len(work)}")
print(f"Dropped Lines:    {dropped_lines}")
print(f"Average Work Time: {mean_work:.2f} us")
print(f"FPU Corruptions:  {total_mismatches}")
print("=========================\n")

if total_mismatches > 0:
    print("WARNING: FPU CONTEXT CORRUPTION DETECTED. REVERT FLAGS.")
else:
    print("SUCCESS: FPU CONTEXT IS SAFE.")

plt.figure(figsize=(10, 4))
plt.plot(seq, work, lw=0.5, color='blue')
plt.axhline(mean_work, color='red', ls='--', label=f'Mean Work Time: {mean_work:.1f} us')
plt.title("FPU Benchmark Work Time")
plt.xlabel("Sample Index")
plt.ylabel("Work Time (us)")
plt.legend()
plt.tight_layout()
plt.savefig(f"{csv_filepath.replace('.csv', '.png')}", dpi=120)
plt.show()