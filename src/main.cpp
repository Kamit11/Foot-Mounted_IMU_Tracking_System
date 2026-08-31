#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"
#include "IMUHandler.h"
#include "helperFunctions.h"

uint32_t target_delta_t = 5000; 
uint32_t nextTick = 0;
uint32_t seq = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial); 

    while (Serial.available() == 0) {}
    Serial.read(); // Consume the start signal ('S')

    if (!initIMU()) {
        while (1); 
    }

    delay(50); 
    nextTick = micros() + target_delta_t; 
}

void loop() {
    uint32_t now = micros();

    if (int32_t(now - nextTick) < 0) return;
    nextTick += target_delta_t;

    static uint32_t prev = now - target_delta_t;
    uint32_t dt = now - prev;
    prev = now;

    static uint32_t missed = 0;
    while (int32_t(now - nextTick) >= 0) {
        nextTick += target_delta_t; 
        missed++;
    }

    uint32_t t0 = micros();
    IMUData _IMUData = getIMUData();
    uint32_t current_t_imu = micros() - t0;
    Vector3 accData = _IMUData.acc;
    Vector3 gyroData = _IMUData.gyro;

    static uint32_t last_t_imu = 0;
    static uint32_t last_t_serial = 0;

    uint32_t t1 = micros();
    char buf[128];

    // Removed the trailing ,%d and the old state_flag comment
    int len = snprintf(buf, sizeof(buf), "%lu,%lu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%d,%lu,%lu,%lu\n",
        now, seq, 
        accData.x, accData.y, accData.z, 
        gyroData.x, gyroData.y, gyroData.z,
        _IMUData.valid, last_t_imu, last_t_serial, missed);

    seq++;
    Serial.write(buf, len);

    last_t_imu = current_t_imu;
    last_t_serial = micros() - t1;
}