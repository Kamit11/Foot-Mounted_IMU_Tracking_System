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
    instant_quiet = acc_cond & gyro_cond & var_cond

    if instant_quiet:
        state.dwell_counter += 1
    else:
        state.dwell_counter = 0

    # been quiet for DWELL samples?
    state.is_zvw = (state.dwell_counter >= DWELL)
    return state.is_zvw

def update_mahony(state: FilterState, ax: float, ay: float, az: float, gx: float, gy: float, gz: float, dt: float, is_zvw: bool, Kp: float = 2.0, Ki: float = 0.5):
    """
    Updates the quaternion orientation.
    """


    pass

def update_kinematics(state: KinematicsState, q: np.ndarray, ax: float, ay: float, az: float, dt: float, is_zvw: bool):
    """
    Rotates acceleration, removes gravity, and integrates to velocity and position.
    """
    if is_zvw:
        # state.velocity
        return

    qw, qx, qy, qz = q
    vx, vy, vz = ax, ay, az

    # 3D Quaternion Rotation Math (v_new = q * v * q^-1)
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)

    # this is the rotated vector
    rx = vx + qw * tx + (qy * tz - qz * ty)
    ry = vy + qw * ty + (qz * tx - qx * tz)
    rz = vz + qw * tz + (qx * ty - qy * tx)
