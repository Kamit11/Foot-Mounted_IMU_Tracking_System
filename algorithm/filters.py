import numpy as np

def mahony_filter(ax, ay, az, gx, gy, gz, dt_array, zvw_mask, Kp=2.0, Ki=0.5, get_eInt_vals = False):
    # static initialization:
    # Find the average gravity vector over the first 100 samples (0.5s of standing still)
    mean_ax = np.mean(ax[:100])
    mean_ay = np.mean(ay[:100])
    mean_az = np.mean(az[:100])
    norm = np.sqrt(mean_ax**2 + mean_ay**2 + mean_az**2)
    
    # Calculate initial pitch and roll from that gravity vector
    init_roll = np.arctan2(mean_ay / norm, mean_az / norm)
    init_pitch = np.arctan2(-mean_ax / norm, np.sqrt((mean_ay / norm)**2 + (mean_az / norm)**2))
    
    # Convert the angles into a starting quaternion
    cy = np.cos(0.0) # Yaw is 0
    sy = np.sin(0.0)
    cp = np.cos(init_pitch * 0.5)
    sp = np.sin(init_pitch * 0.5)
    cr = np.cos(init_roll * 0.5)
    sr = np.sin(init_roll * 0.5)
    
    q = np.array([
        cr * cp * cy + sr * sp * sy, # qw
        sr * cp * cy - cr * sp * sy, # qx
        cr * sp * cy + sr * cp * sy, # qy
        cr * cp * sy - sr * sp * cy  # qz
    ])

    # Rest of the code from the Jupyter's notebook 02
    quaternions = np.zeros((len(dt_array), 4))
    quaternions[0] = q

    gx_rad = np.deg2rad(gx)
    gy_rad = np.deg2rad(gy)
    gz_rad = np.deg2rad(gz)

    eInt_x, eInt_y, eInt_z = 0.0, 0.0, 0.0

    e_ints = np.zeros((len(dt_array), 3))

    # filter loop
    for i in range(1, len(dt_array)):
        dt = dt_array[i]

        wx = gx_rad[i]
        wy = gy_rad[i]
        wz = gz_rad[i]

        # Apply the permanent hardware bias estimate to every single sample, 
        # regardless of whether the foot is swinging or planted.
        wx += (Ki * eInt_x)
        wy += (Ki * eInt_y)
        wz += (Ki * eInt_z)

        a_x, a_y, a_z = ax[i], ay[i], az[i]
        acc_norm = np.sqrt(a_x**2 + a_y**2 + a_z**2)
        
        # Only calculate errors and update estimates if the foot is perfectly still
        if acc_norm > 0.0 and zvw_mask[i]:
            a_x /= acc_norm
            a_y /= acc_norm
            a_z /= acc_norm

            qw, qx, qy, qz = q

            v_x = 2.0 * (qx * qz - qw * qy)
            v_y = 2.0 * (qw * qx + qy * qz)
            v_z = 1.0 - 2.0 * (qx**2 + qy**2)

            e_x = (a_y * v_z) - (a_z * v_y)
            e_y = (a_z * v_x) - (a_x * v_z)
            e_z = (a_x * v_y) - (a_y * v_x)

            # Update the persistent bias estimate (integration)
            if Ki > 0.0:
                eInt_x += e_x * dt
                eInt_y += e_y * dt
                eInt_z += e_z * dt

                # Clamp the accumulated error to a max of 2.0deg/s so that sudden weird
                # movements wont blow the integrator
                max_eInt_val = np.deg2rad(2.0) / Ki
                eInt_x = max(-max_eInt_val, min(max_eInt_val, eInt_x))
                eInt_y = max(-max_eInt_val, min(max_eInt_val, eInt_y))
                eInt_z = max(-max_eInt_val, min(max_eInt_val, eInt_z))

            # Apply the real time Proportional nudge
            wx += (Kp * e_x)
            wy += (Kp * e_y)
            wz += (Kp * e_z)


        # REMOVE THIS AFTER - FOR DEBUGGING PURPOSES!
        e_ints[i] = [Ki * eInt_x, Ki * eInt_y, Ki * eInt_z]

        # gyro integration
        qw, qx, qy, qz = q

        # Calulate q_dot - this is how a we rotate a quaternion using
        # a given angular velocity (omega)
        q_dot_w = 0.5 * (-qx*wx - qy*wy - qz*wz)
        q_dot_x = 0.5 * ( qw*wx + qy*wz - qz*wy)
        q_dot_y = 0.5 * ( qw*wy - qx*wz + qz*wx)
        q_dot_z = 0.5 * ( qw*wz + qx*wy - qy*wx)

        q[0] += q_dot_w * dt
        q[1] += q_dot_x * dt
        q[2] += q_dot_y * dt
        q[3] += q_dot_z * dt

        q = q / np.linalg.norm(q)
        quaternions[i] = q

    return e_ints if get_eInt_vals else quaternions


def quaternions_to_euler(quats):
    w, x, y, z = quats[:, 0], quats[:, 1], quats[:, 2], quats[:, 3]
    
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x**2 + y**2)
    roll = np.arctan2(sinr_cosp, cosr_cosp) 
    
    sinp = 2 * (w * y - z * x)
    sinp = np.clip(sinp, -1.0, 1.0) 
    pitch = np.arcsin(sinp)
    
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y**2 + z**2)
    yaw = np.arctan2(siny_cosp, cosy_cosp)
    
    return np.rad2deg(roll), np.rad2deg(pitch), np.rad2deg(yaw)


def rotate_vector_by_quaternion(v, q):
    # Extract vector components
    vx, vy, vz = v[:, 0], v[:, 1], v[:, 2]
    # Extract quaternion components
    qw, qx, qy, qz = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    
    # 3D Quaternion Rotation Math (v_new = q * v * q^-1)
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    
    rx = vx + qw * tx + (qy * tz - qz * ty)
    ry = vy + qw * ty + (qz * tx - qx * tz)
    rz = vz + qw * tz + (qx * ty - qy * tx)
    
    return np.column_stack((rx, ry, rz))


def apply_zaru_single_mean(gz, zaru_mask):
    """
    Collects all gated samples, takes one mean, and subtracts 
    that single fixed value across the entire log.
    """
    gz_cleaned = np.zeros_like(gz)
    fixed_bias_z = 0.0

    if np.sum(zaru_mask) > 0:
        fixed_bias_z = np.mean(gz[zaru_mask])
    else:
        fixed_bias_z = 0.0
        
    gz_cleaned = gz - fixed_bias_z
    return gz_cleaned, fixed_bias_z