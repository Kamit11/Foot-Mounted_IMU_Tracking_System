#pragma once

#include <stdint.h>
#include <math.h>

// ======================================
// CONSTANT VARIABLES:
// ======================================
constexpr float ACC_DEVIATION = 0.3f;   // Allowable deviation from 1.0g
constexpr float GYRO_LIMIT = 75.0f;     // Maximum dps
constexpr float VAR_LIMIT = 0.06f;      // Maximum rolling variance
constexpr uint8_t VAR_WINDOW = 15;      // Variance window to calculate
constexpr uint8_t DWELL = 20;           // Minimum consecutive samples
// ======================================


// ======================================
// STRUCTS
// ======================================

struct ZVWState{
    float acc_ring_buffer[VAR_WINDOW] = {0.0f};
    uint16_t ring_index = 0;
    bool is_buffer_full = false;
    uint16_t dwell_counter = 0;
    bool is_zvw = false;
    bool instant_quiet = false;

};


struct FilterState{
    float q[4] = {1.0f, 0.0f, 0.0f, 0.0f};
    float eInt[3] = {0.0f, 0.0f, 0.0f};

    bool is_initialized = false;
    uint16_t init_sample_count = 0;
    float init_acc_accum[3] = {0.0f, 0.0f, 0.0f};

};


struct KinematicsState{
    float velocity[3] = {0.0f, 0.0f, 0.0f};
    float position[3] = {0.0f, 0.0f, 0.0f};

    float stance_onset_pos[3] = {0.0f, 0.0f, 0.0f};
};


struct SystemState{
    ZVWState zvw{};
    FilterState mahony{};
    KinematicsState kinematics{};
};



bool update_zvw(ZVWState& state, float ax, float ay, float az, float gx, float gy, float gz);

void update_mahony(FilterState& state, float ax, float ay, float az, float gx, float gy, float gz, float dt, bool instant_quiet, float Kp = 2.0f, float Ki = 0.5f);

void update_kinematics(KinematicsState& state, const float q[4], float ax, float ay, float az, float dt, bool is_zvw, uint8_t dwell_counter);