import pandas as pd
import numpy as np
import matplotlib.pylab as plt
import detectors as det
import filters as filt
import integrators as integ

csv_file_name = 'mag_walk_indoors_23-08-2026_20-02-47.csv'
csv_path = '../data/magnetometer_readings/'
csv_save_path = '../data/magnetometer_readings/'
df = pd.read_csv(f'{csv_path}{csv_file_name}', skipinitialspace=True)


# Get correct heading from Mahony filter:
ax, ay, az = df['ax'], df['ay'], df['az']
gx, gy, gz = df['gx'], df['gy'], df['gz']
mx, my, mz = df['mx'], df['my'], df['mz']

dt_array = (df['t_us'] - df['dt_us'].iloc[0])
dt_array = np.insert(dt_array, 0, dt_array.mean()) / 1e6

zvw_mask = det.detect_zvw(df)
masked_quats = filt.mahony_filter(ax,ay,az,gx,gy,gz,dt_array,zvw_mask)

raw_accel = np.column_stack((ax,ay,az))
global_accel = filt.rotate_vector_by_quaternion(raw_accel, masked_quats)
linear_accel = np.copy(global_accel)
linear_accel[:,2] -= 1.0
accel_ms2 = linear_accel * 9.80665




