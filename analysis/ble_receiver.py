"""
Live BLE receiver + plotter for the Nano33 foot-mounted inertial mapper.

Change vs. the previous version: every step vector is committed to the CSV the
moment it arrives, not at shutdown. A hard kill (terminal stop button, a Ctrl+C
the GUI loop swallows, a backend crash on window close) can no longer lose the
session -- worst case you lose the packet currently in flight.
"""

import asyncio
import csv
import datetime
import struct
import threading
import time

import matplotlib
import matplotlib.pyplot as plt
from bleak import BleakClient, BleakScanner
from matplotlib.animation import FuncAnimation

SERVICE_UUID = "28e1f1cd-733a-41d1-8d21-fb59e2c15db3"
CHAR_UUID = "28e1f1cd-733a-41d1-8d21-fb59e2c15db2"
DEVICE_NAME = "Nano33_Mapper"

# seq:H  x_mm:h  y_mm:h  stance_ms:H  quality:B  state:B  missed:H  -> 12 bytes
PACKET_FMT = "<HhhHBBH"
PACKET_LEN = struct.calcsize(PACKET_FMT)

# ---------------------------------------------------------------- shared state
# Touched by the bleak thread (writer) and the matplotlib main thread (reader).
_lock = threading.Lock()
path_x = [0.0]
path_y = [0.0]

_t0 = time.monotonic()

# ------------------------------------------------------- open the log up front
_csv_path = "_with_yield_ble_mapping_session_{}.csv".format(
    datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
)
_csv_file = open(_csv_path, "w", newline="")
_csv_writer = csv.writer(_csv_file)
_csv_writer.writerow(
    [
        "t_host_s",
        "Sequence",
        "X_Position_m",
        "Y_Position_m",
        "Stance_Duration_ms",
        "Quality",
        "State_Flag",
        "Missed_Ticks",
    ]
)
_csv_file.flush()


def notification_handler(_sender, data):
    """Runs on the bleak event-loop thread."""
    if len(data) != PACKET_LEN:
        print(f"Warning: {len(data)}-byte packet, expected {PACKET_LEN}.")
        return

    try:
        seq, x_mm, y_mm, stance_ms, quality, state_flag, missed = struct.unpack(
            PACKET_FMT, data
        )
    except struct.error as exc:
        print(f"Error parsing packet: {exc}")
        return

    abs_x = x_mm / 1000.0
    abs_y = y_mm / 1000.0
    t = time.monotonic() - _t0

    with _lock:
        path_x.append(abs_x)
        path_y.append(abs_y)
        _csv_writer.writerow(
            [f"{t:.3f}", seq, abs_x, abs_y, stance_ms, quality, state_flag, missed]
        )
        _csv_file.flush()  # survives TerminateProcess; fsync only needed for power loss

    print(
        f"Step {seq:5d}  pos=({abs_x:+7.2f}, {abs_y:+7.2f}) m  "
        f"stance={stance_ms:4d} ms  q={quality}  state={state_flag}  missed={missed}"
    )


async def run_ble():
    print(f"Scanning for {DEVICE_NAME}...")
    nano_device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=10.0)

    if nano_device is None:
        print(f"Could not find {DEVICE_NAME}. Is it powered on and advertising?")
        return

    print(f"Found {DEVICE_NAME} at {nano_device.address}. Connecting...")
    async with BleakClient(nano_device) as client:
        print("Connected. Subscribing to step vectors...")
        await client.start_notify(CHAR_UUID, notification_handler)
        while client.is_connected:
            await asyncio.sleep(1.0)
    print("BLE link dropped.")


def update_plot(_frame):
    with _lock:  # snapshot so the two lists can't be read out of sync
        xs = list(path_x)
        ys = list(path_y)

    plt.cla()
    plt.plot(xs, ys, "b-o", markersize=4, linewidth=2, label="Live Path")
    plt.plot(xs[0], ys[0], "go", markersize=8, label="Start")
    if len(xs) > 1:
        plt.plot(xs[-1], ys[-1], "ro", markersize=8, label="Current")

    plt.title(f"Live Wireless Indoor Map ({len(xs) - 1} steps)")
    plt.xlabel("X Position (meters)")
    plt.ylabel("Y Position (meters)")
    plt.grid(True)
    plt.legend()
    plt.axis("equal")


if __name__ == "__main__":
    print(f"matplotlib backend: {matplotlib.get_backend()}")
    print(f"Logging to {_csv_path} (written continuously)")

    threading.Thread(target=lambda: asyncio.run(run_ble()), daemon=True).start()

    fig = plt.figure(figsize=(6, 6))
    ani = FuncAnimation(fig, update_plot, interval=500, cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        # Nice-to-have, not load-bearing: the data is already on disk.
        with _lock:
            _csv_file.flush()
            _csv_file.close()
        print(f"Session saved: {_csv_path}")