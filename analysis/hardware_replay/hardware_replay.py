import struct
import time

import pandas as pd
import serial

COM_PORT = 'COM3'
BAUD_RATE = 115200          # ignored by native USB CDC, but pyserial wants a value
MAX_RETRIES = 3

SYNC = b'\xAA\x55'
FMT = '<IIffffff'           # seq, t_us, ax, ay, az, gx, gy, gz  -> 32 bytes
assert struct.calcsize(FMT) == 32

input_csv = 'data/measured_closed_loops/closed_loop_18-08-2026_20-44-45_3_CW_18m.csv'
output_path = 'data/golden_references/hardware_stream_output.csv'

df = pd.read_csv(input_csv, skipinitialspace=True)


def build_frame(row):
    """Pack one IMU sample into the 35-byte wire frame."""
    data = struct.pack(
        FMT,
        int(row['seq']), int(row['t_us']),
        float(row['ax']), float(row['ay']), float(row['az']),
        float(row['gx']), float(row['gy']), float(row['gz']),
    )
    checksum = 0
    for b in data:
        checksum ^= b
    return SYNC + data + bytes([checksum])


hardware_stream = []
print(f"Connecting to {COM_PORT}...")

try:
    with serial.Serial(COM_PORT, BAUD_RATE, timeout=2) as ser:
        deadline = time.time() + 10
        while time.time() < deadline:
            if ser.readline().decode('utf-8', errors='replace').strip() == 'READY':
                print("Connected to Arduino successfully")
                break
        else:
            raise RuntimeError("Never saw READY from the Arduino")

        for index, row in df.iterrows():
            frame = build_frame(row)
            expected_seq = int(row['seq'])

            for attempt in range(MAX_RETRIES):
                ser.write(frame)
                response = ser.readline().decode('utf-8', errors='replace').strip()
                parts = response.split(',')

                if len(parts) == 10 and int(parts[0]) == expected_seq:
                    hardware_stream.append({
                        'seq': int(parts[0]),
                        'is_zvw': int(parts[1]),
                        'instant_quiet': int(parts[2]),
                        'qw': float(parts[3]), 'qx': float(parts[4]),
                        'qy': float(parts[5]), 'qz': float(parts[6]),
                        'pos_x': float(parts[7]), 'pos_y': float(parts[8]), 'pos_z': float(parts[9]),
                    })
                    break

                print(f"row {index} (seq {expected_seq}) attempt {attempt + 1} failed: {response!r}")
                time.sleep(0.05)
                ser.reset_input_buffer()
            else:
                # Abort rather than silently drop a sample. A gap in the stream is
                # exactly what would poison the golden reference.
                raise RuntimeError(
                    f"Row {index} (seq {expected_seq}) failed {MAX_RETRIES} times - aborting."
                )

            if index % 500 == 0:
                print(f"Processed {index} / {len(df)} rows...")

except serial.SerialException:
    print(f"Failed to connect to {COM_PORT}. Is it open in another terminal?")
    raise

df_hw = pd.DataFrame(hardware_stream)

# Hard proof that nothing was dropped, duplicated, or reordered.
assert len(df_hw) == len(df), f"{len(df_hw)} responses for {len(df)} input rows"
assert (df_hw['seq'].values == df['seq'].values).all(), "seq mismatch: stream desynchronised"

df_hw.to_csv(output_path, index=False)
print(f"\nHardware replay complete, {len(df_hw)}/{len(df)} rows verified. Saved to {output_path}")