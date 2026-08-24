# Build Roadmap — Foot-Mounted Inertial Indoor Mapper

**Assumed background:** confident programmer (C# / Unity, Python), some bare-metal Arduino Uno, no prior exposure to sensor fusion, estimation, DSP, or BLE.

**Assumed effort:** ~20–25 hours/week over 10 weeks. If you can only do 12–15, execute the cut list in §Contingency from week 1 rather than discovering you're behind in week 8.

---

## Read This First: You Know More Than You Think

Almost every "foreign" concept in this project has a direct counterpart in Unity. The vocabulary is unfamiliar; the ideas are not.

| Project concept | You already know it as |
|---|---|
| Body frame vs. global frame | `transform.localPosition` vs `transform.position`; `TransformDirection()` |
| Orientation quaternion | `Quaternion` / `transform.rotation` |
| Rotating a vector into world space | `transform.rotation * localVector` |
| Fixed-rate sensor loop @ 200 Hz | `FixedUpdate()` with `Time.fixedDeltaTime = 0.005` |
| Integration: accel → velocity → position | `velocity += accel * dt; position += velocity * dt` — exactly what a Rigidbody does |
| Drift from accumulated float error | Why your Unity physics jitters after long play sessions |
| Extruding a 2D polygon into a 3D block | Mesh generation from a vertex loop |

The genuinely new material is narrower than it looks:

1. **Sensors lie** — every measurement has noise, bias, and scale error, and you must model that.
2. **Filtering** — combining two bad signals into one good one.
3. **Observability** — knowing which errors your measurements *can* correct and which they cannot.
4. **I²C and BLE** — two communication protocols.

That's the whole syllabus. Four things.

---

## Working Method (applies to every week)

**Git from day one.** Firmware and analysis in one repo. Commit before every experiment.

**Every log file is data.** Naming scheme: `YYYYMMDD_HHMM_description.csv`. Keep a plain-text lab notebook: what you did, what the conditions were, what you saw. In week 9 you will need to know which log was "carpet, slow walk, tight mount" and you will not remember.

**One question per experiment.** Change one thing, measure, write it down.

**Plot everything.** You cannot debug an estimator by reading numbers. Every stage of the pipeline gets a plot before you move on.

**Verification gates are hard gates.** Each phase ends with a measurable criterion. Do not proceed past a failed gate by telling yourself you'll fix it later — errors in this pipeline compound, and a bad stance detector in week 3 becomes an unexplainable map failure in week 9.

---

# Phase 1 — Weeks 1–2: Get Trustworthy Data Out of the Board

**Goal:** A 200 Hz stream of correctly-scaled, correctly-timestamped IMU data landing in a CSV file, plus a rigid shoe mount. No algorithms yet.

This phase looks boring and is the highest-leverage two weeks in the project. Every later phase assumes the data is clean. If it isn't, you will spend week 6 debugging an estimator that was never the problem.

### Concepts to learn

**I²C.** A two-wire bus where a master addresses a slave by a 7-bit address and reads/writes numbered 8-bit registers. Everything a sensor can tell you or be told is a register. Learn: address, register map, read/write transaction, the concept of a *configuration register* vs a *data register*.

> Note for the Nano 33 BLE Sense Rev2: the onboard sensors sit on an internal I²C bus, which may not be the default `Wire` instance. Find out which one your library uses before attempting raw register access.

**Sensor ranges and resolution.** An accelerometer configured for ±4 g physically cannot report 6 g — it clips silently and the output still looks like a plausible number. Same for gyro at ±1000 °/s. You must know your configured range and confirm your motion fits inside it.

**ODR (Output Data Rate)** — how often the sensor produces a new sample internally. Reading faster than the ODR returns the same sample twice. Reading slower loses samples. Your loop rate and the ODR must be deliberately matched.

**Fixed-rate loops and jitter.** `delay(5)` does not give you 200 Hz — it gives you 5 ms *plus* however long your loop body took. Use `micros()` and a target-time accumulator. Jitter matters because you'll multiply by `dt`; if `dt` is wrong, your integration is wrong.

### Build tasks, in order

1. **Toolchain sanity.** Blink, then serial print. Confirm you can flash and read output reliably.
2. **Read the IMU with the stock library** (`Arduino_BMI270_BMM150`), print at 10 Hz. Sanity-check: board flat → accel ≈ (0, 0, 1) g in *some* axis order; find out which. Rotate it and confirm the axes behave as you'd expect.
3. **Determine your actual ODR and configured ranges.** Two ways, do both:
   - Read the configuration registers directly and decode them against the BMI270 datasheet.
   - Empirically: count samples per second; drop the board a few cm onto a cushion and look for a flat-topped plateau in the acceleration trace, which is clipping.
4. **Fix the ranges if needed.** Target: accel ±8 g or ±16 g, gyro ±2000 °/s. This may require writing BMI270 registers directly, past the library. This is your first real embedded task.
5. **Build the 200 Hz fixed-rate loop.** Measure jitter: log `micros()` deltas for 10 seconds, plot the histogram. You want a tight spike at 5000 µs.
6. **Serial logging.** CSV with a device-side timestamp in µs — *never* use host arrival time, USB buffering will lie to you. Format: `t_us, ax, ay, az, gx, gy, gz, mx, my, mz`.
7. **Python capture script.** `pyserial` → file. Add a sample-counter column so you can detect drops.
8. **Build the mount.** Rigid plate (3 mm plywood or printed PLA), board bolted or double-sided-taped down hard, plate laced into the shoe through the laces, cable strain-relieved up the leg to a power bank in your pocket. Grip the board and try to wiggle it relative to the shoe — if it moves, the project cannot work.
9. **First walking log.** 60 seconds, normal walk, flat floor.

### Verification gate

- 60-second walk logged with **zero dropped samples**.
- Timestamp jitter **< 0.5 ms** at 200 Hz.
- **No clipping**: max |accel| during heel strike is comfortably inside your configured range; no flat-topped peaks.
- Board is immovable relative to the shoe.

### What you should be able to see

Open the log in Python and plot acceleration magnitude over 5 seconds of walking. You should see a repeating pattern with a sharp spike (heel strike) and a quiet flat region (foot planted). **Spend real time looking at this plot.** Learning to read gait visually is what makes weeks 3–4 tractable.

---

# Phase 2 — Weeks 3–4: The Estimator, Offline in Python

**Goal:** Recorded walking data in, a straight-line trajectory out, with measured error against a tape measure. Nothing runs on the board this phase.

### Concepts to learn

**Coordinate frames.** The sensor measures in *its own* frame, which tumbles with your foot. You want motion in a *fixed world* frame. Converting between them is the entire purpose of the attitude filter. Unity bridge: this is `transform.TransformDirection(localVec)` — and the attitude filter's job is to figure out what `transform.rotation` currently is, using only measurements.

**Why an accelerometer can't just tell you acceleration.** It measures *specific force* — real acceleration plus the reaction to gravity. Sitting on a table it reads 1 g upward. You cannot separate "moving" from "tilted" from a single sample. This is the founding problem of the whole field.

**Gyro integration and drift.** Integrating angular rate gives orientation change. It's excellent over one second and garbage over one minute, because a small constant bias integrates into a growing angle error.

**Complementary filtering.** The gyro is good short-term, bad long-term. The accelerometer's *average* direction is a reliable long-term "down" reference but is useless short-term because motion contaminates it. Trust the gyro at high frequency and the accelerometer at low frequency. That's a complementary filter. **Mahony** is a well-behaved formulation of exactly this idea using quaternions and a proportional-integral correction.

**Bias.** A gyro at rest doesn't read zero — it reads some small constant offset that drifts with temperature. This is the enemy. Naming it and estimating it is half the project.

**Double integration and why it explodes.** Accel error → integrated once → velocity error that *never goes away* → integrated again → position error growing without bound. This is why ZUPT exists.

**ZUPT.** During stance, true velocity is zero. Whatever velocity your integrator holds is pure error. Set it to zero. This is the whole trick, and it is startlingly simple once you see it.

### Build tasks, in order

Each step produces a plot. Do not skip the plots.

1. **Load and explore.** numpy + matplotlib. Plot all six channels for a 10-second walk. Identify by eye: heel strike, swing phase, stance phase.
2. **Hand-label stance.** On one 20-step log, manually record the sample ranges where the foot is planted. This is your ground truth for tuning the detector — a small investment that saves days.
3. **Stance detector.** Three simultaneous conditions, all must hold:
   - accel magnitude within a band around 1 g,
   - rolling variance of accel magnitude below a threshold,
   - gyro magnitude below a threshold,
   - held for a minimum dwell (~4–10 samples).
   
   Overlay detected stance on your plot as shaded regions. Tune thresholds against your hand labels. **Do not proceed until this is >98% accurate.**
4. **Gyro-only attitude.** Integrate angular rate into a quaternion. Plot resulting pitch/roll over a 60 s stationary log. Watch it drift. Understand *why* before you fix it.
5. **Mahony filter.** Add accelerometer correction. Verify:
   - stationary: pitch/roll stable over 60 s,
   - tilt to 45°, hold, return: angle tracks and comes back to zero,
   - during walking: pitch/roll are smooth and plausible.
6. **Gravity removal.** Rotate measured accel into the global frame using your quaternion, subtract gravity. Verify: while the foot is planted, this should be ≈ 0 on all axes. If it isn't, your attitude estimate is bad — go back to step 5.
7. **Integrate to velocity, without ZUPT.** Plot. It explodes. Good. Now you understand the problem viscerally.
8. **Add ZUPT.** Zero the velocity whenever the stance detector fires. Re-plot. Velocity should now look like a series of clean bumps, each returning to zero. **This is the moment the project starts working.**
9. **Integrate velocity to position.** Extract a per-step displacement vector.
10. **Straight-line validation.** Tape-measure a 20 m hallway. Walk it. Compare computed distance to actual. Repeat 5 times.

### Verification gate

- Stance detection **> 98%** vs hand-labelled ground truth.
- Straight-line distance error **< 10%** over 20 m, consistent across runs. (Tightens to 5% after week 5–6 corrections.)
- Zero-velocity residual during stance is visibly near zero.

### Where you will get stuck

- **Axis conventions.** Sensor axes, gravity sign, and rotation handedness will bite you at least once. When something is inverted, print the quaternion for a known orientation and reason it out — don't flip signs randomly until it works.
- **Mahony gains.** Too high and walking motion corrupts your attitude; too low and it drifts. Start low, tune on recorded data.
- **`dt`.** Use the actual timestamp deltas from the log, not a nominal 0.005.

---

# Phase 3 — Weeks 5–6: Heading

**Goal:** Turn a banana-shaped path into a closed room outline. This is the intellectual core of the project.

### Concepts to learn

**Observability.** The single most important idea here. ZUPT works because "I am stationary" contradicts "my velocity is 2 m/s" — the measurement *constrains* the error. But "I am stationary" says nothing about which direction you're facing. Yaw error is therefore **unobservable** from ZUPT, and no amount of ZUPT will fix it. Being able to explain this in an interview is worth more than the rest of the project combined.

**ZARU (Zero Angular Rate Update).** During stance, true angular rate is zero, so the gyro reading *is* the bias. Feed that into a slow-moving bias estimate and subtract it from all subsequent readings. You are already detecting stance, so this is nearly free.

**Loop closure.** Walk a closed path, end where you began. The gap between computed start and end is your total accumulated error. Distribute it backwards across the path in proportion to distance travelled. This is a global correction — it's why the host PC does it and not the microcontroller.

**Dominant-direction (Manhattan) snapping.** Histogram your per-step headings modulo 90°. Real rooms cluster hard around a single grid. Find the grid, snap the segments to it. Applied explicitly and labelled as such, this is legitimate prior knowledge, not cheating.

**Magnetometer reality.** Hard-iron and soft-iron distortion are the *calibratable* problems. The uncalibratable problem is that indoor buildings contain steel, and the field you measure near the floor bears little relation to Earth's. You will measure this, not assume it.

### Build tasks

1. **Baseline the damage.** Walk a closed rectangular loop (a room, or a hallway circuit). Plot the raw path. Measure the closure gap. Quantify the drift rate in °/min.
2. **Implement ZARU.** Estimate gyro bias during stance phases with a slow filter; subtract continuously. Re-run the same log. Plot before/after side by side. Quantify the improvement — **this plot goes in your portfolio.**
3. **Loop closure correction.** Detect or manually mark loop closure, distribute residual error along the path proportionally to cumulative distance. Re-plot.
4. **Heading histogram and snapping.** Extract per-step headings, histogram them mod 90°, find the dominant offset, snap. Re-plot.
5. **Magnetometer characterization.** This is a standalone experiment and a standalone deliverable:
   - Calibrate hard/soft iron outdoors (rotate the board through all orientations, fit an ellipsoid, or start with a simple min/max offset calibration).
   - Walk your test room logging magnetometer heading alongside gyro-derived heading.
   - Plot the disagreement as a function of position in the room.
   - Produce a heatmap or annotated floor plan of "where the compass lies and by how much."

### Verification gate

- Closed-loop closure error **< 1.5 m on a 20 m loop**, before correction.
- Rectangular room reconstructs as visibly rectangular after correction.
- Magnetometer error characterized with data, not assertion.

---

# Phase 4 — Weeks 7–8: Port to C++ and Go Wireless

**Goal:** The algorithm runs on the board; step vectors arrive at the host over BLE; the live map matches the offline map.

### Concepts to learn

**Float, not double.** The Cortex-M4F has hardware single-precision float and *no* double-precision unit. A stray `double` silently drops you to software emulation and destroys your timing budget. On Arduino, `1.0` is a double and `1.0f` is a float — this matters.

**Structuring embedded code as a state machine.** No dynamic allocation, no `String`, fixed-size buffers, everything preallocated.

**Struct packing and endianness.** You're serializing a C struct into bytes and parsing it in Python with `struct.unpack`. Byte alignment and padding will surprise you once. Use explicit-width types (`int16_t`, `float`) and consider `__attribute__((packed))`.

**BLE GATT, minimum viable version.** A *peripheral* (your board) advertises a *service* (a UUID grouping related data) containing a *characteristic* (a data slot with a UUID). A *central* (your laptop) connects, subscribes to *notifications*, and receives a packet each time the peripheral updates it. That's all you need. Ignore the other 95% of BLE.

**Async Python.** `bleak` is asyncio-based. If you've never written `async def` / `await`, spend an hour on it before touching BLE.

### Build tasks

1. **Refactor the Python first.** Restructure your pipeline into pure functions with an explicit state struct, processing one sample at a time — mirroring how the C++ must work. Verify the refactor produces identical output to the batch version. This makes the port a transcription rather than a redesign.
2. **Build a replay harness.** A mode where the firmware receives recorded samples over serial instead of reading the IMU, runs the pipeline, and prints results. This lets you compare C++ output against Python output on *identical input* — the single most valuable debugging tool in this phase.
3. **Port module by module**, verifying each against Python via replay: attitude filter → gravity removal → stance detector → ZUPT/ZARU → step vector extraction.
4. **Live on-board test.** Same walk, compare on-board output to offline processing of the raw log.
5. **Define the packet.** Sequence number, ΔX, ΔY, heading, stance duration, quality flag, state flag. Keep it under 20 bytes to fit the default BLE MTU without fragmentation.
6. **BLE peripheral.** Custom service + notify characteristic using `ArduinoBLE`.
7. **`bleak` central.** Connect, subscribe, parse packets, append to path.
8. **Live plot.** matplotlib updating per step is fine at 2 Hz.

### Verification gate

- Firmware output on a replayed dataset matches Python within tight numerical tolerance.
- A live BLE walk produces the same map as offline processing of the same walk.
- Loop time stays within budget at 200 Hz with BLE active — measure it.

---

# Phase 5 — Weeks 9–10: Gesture, Polygons, Render, Writeup

**Goal:** The complete demo, plus the documentation that makes it count.

### Concepts to learn

**Thresholding with hysteresis and debounce.** A raw proximity value crossing a threshold will chatter. You need: an on-threshold, a lower off-threshold (hysteresis), a minimum duration, and a refractory period before re-triggering. This is the same pattern as button debouncing you'd have hit on the Uno, one level up.

**Bus scheduling.** The APDS-9960 shares I²C with the IMU. A proximity read must never delay an IMU sample. Poll it at ~10 Hz in the slack time after the IMU read, and measure the worst-case loop time.

**Polygon handling and extrusion.** Close the vertex loop, check it isn't self-intersecting, extrude along Z into a prism mesh.

**The Interaction State Machine.** The system requires a seamless way to distinguish between the room boundary, furniture objects, and the physical steps taken to walk between them. This is managed via a single toggle, a polygon counter, and a default `TRANSIT` state:
*   **The Toggle:** A physical trigger (e.g., APDS swipe) acts as a pure binary toggle. An odd trigger opens a polygon; an even trigger closes it.
*   **The Counter:** A counter increments every time a polygon closes. 
*   **The Origin & Boundary:** Polygon 0 is defined as the room boundary. The map coordinate frame is born the moment Polygon 0's first vertex is opened.
*   **TRANSIT as the Default State:** `TRANSIT` is not a triggered mode; it is the default resting state. Whenever no polygon is currently open, the system is in `TRANSIT`. The estimator underneath runs continuously and unbroken—step vectors are tracked for displacement but are appended to nothing, ensuring the floor plan and objects remain in a single, unified coordinate frame.


### Build tasks

1. **Characterize the sensor.** Log raw proximity while passing your hand over the shoe at various speeds and distances. Plot it. Choose thresholds from the data.
2. **Trigger state machine.** Threshold + hysteresis + debounce + refractory. Test that walking, sunlight, and trouser legs don't false-trigger. Test it 50 times.
3. **Wire the state flag** into the BLE packet.
4. **Host polygon capture (Toggle + Counter Model).** Implement the state machine where the default state is `TRANSIT`. The first trigger opens Polygon 0. The second trigger applies the polygon closure constraint (connecting the last vertex to the first) and returns the system to `TRANSIT`. Subsequent triggers open and close Polygons 1, 2, etc. Tracking runs continuously regardless of the state. 
5. **PyVista render.** Render Polygon 0 as the 2D floor boundary. Render Polygons $\ge 1$ as extruded 3D solid blocks. `TRANSIT` steps are drawn as neither wall nor block.
6. **Validation runs.** Map a real room. Tape-measure each wall and each piece of furniture. Tabulate computed vs actual.
7. **Writeup.** Lead with the error table. The render is the thumbnail; the numbers are the substance.

### Final deliverables

- Working end-to-end demo (video).
- Error table: per-wall and per-object, computed vs measured.
- Before/after ZARU drift plot.
- Magnetometer indoor error characterization.
- Stance detection accuracy figure.
- Repo with firmware, analysis code, and datasets.
- Writeup explaining the heading problem and your solution to it.

---

## Contingency / Cut List

Execute in this order if you fall behind. Each cut removes scope without breaking what's already built:

1. **Gesture input → keyboard press on the host.** Costs nothing conceptually; saves a week.
2. **PyVista → matplotlib 2D with shaded object footprints.** The estimation work is the project; the renderer isn't.
3. **Manhattan snapping.** Nice-to-have polish.
4. **Live BLE → offline-only processing.** Ugly to lose but the algorithm still demonstrates fully. Do not cut this before the other three.

**Never cut:** stance detection quality, ZUPT, ZARU, or the validation measurements. Those *are* the project.

---

## Background Reading

Worth an afternoon each, roughly in order of when you'll need them. Search for these by name rather than trusting any URL I'd give you:

- **Foxlin (2005), "Pedestrian Tracking with Shoe-Mounted Inertial Sensors"** — the founding paper for this exact approach. Read it in week 3.
- **The OpenShoe project (KTH)** — open-source foot-mounted INS, papers by Nilsson and Skog. Read their treatment of stance detection specifically.
- **Madgwick's report on IMU orientation filters** — the clearest practical introduction to attitude filtering, and it covers Mahony's approach alongside his own.
- **Any solid "quaternions for rotation" primer.** You have Unity intuition already; you now need the math underneath it.
- **`bleak` documentation** — week 7, not before.

---

## What Success Looks Like at Each Gate

| End of | You can demonstrate |
|---|---|
| Week 2 | Clean 200 Hz data, no clipping, rigid mount |
| Week 4 | A straight-line walk measured to within 10% |
| Week 6 | A closed room outline, with quantified drift correction |
| Week 8 | Live wireless mapping matching offline results |
| Week 10 | Full demo with a validation table |

If you hit week 6's gate, the project is a success regardless of what happens after. Everything past that point is presentation.
