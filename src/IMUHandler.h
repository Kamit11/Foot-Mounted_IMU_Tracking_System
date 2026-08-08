#include "mathTypes.h"

#pragma once
struct IMUData{
    struct Vector3 acc;
    struct Vector3 gyro;
    bool valid;
};

bool initIMU();
IMUData getIMUData();