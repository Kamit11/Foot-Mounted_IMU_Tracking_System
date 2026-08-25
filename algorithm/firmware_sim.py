import numpy as np
import math
from dataclasses import dataclass, field

# ======================================
# CONSTANT VARIABLES:
# ======================================
ACC_DEVIATION = 0.3     # Allowable deviation from 1.0g
GYRO_LIMIT = 75.0       # Maximum dps
VAR_LIMIT = 0.06        # Maximum rolling variance
VAR_WINDOW = 15         # Variance window to calculate
DWELL = 20              # Minimum consecutive samples
# ======================================


# ======================================
# C++ STRUCT SIMULATION
# ======================================

@dataclass
class ZVWState:
    """
    Simulates the C++ state for Zero Velocity Window detection.
    Uses a ring buffer for variance to simulate streaming as opposed of batch processing.
    """
    acc_ring_buffer: np.ndarray = field(default_factory=lambda: np.zeros(VAR_WINDOW, dtype=np.float32))
    ring_index: int = 0
    is_buffer_full: bool = False
    dwell_counter: int = 0
    is_zvw: bool = False
    instant_quiet: bool = False


@dataclass
class FilterState:
    """
    Simulates the Mahony Filter state.
    Holds the current quaternion and the integral error.
    """
    # Initialize flat and forward (w, x, y, z)
    q: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32))
    # Integral error
    eInt: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))

    is_initialized: bool = False
    init_sample_count: int = 0
    init_acc_accum: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    

@dataclass
class KinematicsState:
    """
    Simulates the integration state (Dead Reckoning).
    Holds the current velocity and global position.
    """
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))
    position: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))

    stance_onset_pos: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float32))

@dataclass
class SystemState:
    """
    The master struct that holds the entire state of the microcontroller.
    """
    zvw: ZVWState = field(default_factory=ZVWState)
    mahony: FilterState = field(default_factory=FilterState)
    kinematics: KinematicsState = field(default_factory=KinematicsState)



def update_zvw(state: ZVWState, ax: float, ay: float, az: float, gx: float, gy: float, gz: float) -> bool:
    """
    Updates the ZVW state.
    Returns True if the foot is currently planted.
    """
    acc_mag = math.sqrt(ax**2 + ay**2 + az**2)
    gyro_mag = math.sqrt(gx**2 + gy**2 + gz**2)
    state.acc_ring_buffer[state.ring_index] = acc_mag

    state.ring_index += 1
    if state.ring_index >= state.acc_ring_buffer.size:
        state.ring_index = 0
        state.is_buffer_full = True

    # Rolling variance
    # [image-comments/image-20260824-174335-agyg8n.png]
    if state.is_buffer_full:
        # Pandas .var() uses N-1 (Bessel's correction) by default.
        mean_acc = np.sum(state.acc_ring_buffer) / VAR_WINDOW

        # subtracts mean_acc from each individual element (\(x_i - \bar{x}\)) 
        # and squares each result individually.
        acc_var = np.sum((state.acc_ring_buffer - mean_acc)**2) / (VAR_WINDOW - 1)

        var_cond = acc_var <= VAR_LIMIT
    else:
        var_cond = False

    acc_cond = abs(acc_mag - 1.0) <= ACC_DEVIATION
    gyro_cond = gyro_mag <= GYRO_LIMIT
    state.instant_quiet = acc_cond & gyro_cond & var_cond

    if state.instant_quiet:
        state.dwell_counter += 1
    else:
        state.dwell_counter = 0

    # been quiet for DWELL samples?
    state.is_zvw = (state.dwell_counter >= DWELL)
    return state.is_zvw

def update_mahony(state: FilterState, ax: float, ay: float, az: float, gx: float, gy: float, gz: float, dt: float, is_instant_quiet: bool, Kp: float = 2.0, Ki: float = 0.5):
    """
    Updates the quaternion orientation.
    """

    # calculate initial quaternion
    if not state.is_initialized:
        state.init_sample_count +=1
        state.init_acc_accum[0] += ax
        state.init_acc_accum[1] += ay
        state.init_acc_accum[2] += az

        if state.init_sample_count >= 100:
            mean_ax = state.init_acc_accum[0] / 100.0
            mean_ay = state.init_acc_accum[1] / 100.0
            mean_az = state.init_acc_accum[2] / 100.0
            norm = math.sqrt(mean_ax**2 + mean_ay**2 + mean_az**2)

            init_roll = math.atan2(mean_ay / norm, mean_az / norm)
            init_pitch = math.atan2(-mean_ax / norm, math.sqrt((mean_ay/norm)**2 + (mean_az/norm)**2))

            # Convert the angles into a starting quaternion
            # rotation quaternion = cos(phi/2) + sin(phi/2)(xi + yj + zk)
            cy = math.cos(0.0) # Yaw is 0, unobservable
            sy = math.sin(0.0)
            cp = math.cos(init_pitch * 0.5)
            sp = math.sin(init_pitch * 0.5)
            cr = math.cos(init_roll * 0.5)
            sr = math.sin(init_roll * 0.5)

            # rotate the quaternion
            state.q[0] = cr * cp * cy + sr * sp * sy #qw
            state.q[1] = sr * cp * cy - cr * sp * sy # qx
            state.q[2] = cr * sp * cy + sr * cp * sy # qy
            state.q[3] = cr * cp * sy - sr * sp * cy  # qz

            state.is_initialized = True

        # make sure we initialize the initial quaternion before calculating kinematics  
        else: return

    qw, qx, qy, qz = state.q[0], state.q[1], state.q[2], state.q[3]

    # Apply the permanent hardware bias estimate to every single sample, 
    # regardless of whether the foot is swinging or planted.
    # this is the corrected omega instead of the flawed gx, gy ,gz
    wx = math.radians(gx) + (Ki * state.eInt[0])
    wy = math.radians(gy) + (Ki * state.eInt[1])
    wz = math.radians(gz) + (Ki * state.eInt[2])

    acc_norm = math.sqrt(ax**2 + ay**2 + az**2)

    # only correct with accel if foot is perfectly still
    if acc_norm > 0.0 and is_instant_quiet:
        a_x = ax / acc_norm
        a_y = ay / acc_norm
        a_z = az / acc_norm

        # this is where the gyroscope thinks down is
        v_x = 2.0 * (qx * qz - qw * qy)
        v_y = 2.0 * (qw * qx + qy * qz)
        v_z = 1.0 - 2.0 * (qx**2 + qy**2)

        # error vector -> cross gyroscope down and accelerometer down
        e_x = (a_y * v_z) - (a_z * v_y)
        e_y = (a_z * v_x) - (a_x * v_z)
        e_z = (a_x * v_y) - (a_y * v_x)

        # Update the persistent bias estimate (integration)
        if Ki > 0.0:
            state.eInt[0] += e_x * dt
            state.eInt[1] += e_y * dt
            state.eInt[2] += e_z * dt

            # Clamp the accumulated error to a max of 2.0deg/s so that sudden weird
            # movements wont blow the integrator
            max_eInt_val = math.radians(2.0) / Ki
            state.eInt[0] = max(-max_eInt_val, min(max_eInt_val, state.eInt[0]))
            state.eInt[1] = max(-max_eInt_val, min(max_eInt_val, state.eInt[1]))
            state.eInt[2] = max(-max_eInt_val, min(max_eInt_val, state.eInt[2]))

        # Apply the real time Proportional nudge
        wx += (Kp * e_x)
        wy += (Kp * e_y)
        wz += (Kp * e_z)


    # Calulate q_dot - this is how we rotate a quaternion using
    # a given angular velocity (omega)
    # wx/y/z is the corrected gx/y/z
    q_dot_w = 0.5 * (-qx*wx - qy*wy - qz*wz)
    q_dot_x = 0.5 * ( qw*wx + qy*wz - qz*wy)
    q_dot_y = 0.5 * ( qw*wy - qx*wz + qz*wx)
    q_dot_z = 0.5 * ( qw*wz + qx*wy - qy*wx)

    # update current quaternion's rotation
    state.q[0] += q_dot_w * dt
    state.q[1] += q_dot_x * dt
    state.q[2] += q_dot_y * dt
    state.q[3] += q_dot_z * dt

    q_norm = math.sqrt(state.q[0]**2 + state.q[1]**2 + state.q[2]**2 + state.q[3]**2)

    # normalize to stay a rotation vector
    state.q[0] /= q_norm
    state.q[1] /= q_norm
    state.q[2] /= q_norm
    state.q[3] /= q_norm

def update_kinematics(state: KinematicsState, q: np.ndarray, ax: float, ay: float, az: float, dt: float, is_zvw: bool, dwell_counter: int):
    """
    Rotates acceleration, removes gravity, and integrates to velocity and position.
    """

    # take a snapshot
    if dwell_counter == 1:
        state.stance_onset_pos = np.copy(state.position)

    # rollback
    if dwell_counter == DWELL:
        state.position = np.copy(state.stance_onset_pos)
        state.velocity.fill(0.0)

    if is_zvw:
        state.velocity.fill(0.0)
        return

    g = 9.80665

    # quaternion rotation
    qw, qx, qy, qz = q[0], q[1], q[2], q[3]
    vx, vy, vz = ax, ay, az

    # 3D Quaternion Rotation Math (v_new = q * v * q^-1)
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)

    # this is the rotated vector
    rx = vx + qw * tx + (qy * tz - qz * ty)
    ry = vy + qw * ty + (qz * tx - qx * tz)
    rz = vz + qw * tz + (qx * ty - qy * tx)

    rz -= 1.0 # remove 1g

    # convert to ms2
    ax_ms2 = rx * g
    ay_ms2 = ry * g
    az_ms2 = rz * g

    # integrate ms2 accel to velocity
    vx_ms = ax_ms2 * dt
    vy_ms = ay_ms2 * dt
    vz_ms = az_ms2 * dt

    # Update velocity (v = v + a * dt)
    state.velocity[0] += vx_ms
    state.velocity[1] += vy_ms
    state.velocity[2] += vz_ms

    # integrate velocity to position
    # Update position (p = p + v_total * dt)
    state.position[0] += state.velocity[0] * dt
    state.position[1] += state.velocity[1] * dt
    state.position[2] += state.velocity[2] * dt

