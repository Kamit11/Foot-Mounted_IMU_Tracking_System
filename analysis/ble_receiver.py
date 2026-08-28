import asyncio
from bleak import BleakScanner, BleakClient
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import struct
import csv
import datetime

SERVICE_UUID = "28e1f1cd-733a-41d1-8d21-fb59e2c15db3"
CHAR_UUID = "28e1f1cd-733a-41d1-8d21-fb59e2c15db2"
DEVICE_NAME = "Nano33_Mapper"

# global state
sequences = [0]
path_x = [0.0]
path_y = [0.0]
missed_loops = [0]


def notification_handler(sender, data):
    try:
        # Unpack exactly 12 bytes using the reviewer's format string:
        # < = Little Endian (Arduino standard)
        # H = uint16, h = int16, B = uint8
        if len(data) == 12:
            unpacked = struct.unpack('<HhhHBBH', data)
            
            seq = unpacked[0]
            # Convert millimeters back to meters for the matplotlib engine
            abs_x = unpacked[1] / 1000.0
            abs_y = unpacked[2] / 1000.0
            stance_dur = unpacked[3]
            quality = unpacked[4]
            state_flag = unpacked[5]
            missed = unpacked[6]

            path_x.append(abs_x)
            path_y.append(abs_y)
            sequences.append(seq)
            missed_loops.append(missed)

            print(f"Step {seq} Received! Absolute Pos: ({abs_x:.2f}, {abs_y:.2f}) [Missed: {missed}]")
        else:
            print(f"Warning: Received packet of length {len(data)}, expected 12 bytes.")

    except Exception as e:
            print(f"Error parsing packet: {e}")


async def run_ble():
    print(f"Scanning for {DEVICE_NAME}...")
    devices = await BleakScanner.discover()

    nano_device = None
    for d in devices:
        if d.name == DEVICE_NAME:
            nano_device = d
            break

    if not nano_device:
        print(f"Could not find {DEVICE_NAME}. Is it powered on and advertising?")
        return
    
    print(f"Found {DEVICE_NAME} at {nano_device.address}. Connecting...")

    async with BleakClient(nano_device) as client:
        print("Connected! Subscribing to step vectors...")
        await client.start_notify(CHAR_UUID, notification_handler)
        
        # Keep the async loop alive indefinitely while the plotter runs on the main thread
        while True:
            await asyncio.sleep(1.0)


def update_plot(frame):
    """Matplotlib animation function called every 500ms"""
    plt.cla()
    plt.plot(path_x, path_y, 'b-o', markersize=4, linewidth=2, label="Live Path")
    plt.plot(path_x[0], path_y[0], 'go', markersize=8, label="Start")
    if len(path_x) > 1:
        plt.plot(path_x[-1], path_y[-1], 'ro', markersize=8, label="Current")

    plt.title("Live Wireless Indoor Map")
    plt.xlabel("X Position (meters)")
    plt.ylabel("Y Position (meters)")
    plt.grid(True)
    plt.legend()
    plt.axis('equal') # Force 1:1 aspect ratio


if __name__ == "__main__":
    # Start the BLE background task
    import threading
    # Run BLE on different thread to allow matplotlib full control of thread 1
    ble_thread = threading.Thread(target=lambda: asyncio.run(run_ble()), daemon=True)
    ble_thread.start()

    # Start the matplotlib live plotter (must run on main thread)
    fig = plt.figure(figsize=(8, 8))
    ani = FuncAnimation(fig, update_plot, interval=500, cache_frame_data=False)
    plt.show()

    print("Plot closed. Exporting data to CSV...")
    timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    filename = f"mapping_session_{timestamp}.csv"
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        # Write the header
        writer.writerow(["Sequence", "X_Position_m", "Y_Position_m", "Missed_Ticks"])
        
        # Write the data rows
        for i in range(len(path_x)):
            # Safety check to prevent index errors just in case
            seq_val = sequences[i] if i < len(sequences) else sequences[-1]
            miss_val = missed_loops[i] if i < len(missed_loops) else missed_loops[-1]
            writer.writerow([seq_val, path_x[i], path_y[i], miss_val])
            
    print(f"Export complete! Saved to {filename}")