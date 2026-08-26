#include "estimator.h"

constexpr float DEG_TO_RAD = 0.01745329251f;
constexpr float G_MPS2 = 9.80665f;

bool update_zvw(ZVWState& state, float ax, float ay, float az, float gx, float gy, float gz){
    float acc_mag = sqrtf(ax*ax + ay*ay + az*az);
    float gyro_mag = sqrtf(gx*gx + gy*gy + gz*gz);

    state.acc_ring_buffer[state.ring_index] = acc_mag;
    state.ring_index++;
    if (state.ring_index >= VAR_WINDOW){
        state.ring_index = 0;
        state.is_buffer_full = true;
    }

    bool var_cond = false;
    if (state.is_buffer_full){
        // calculate Mean
        float sum = 0.0f;
        for (int i = 0; i < VAR_WINDOW; i++) {
            sum += state.acc_ring_buffer[i];
        }
        float mean_acc = sum / VAR_WINDOW;

        // Calculate Variance (N-1 Bessel's Correction)
        float sq_diff_sum = 0.0f;
        for (int i = 0; i < VAR_WINDOW; i++) {
            float diff = state.acc_ring_buffer[i] - mean_acc;
            sq_diff_sum += (diff * diff);
        }
        float acc_var = sq_diff_sum / (VAR_WINDOW - 1);

        var_cond = (acc_var <= VAR_LIMIT);
    }

    bool acc_cond = fabsf(acc_mag - 1.0f) <= ACC_DEVIATION;
    bool gyro_cond = gyro_mag <= GYRO_LIMIT;

    state.instant_quiet = acc_cond && gyro_cond && var_cond;

    if (state.instant_quiet) state.dwell_counter++;
    else state.dwell_counter = 0;

    state.is_zvw = state.dwell_counter >= DWELL;
    return state.is_zvw;
}


void update_mahony(FilterState& state, float ax, float ay, float az, float gx, float gy, float gz, float dt, bool instant_quiet, float Kp, float Ki){
    if (state.is_initialized == false){
        state.init_sample_count++;
        state.init_acc_accum[0] += ax;
        state.init_acc_accum[1] += ay;
        state.init_acc_accum[2] += az;

        if (state.init_sample_count >= 100){
            float mean_ax = state.init_acc_accum[0] / 100.0f;
            float mean_ay = state.init_acc_accum[1] / 100.0f;
            float mean_az = state.init_acc_accum[2] / 100.0f;
            
            float norm = sqrtf(mean_ax*mean_ax + mean_ay*mean_ay +mean_az*mean_az);
            float init_roll = atan2f(mean_ay / norm, mean_az / norm);

            float denom = sqrtf((mean_ay/norm)*(mean_ay/norm) + (mean_az/norm)*(mean_az/norm));
            float init_pitch = atan2f(-mean_ax / norm, denom);

            float cy = cosf(0.0f);
            float sy = sinf(0.0f);
            float cp = cosf(init_pitch * 0.5f);
            float sp = sinf(init_pitch * 0.5f);
            float cr = cosf(init_roll * 0.5f);
            float sr = sinf(init_roll * 0.5f);

            state.q[0] = cr * cp * cy + sr * sp * sy;
            state.q[1] = sr * cp * cy - cr * sp * sy;
            state.q[2] = cr * sp * cy + sr * cp * sy;
            state.q[3] = cr * cp * sy - sr * sp * cy;

            state.is_initialized = true;
        }
        return;
    }

    // mahony filter
    float qw = state.q[0], qx = state.q[1], qy = state.q[2], qz = state.q[3];
    float wx = (gx * DEG_TO_RAD) + (Ki * state.eInt[0]);
    float wy = (gy * DEG_TO_RAD) + (Ki * state.eInt[1]);
    float wz = (gz * DEG_TO_RAD) + (Ki * state.eInt[2]);

    float acc_norm = sqrtf(ax*ax + ay*ay + az*az);
    if (acc_norm > 0.0f && instant_quiet){
        float a_x = ax / acc_norm;
        float a_y = ay / acc_norm;
        float a_z = az / acc_norm;

        float v_x = 2.0f * (qx * qz - qw * qy);
        float v_y = 2.0f * (qw * qx + qy * qz);
        float v_z = 1.0f - 2.0f * (qx*qx + qy*qy);

        float e_x = (a_y * v_z) - (a_z * v_y);
        float e_y = (a_z * v_x) - (a_x * v_z);
        float e_z = (a_x * v_y) - (a_y * v_x);

        if (Ki > 0.0f) {
            state.eInt[0] += e_x * dt;
            state.eInt[1] += e_y * dt;
            state.eInt[2] += e_z * dt;

            float max_eInt_val = (2.0f * DEG_TO_RAD) / Ki;
            
            // Manual clamping for cross-platform safety
            for (int i = 0; i < 3; i++) {
                if (state.eInt[i] > max_eInt_val) state.eInt[i] = max_eInt_val;
                if (state.eInt[i] < -max_eInt_val) state.eInt[i] = -max_eInt_val;
            }
        }

        wx += (Kp * e_x);
        wy += (Kp * e_y);
        wz += (Kp * e_z);
    }

    // quaternion integration
    float q_dot_w = 0.5f * (-qx*wx - qy*wy - qz*wz);
    float q_dot_x = 0.5f * ( qw*wx + qy*wz - qz*wy);
    float q_dot_y = 0.5f * ( qw*wy - qx*wz + qz*wx);
    float q_dot_z = 0.5f * ( qw*wz + qx*wy - qy*wx);

    state.q[0] += q_dot_w * dt;
    state.q[1] += q_dot_x * dt;
    state.q[2] += q_dot_y * dt;
    state.q[3] += q_dot_z * dt;

    float q_norm = sqrtf(state.q[0]*state.q[0] + state.q[1]*state.q[1] + state.q[2]*state.q[2] + state.q[3]*state.q[3]);
    
    state.q[0] /= q_norm;
    state.q[1] /= q_norm;
    state.q[2] /= q_norm;
    state.q[3] /= q_norm;
}


void update_kinematics(KinematicsState& state, const float q[4], float ax, float ay, float az, float dt, bool is_zvw, uint8_t dwell_counter) {
    // snapshot
    if (dwell_counter == 1) {
        state.stance_onset_pos[0] = state.position[0];
        state.stance_onset_pos[1] = state.position[1];
        state.stance_onset_pos[2] = state.position[2];
    }

    // rollback
    if (dwell_counter == DWELL) {
        state.position[0] = state.stance_onset_pos[0];
        state.position[1] = state.stance_onset_pos[1];
        state.position[2] = state.stance_onset_pos[2];
        
        state.velocity[0] = 0.0f;
        state.velocity[1] = 0.0f;
        state.velocity[2] = 0.0f;
    }

    if (is_zvw) {
        state.velocity[0] = 0.0f;
        state.velocity[1] = 0.0f;
        state.velocity[2] = 0.0f;
        return;
    }

    float qw = q[0], qx = q[1], qy = q[2], qz = q[3];

    // 3D Quaternion Rotation Math (v_new = q * v * q^-1)
    float tx = 2.0f * (qy * az - qz * ay);
    float ty = 2.0f * (qz * ax - qx * az);
    float tz = 2.0f * (qx * ay - qy * ax);

    // this is the rotated vector
    float rx = ax + qw * tx + (qy * tz - qz * ty);
    float ry = ay + qw * ty + (qz * tx - qx * tz);
    float rz = az + qw * tz + (qx * ty - qy * tx);

    rz -= 1.0f;

    // convert to ms2
    float ax_ms2 = rx * G_MPS2;
    float ay_ms2 = ry * G_MPS2;
    float az_ms2 = rz * G_MPS2;

    // integrate ms2 accel to velocity
    state.velocity[0] += ax_ms2 * dt;
    state.velocity[1] += ay_ms2 * dt;
    state.velocity[2] += az_ms2 * dt;

    // update velocity
    state.position[0] += state.velocity[0] * dt;
    state.position[1] += state.velocity[1] * dt;
    state.position[2] += state.velocity[2] * dt;
}