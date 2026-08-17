import numpy as np

def integrate_kinematics(accel_ms2, dt_array, zvw_mask):

    vel_zupt = np.zeros_like(accel_ms2)
    pos_zupt = np.zeros_like(accel_ms2)

    # We will store the velocity from the exact moment BEFORE ZUPT resets it
    pre_zupt_velocities = []

    for i in range(1, len(dt_array)):
        if zvw_mask[i]:
            # store last velocity before entering the zvw
            if not zvw_mask[i-1]:
                pre_zupt_velocities.append(vel_zupt[i-1].copy())

            # force vel to 0 in a zvw
            vel_zupt[i] = np.array([0.0,0.0,0.0])

        else:
            # integrate acc to get velocity
            vel_zupt[i] = vel_zupt[i-1] + (accel_ms2[i] * dt_array[i])

        # integrate vel to get pos
        pos_zupt[i] = pos_zupt[i-1] + (vel_zupt[i] * dt_array[i])


    pre_zupt_velocities = np.array(pre_zupt_velocities)
    return vel_zupt, pos_zupt, pre_zupt_velocities
