# detectors.py
import numpy as np
import pandas as pd

def detect_zvw(df, acc_thresh, gyro_thresh, var_thresh, var_window, min_dwell):
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