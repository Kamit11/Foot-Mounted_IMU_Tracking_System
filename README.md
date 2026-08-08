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
