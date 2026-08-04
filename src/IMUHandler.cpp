#include "IMUHandler.h"
#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"

bool initIMU() {
    if (!IMU.begin()) {
        Serial.println("IMU initialization failed!");
        return false; // Return false if IMU initialization fails
    }
    return true; // Return true if IMU initialization is successful
}

Vector3 getGyroData() {
    Vector3 gyroData = {0.0f, 0.0f, 0.0f};

    if (IMU.gyroscopeAvailable()) {
        IMU.readGyroscope(gyroData.x, gyroData.y, gyroData.z);
    }
    else {
        Serial.println("No gyroscope data available.");
    }
    return gyroData;
}

Vector3 getAccelData() {
    Vector3 accelData = {0.0f, 0.0f, 0.0f};
    if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(accelData.x, accelData.y, accelData.z);
    }
    else {
        Serial.println("No accelerometer data available.");
    }
    return accelData;
}

Vector3 getMagData() {
    Vector3 magData = {0.0f, 0.0f, 0.0f};
    if (IMU.magneticFieldAvailable()) {
        IMU.readMagneticField(magData.x, magData.y, magData.z);
    }
    else {
        Serial.println("No magnetometer data available.");
    }
    return magData;
}