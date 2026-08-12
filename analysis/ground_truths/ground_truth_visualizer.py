import numpy as np
import pandas as pd
import matplotlib.pylab as plt


ground_truth_csv = 'data/ZVW_hand_labels/ground_truth_ZVW_hand_labeled.csv'
recording_csv = 'data/measured_walks/initial_walk_test_10-08-2026_16-31-45_3.csv'

df_truth = pd.read_csv(ground_truth_csv)
df_base = pd.read_csv(recording_csv)

acc_mag = np.sqrt(df_base['ax']**2 + df_base['ay']**2 + df_base['az']**2)
gyro_mag = np.sqrt(df_base['gx']**2 + df_base['gy']**2 + df_base['gz']**2)



fig, ax1 = plt.subplots(figsize=(16,6))
ax1.plot(df_base['seq'], acc_mag, color="tab:blue", label='Acc Mag')
ax1.set_xlabel('Sequence')
ax1.set_ylabel('Acceleration Magnitude')

ax2 = ax1.twinx()
ax2.plot(df_base['seq'], gyro_mag, color='tab:red', label='Gyro Mag')
ax2.set_xlabel('Sequence')
ax2.set_ylabel('Gyroscope Magnitude')

starts, ends = df_truth['stance_start_idx'].tolist(), df_truth['stance_end_idx'].tolist()

for i, (start, end) in enumerate(zip(starts, ends)):
    # Convert row indexes to actual seq numbers for the X-axis
    seq_start = df_base.loc[start, 'seq']
    seq_end = df_base.loc[end, 'seq']
    
    if i == 0:
        ax1.axvspan(seq_start, seq_end, color='y', alpha=0.3, label='Predicted ZVWs')
    else:
        ax1.axvspan(seq_start, seq_end, color='y', alpha=0.3)
    

lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')

plt.title('Zero-Velocity Windows')
plt.tight_layout()


plt.show()