# Foot Mounted IMU Tracking System

This repository tracks the embedded development and hardware characterization of a 6 DOF (Accel + Gyro) tracking system using the BMI270 IMU on an nRF52840 (Arduino Nano 33 BLE Rev2). 

## Engineering Log & Hardware Characterization

### 1. I2C Read Path Optimization (10,394 µs → 477 µs)
**Measurement:** Initial loop timings using the stock `Arduino_BMI270_BMM150` wrapper library yielded an I2C read cost of 10,488 µs, consistently missing the 5,000 µs (200 Hz) deadline budget.

**Analysis:** By testing the bus at both 100 kHz and 400 kHz, fixed software overhead was separated from physical bus transmission time. This relationship is modeled using a system of two equations:

$$4230 = F + B$$
$$2313 = F + \frac{B}{4}$$

* **$F$**: Fixed CPU Time (the time the Arduino spends executing the bloated library code).
* **$B$**: Bus Time (the time the data spends physically traveling on the copper wire at 100 kHz).

This revealed ~1,674 µs of fixed CPU overhead per read. A review of the library source code showed that `bmi2_get_sensor_data` was being called twice per iteration, dragging redundant bytes across the bus each time.

<table>
  <tr>
    <td width="50%">
      <img width="100%" alt="Reading times for bus (Wire1) at 100kHz" src="https://github.com/user-attachments/assets/6940bc39-431a-4fba-88db-e34e823e8b14" />
    </td>
    <td width="50%">
      <img width="100%" alt="Reading times for bus (Wire1) at 400kHz" src="https://github.com/user-attachments/assets/f8b7f2e9-3689-4e81-a532-eccc297a67d3" />
    </td>
  </tr>
  <tr>
    <td align="center"><em>I2C mean: 10394 µs, Wire1 I2C bus (f) = 100kHz</em></td>
    <td align="center"><em>I2C mean: 3736 µs, Wire1 I2C bus (f) = 400kHz</em></td>
  </tr>
</table>

**Decision:** Bypassed the high overhead library wrapper in favor of raw register level access over `Wire1`. Replaced six separate API calls with a single, contiguous 12 byte burst read starting at register `0x0C` over a 400 kHz bus.

**Result:** Read time dropped to 477 µs (a 22× speedup), consuming only 27.6% of the loop budget with zero missed deadlines.
<img width="900" height="300" alt="image" src="https://github.com/user-attachments/assets/75c24329-0ce5-4d7b-a27a-eafdbd623e45" />

### 2. Sensor Configuration Discovery 
**Measurement:** Initial data logs revealed a 50.6% duplicate frame rate and physical signal clipping.

**Analysis:** The stock library shipped with a 100 Hz Output Data Rate (ODR) and a ±4 g range hardcoded, silently starving the 200 Hz loop of fresh data.

**Decision:** Bypassed the library initialization. Wrote directly to the hardware configuration registers (`0x40`, `0x41`, `0x42`) to explicitly force the accelerometer and gyroscope to a 200 Hz ODR, widen the range to ±16 g, and lock in the hardware OSR2 filter. 

**Result:** Three independent predictions were verified empirically:
* The duplicate frame fraction collapsed from 50.6% to 0%.
* The quantization step quadrupled to 0.0004 g, revealing the true hardware LSB natively for the first time.
* Because the LSB (0.49 mg) sits safely below the datasheet noise floor (~1.5 mg RMS at 200 Hz), the ±16 g range was secured without losing real data to quantization noise.

### 3. Real World Gait Validation
**Measurement:** Conducted dynamic walk and heel strike tests to validate sensor configurations against physical human gait.

**Result:** 
* **Range Justification:** Peak walking magnitude reached 6.33 g, while a hard heel strike hit 11.12 g, empirically justifying the ±16 g accelerometer range (a ±8 g configuration would have clipped). Peak gyro swing reached 860 dps, validating the ±2000 dps range.
* **Axis Frame Establishment:** Discarded the stock library's axis remap. A physical gravity/rotation consistency test proved the chip's native right handed coordinate frame was proper. 
* **Z Axis Characterization:** A two orientation flip test decomposed a 2.14% gravity magnitude anomaly into a 1.22% physical bias and a 0.92% scale error.
* **The ZARU Justification:** Measured a static Gyro Z axis bias of 0.144 dps. This equates to 8.7°/min of yaw drift, providing the quantitative justification for requiring a Zero Angular Rate Update (ZARU) algorithm to correct heading drift during the stance phase.

<p align="center">
  <em><img width="720" height="360" alt="image" src="https://github.com/user-attachments/assets/f04756c7-8e61-4543-9f0b-0705b5416ab2" /></em>
</p>


### 4. Zero Velocity Window (ZVW) Detection
**Objective:** Build a robust algorithm to identify the exact moments the foot is perfectly still during the stance phase to allow for instantaneous velocity resets (ZUPT).

**Method:** Constructed a three condition detector evaluating sample by sample data. The conditions require the acceleration magnitude to sit within a tight 1.0 g band, the gyroscope magnitude to fall below a maximum threshold, and the trailing rolling variance to remain quiet. These conditions must hold true for a minimum dwell time of 20 consecutive samples to reject mid air transients.

**Evaluation:** The algorithm was tuned exclusively on a manually labeled long walk dataset. It was then evaluated against a completely unseen 20 meter walk to prove generalization and avoid overfitting.

**Result:** 
* **Accuracy:** Achieved a perfect 10/10 detection rate on the unseen validation data with zero false positives.
* **Boundary Precision:** Algorithm entry boundaries agreed with the manually labeled ground truth within ±3 samples. 
* **Conclusion:** This provides a mathematically proven, robust classifier for the integration pipeline.

<p align="center">
  <em><img width="1680" height="720" alt="image" src="https://github.com/user-attachments/assets/1f3dabdd-5b2a-4b7f-8eec-505351b550ad" />
</em>
</p>


## Performance Profiling & Optimization

### Hardware FPU Validation

The mapper's Mahony filter runs at a fixed 200 Hz, giving each iteration a hard
5,000 µs budget. To leave headroom for I2C polling and the BLE stack, hardware
floating point flags were enforced at the toolchain level
(`-mfpu=fpv4-sp-d16 -mfloat-abi=softfp`) and verified against a 500 iteration
float workload.

| Build configuration            | Work time | Loop budget consumed |
| :--------------------------- | --------: | -------------------: |
| Soft float (emulated)        |  ~889 µs  |               18.0 % |
| Hard float (Cortex M4F FPU)  |  ~101 µs  |                2.0 % |

**8.8× speedup**, reclaiming 16% of the loop budget for sensor I/O and wireless
transmission.

<table>
  <tr>
    <td width="50%">
      <img width="100%" alt="Serial output: 500 iteration float workload with the FPU disabled, averaging 889 µs" src="https://github.com/user-attachments/assets/5a07bafe-b757-4db4-8c8e-c90c9573093b" />
    </td>
    <td width="50%">
      <img width="100%" alt="Serial output: identical workload with hardware FPU enabled, averaging 101 µs" src="https://github.com/user-attachments/assets/5b871daf-a1e2-4c01-9bb2-32ab755d5e22" />
    </td>
  </tr>
  <tr>
    <td align="center"><em>Soft float (889 µs)</em></td>
    <td align="center"><em>Hard float (101 µs)</em></td>
  </tr>
</table>

### Thread Preemption Safety

The Nano 33 BLE runs Mbed OS beneath the sketch, so FPU register state must
survive context switches mid calculation. Across **120,000** iterations, work time
showed ~50 µs of preemption induced variance. Bit for bit comparison of the
resulting floats yielded **0 mismatches**, confirming the scheduler correctly preserves FPU context during thread preemption.
