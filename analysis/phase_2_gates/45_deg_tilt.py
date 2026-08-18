import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import detectors as det
import filters as filt

def evaluate_tilt_test(csv_filepath, test_name):
    # 1. Load Data
    df = pd.read_csv(csv_filepath, skipinitialspace=True)
    
    ax = df['ax']
    ay = df['ay']
    az = df['az']
    gx = df['gx']
    gy = df['gy']
    gz = df['gz']
    
    # 2. Compute dt_array
    dt_array = np.diff(df['t_us'] - df['t_us'].iloc[0]) / 1e6
    dt_array = np.insert(dt_array, 0, dt_array.mean())
    time_sec = (df['t_us'] - df['t_us'].iloc[0]) / 1e6
    
    # 3. Run Pipeline
    zvw_mask = det.detect_zvw(df=df)
    masked_quats = filt.mahony_filter(ax, ay, az, gx, gy, gz, dt_array, zvw_mask)
    roll, pitch, yaw = filt.quaternions_to_euler(masked_quats)
    
    # 4. Extract Metrics for Reviewer
    # Assume the first 2 seconds are flat on the table, and the last 2 seconds are flat on the table
    start_mask = time_sec < 2.0
    end_mask = time_sec > (time_sec.iloc[-1] - 2.0)
    
    start_roll = np.mean(roll[start_mask])
    end_roll = np.mean(roll[end_mask])
    roll_recovery_error = abs(end_roll - start_roll)
    
    start_pitch = np.mean(pitch[start_mask])
    end_pitch = np.mean(pitch[end_mask])
    pitch_recovery_error = abs(end_pitch - start_pitch)
    
    # 5. Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Text box styling
    bbox_props = dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray", alpha=0.85)
    
    # Roll Subplot (X-Axis)
    ax1.plot(time_sec, roll, color='tab:blue', label='Roll (X-Axis)', linewidth=1.5)
    ax1.set_title(f'{test_name} - Roll (X-Axis)')
    ax1.set_ylabel('Angle (deg)')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend(loc='lower right')
    
    roll_text = f"Recovery Error:\n{roll_recovery_error:.3f}°"
    ax1.text(0.02, 0.90, roll_text, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=bbox_props)
    
    # Pitch Subplot (Y-Axis)
    ax2.plot(time_sec, pitch, color='tab:red', label='Pitch (Y-Axis)', linewidth=1.5)
    ax2.set_title(f'{test_name} - Pitch (Y-Axis)')
    ax2.set_ylabel('Angle (deg)')
    ax2.set_xlabel('Time (s)')
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='lower right')
    
    pitch_text = f"Recovery Error:\n{pitch_recovery_error:.3f}°"
    ax2.text(0.02, 0.90, pitch_text, transform=ax2.transAxes, fontsize=10,
             verticalalignment='top', bbox=bbox_props)
    
    plt.tight_layout()
    plt.savefig(csv_filepath.replace('.csv', '_tilt_eval_Kp_Ki_change.png'), dpi=120)
    plt.show()


# X Axis Tilt
evaluate_tilt_test('data/orientation_mahony/tilt_long_edge_17-08-2026_16-51-01.csv', 'X-Axis Tilt Test (Roll)')

# Y Axis Tilt
evaluate_tilt_test('data/orientation_mahony/tilt_usb_edge_17-08-2026_16-50-19.csv', 'Y-Axis Tilt Test (Pitch)')