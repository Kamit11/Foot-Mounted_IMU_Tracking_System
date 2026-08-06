#include "MathTypes.h"

struct IMUData{
    float x;
    float y;
    float z;
    bool valid; // true if a fresh sample, false if zero order hold (ZOH) sample
};

bool initIMU();

IMUData getGyroData();
IMUData getAccelData();
IMUData getMagData();