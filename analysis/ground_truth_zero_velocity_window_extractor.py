import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

file_name = "data/measured_walks/initial_walk_test_10-08-2026_16-38-16_long_walk.csv"
df = pd.read_csv(file_name)

sample_idx = df.index
accel_mag = np.sqrt(df['ax']**2 + df['ay']**2 + df['az']**2)
gyro_mag = np.sqrt(df['gx']**2 + df['gy']**2 + df['gz']**2)

fig, ax1 = plt.subplots(figsize=(16,6))

ax1.plot(sample_idx, accel_mag, color='tab:blue', label='Accel Mag')
ax1.set_xlabel('Sample Index')
ax1.set_ylabel('Accel Magnitude (g)', color = 'tab:blue')
ax1.set_ylim(0, 4) # Clip to see the flatlines clearly

ax2 = ax1.twinx()
ax2.plot(sample_idx, gyro_mag, color='tab:red', label='Gyrp Mag')
ax2.set_xlabel('Gyro Magnitude (dps)', color='tab:red')
ax2.set_ylabel('Gyroscope Magnitude (dps)')
ax2.set_ylim(-10, 500)

plt.title("Click START and END of flatline for 20 steps (40 clicks total). Right click to undo a mistake.")
ax1.set_xlim(6000, 10500)
plt.tight_layout()
print("Click 20 times on the plot (Start of stance, End of stance, repeat 10 times)...")

click = plt.ginput(n=40, timeout=0, show_clicks=True)
plt.close()

stance_starts = []
stance_ends = []

for i in range(0, len(click), 2):
    # clicks is a list of (x, y) tuples. We only want the X-coordinate (sample index)
    start_x = click[i][0]
    end_x = click[i+1][0]
    stance_starts.append(int(round(start_x)))
    stance_ends.append(int(round(end_x)))

truth_df = pd.DataFrame ({
    'stance_start_idx': stance_starts,
    'stance_end_idx': stance_ends,
    'source_file': file_name
})

save_file_name = "ground_truth_ZVW_long_walk.csv"
truth_df.to_csv(save_file_name, index=False)
print(f"Saved 20 hand labeled steps to {save_file_name}")