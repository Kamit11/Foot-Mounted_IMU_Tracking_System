import serial
import time
import os
from datetime import datetime


N = 999999

prefix = "18m_walk_indoors_with_BLE_wired"
header = "t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed"
port = 'COM3'



def collect_serial_data(header, port='COM5', num_samples=2000, file_prefix="benchmark", save_to_temp_dir=True):
    """
    Collects data from an Arduino via serial port and saves it to a CSV.
    Returns the absolute path to the saved CSV file.
    """
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    filename = f"{file_prefix}_{timestamp}.csv"

    if not header.endswith('\n'):
            header += '\n'

    if save_to_temp_dir:
        os.makedirs("data/temp_data/", exist_ok=True)
        filepath = os.path.join("data/temp_data", filename)
    else:
        filepath = os.path.join(os.getcwd(), filename)
    
    print(f"Listening on {port} for {num_samples} samples, saving to {filepath}...")
    
    with serial.Serial(port, 115200, timeout=2) as s, open(filepath, "w", encoding='utf-8') as f:
        time.sleep(2)                # Allow Arduino to reset
        s.reset_input_buffer()

        # Send a single byte to break the Arduino out of its while loop
        s.write(b'S')
        s.flush() # Ensure the byte is sent out immediately

        f.write(header)

        # Skip the first 10 lines
        print("Discarding first 10 startup samples...")
        for _ in range(10):
            s.readline()

        rows_collected = 0
        while rows_collected < num_samples:
            line = s.readline().decode(errors='ignore').strip()

            # Only write lines that contain data (skip empty lines and the Arduino's header)
            if line and not line.startswith('seq'):
                f.write(line + "\n")
                rows_collected += 1

                if rows_collected % 100 == 0:
                    print(f"Saved {rows_collected}/{num_samples} samples.")

    print("Data collection complete. Serial port closed.")
    print("Saved to:", filepath)
    
    return filepath


if __name__ == "__main__":
    csv_filepath = collect_serial_data(header=header, file_prefix=prefix, num_samples=N, port=port)