# Foot-Mounted IMU Tracking System

This repository tracks the embedded development and hardware characterization of a 6-DOF (Accel + Gyro) tracking system using the BMI270 IMU on an nRF52840 (Arduino Nano 33 BLE Rev2). 

## Engineering Log & Hardware Characterization

*Rule: Measurements drive decisions and quantify limits. Measure, don't assume.*

### 1. I²C Read Path Optimization (10,394 µs → 477 µs)
**Measurement:** Initial loop timings using the stock `Arduino_BMI270_BMM150` wrapper library yielded an I²C read cost of 10,488 µs, consistently missing the 5,000 µs (200 Hz) deadline budget.

**Analysis:** By testing the bus at both 100 kHz and 400 kHz, fixed software overhead was separated from physical bus transmission time using a system of two equations (`4230 = F + B` and `2313 = F + B/4`). This revealed ~1,674 µs of fixed CPU overhead per read. A review of the library source code showed that `bmi2_get_sensor_data` was being called twice per iteration, dragging redundant bytes across the bus each time.

**Decision:** Bypassed the high-overhead library wrapper in favor of raw register-level access over `Wire1`. Replaced six separate API calls with a single, contiguous 12-byte burst read starting at register `0x0C` over a 400 kHz bus.

**Result:** Read time dropped to 477 µs (a 22× speedup), consuming only 27.6% of the loop budget with zero missed deadlines.

### 2. Sensor Configuration Discovery 
**Measurement:** Initial data logs revealed a 50.6% duplicate frame rate and physical signal clipping.
**Analysis:** The stock library shipped with a 100 Hz Output Data Rate (ODR) and a ±4 g range hardcoded, silently starving the 200 Hz loop of fresh data.
**Decision:** Bypassed the library initialization. Wrote directly to the hardware configuration registers (`0x40`, `0x41`, `0x42`) to explicitly force the accelerometer and gyroscope to a 200 Hz ODR, widen the range to ±16 g, and lock in the hardware OSR2 filter. 
**Result:** Three independent predictions were verified empirically:
* The duplicate frame fraction collapsed from 50.6% to 0%.
* The quantization step quadrupled to 0.0004 g, revealing the true hardware LSB natively for the first time.
* Because the LSB (0.49 mg) sits safely below the datasheet noise floor (~1.5 mg RMS at 200 Hz), the ±16 g range was secured without losing real data to quantization noise.

### 3. Floating Point Unit (FPU) Context
**Measurement:** Ran an FPU benchmark to determine if float operations inside the loop would be compromised or corrupted by RTOS scheduling.
**Result:** Verified empirically that float variables successfully survive loop preemption on the nRF52840.

## Performance Profiling & Optimization

### Hardware FPU Validation

The mapper's Mahony filter runs at a fixed 200 Hz, giving each iteration a hard
5,000 µs budget. To leave headroom for I²C polling and the BLE stack, hardware
floating point flags were enforced at the toolchain level
(`-mfpu=fpv4-sp-d16 -mfloat-abi=softfp`) and verified against a 500 iteration
float workload.

| Build configuration          | Work time | Loop budget consumed |
| :--------------------------- | --------: | -------------------: |
| Soft-float (emulated)        |  ~889 µs  |               18.0 % |
| Hard-float (Cortex-M4F FPU)  |  ~101 µs  |                2.0 % |

**8.8× speedup**, reclaiming 16% of the loop budget for sensor I/O and wireless
transmission.

<table>
  <tr>
    <td width="50%">
      <img width="100%" alt="Serial output: 500-iteration float workload with the FPU disabled, averaging 889 µs" src="https://github.com/Kamit11/foot-mounted-inertial-mapper/blob/master/data/FPU_Benchmark/fpu_disabled_benchmark_01-08-2026_21-40-16_dual_plot.png" />
    </td>
    <td width="50%">
      <img width="100%" alt="Serial output: identical workload with hardware FPU enabled, averaging 101 µs" src="https://github.com/Kamit11/foot-mounted-inertial-mapper/blob/master/data/FPU_Benchmark/fpu_enabled_benchmark_01-08-2026_21-45-09_dual_plot.png" />
    </td>
  </tr>
  <tr>
    <td align="center"><em>Soft-float - 889 µs</em></td>
    <td align="center"><em>Hard-float - 101 µs</em></td>
  </tr>
</table>

### Thread Preemption Safety

The Nano 33 BLE runs Mbed OS beneath the sketch, so FPU register state must
survive context switches mid calculation. Across **120,000** iterations, work time
showed ~50 µs of preemption induced variance. Bit for bit comparison of the
resulting floats yielded **0 mismatches**, confirming the scheduler correctly
preserves FPU context under lazy stacking.
