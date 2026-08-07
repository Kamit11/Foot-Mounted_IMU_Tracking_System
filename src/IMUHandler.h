#include "mathTypes.h"

struct IMUData{
    struct Vector3 acc;
    struct Vector3 gyro;
};

bool initIMU();
IMUData getIMUData();