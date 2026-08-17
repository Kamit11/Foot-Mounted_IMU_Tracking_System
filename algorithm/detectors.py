import numpy as np

ACC_DEVIATION = 0.3    # Allowable deviation from 1.0g
GYRO_LIMIT = 75.0       # Maximum dps
VAR_LIMIT = 0.06        # Maximum rolling variance
VAR_WINDOW = 15         # Variance window to calculate
DWELL = 20               # Minimum consecutive samples

def detect_zvw(df, acc_thresh=ACC_DEVIATION, gyro_thresh=GYRO_LIMIT, var_thresh=VAR_LIMIT, var_window=VAR_WINDOW, min_dwell=DWELL):
    acc_mag = np.sqrt(df['ax']**2 + df['ay']**2 + df['az']**2)
    gyro_mag = np.sqrt(df['gx']**2 + df['gy']**2 + df['gz']**2)

    acc_thresh_samples = np.abs(acc_mag - 1) <= acc_thresh
    gyro_mag_samples = gyro_mag <= gyro_thresh

    acc_var = acc_mag.rolling(window=var_window).var().fillna(1.0)
    var_cond = acc_var <= var_thresh

    is_zvw = acc_thresh_samples & gyro_mag_samples & var_cond

    blocks = (is_zvw != is_zvw.shift()).cumsum()
    final_zvw = is_zvw.groupby(blocks).transform('sum') >= min_dwell
    
    return final_zvw