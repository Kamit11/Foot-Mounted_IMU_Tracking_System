import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

file_name = 'initial_walk_test_10-08-2026_16-31-45_3.csv'
file_path = f'data/measured_walks/{file_name}'
df = pd.read_csv(file_path)

save_path = f'data/zero_velocity_windows/{file_name}'.replace('.csv', '_ground_truth_ZVW.csv')

sample_seq = df['seq']
accel_mag = np.sqrt(df['ax']**2 + df['ay']**2 + df['az']**2)
gyro_mag = np.sqrt(df['gx']**2 + df['gy']**2 + df['gz']**2)

fig, ax1 = plt.subplots(figsize=(16,6))

ax1.plot(sample_seq, accel_mag, color='tab:blue', label='Accel Mag')
ax1.set_xlabel('Sample Index')
ax1.set_ylabel('Accel Magnitude (g)', color = 'tab:blue')
ax1.set_ylim(0, 4) # Clip to see the flatlines clearly

ax2 = ax1.twinx()
ax2.plot(sample_seq, gyro_mag, color='tab:red', label='Gyrp Mag')
ax2.set_xlabel('Gyro Magnitude (dps)', color='tab:red')
ax2.set_ylabel('Gyroscope Magnitude (dps)')
ax2.set_ylim(-10, 500)

plt.title("Click START and END of flatline for 20 steps (40 clicks total). Right click to undo a mistake.")
ax1.set_xlim(36000, 40000)
plt.tight_layout()
print("Click 20 times on the plot (Start of stance, End of stance, repeat 10 times)...")

click = plt.ginput(n=20, timeout=0, show_clicks=True)
plt.close()

zvw_starts = []
zvw_ends = []

if len(click) % 2 != 0:
    print(f"Warning: You clicked an odd number of times ({len(click)}). Dropping the last incomplete pair.")
    click = click[:-1] # Slicing off the last item to make it even

for i in range(0, len(click), 2):
    start_x = click[i][0]
    end_x = click[i+1][0]
    
    # 2. UPGRADE: "Snap" the user's manual click to the nearest ACTUAL hardware sequence number
    # This guarantees we never save a dropped packet or floating-point sequence number
    real_start_seq = df.iloc[(df['seq'] - start_x).abs().argsort()[:1]]['seq'].values[0]
    real_end_seq = df.iloc[(df['seq'] - end_x).abs().argsort()[:1]]['seq'].values[0]
    
    zvw_starts.append(real_start_seq)
    zvw_ends.append(real_end_seq)

truth_df = pd.DataFrame ({
    'window_start_seq': zvw_starts,
    'window_end_seq': zvw_ends,
    'source_file': file_name
})

truth_df.to_csv(save_path, index=False)
print(f"Saved {len(zvw_starts)} hand labeled steps to {save_path}")