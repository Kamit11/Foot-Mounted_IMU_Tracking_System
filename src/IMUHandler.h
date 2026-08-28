#include "mathTypes.h"

#pragma once

struct IMUData{
    Vector3 acc;
    Vector3 gyro;
    bool valid;
};

bool initIMU();
IMUData getIMUData();