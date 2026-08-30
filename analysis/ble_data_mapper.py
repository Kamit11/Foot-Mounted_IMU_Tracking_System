import matplotlib.pyplot as plt
import pandas as pd

csv_name = "3_ble_mapping_session_30-08-2026_20-35-24.csv"
save_path = "data/ble_walking_logs/"
df = pd.read_csv(f"{save_path}{csv_name}")


path_x, path_y = df['X_Position_m'], df['Y_Position_m']

"""Matplotlib animation function called every 500ms"""
plt.cla()
plt.plot(path_x, path_y, 'b-o', markersize=4, linewidth=2, label="Live Path")
plt.plot(path_x.iloc[0], path_y.iloc[0], 'go', markersize=8, label="Start")
if len(path_x) > 1:
    plt.plot(path_x.iloc[-1], path_y.iloc[-1], 'ro', markersize=8, label="Current")

plt.title("Live Wireless Indoor Map")
plt.xlabel("X Position (meters)")
plt.ylabel("Y Position (meters)")
plt.grid(True)
plt.legend()
plt.axis('equal') # Force 1:1 aspect ratio
plt.savefig(f"{save_path}{csv_name}".replace(".csv", ",.png"), dpi=120)
plt.show()
