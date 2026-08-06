#include "IMUHandler.h"
#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"

bool initIMU() {
    if (!IMU.begin()) {
        Serial.println("IMU initialization failed!");
        return false;
    }
    return true;
}

IMUData getGyroData() {
    // Declare as static to retain the last known value between calls
    static IMUData gyroData = {0.0f, 0.0f, 0.0f, false};

    if (IMU.gyroscopeAvailable()) {
        IMU.readGyroscope(gyroData.x, gyroData.y, gyroData.z);
        gyroData.valid = true; // Mark as fresh data
    }
    else {
        gyroData.valid = false; // Mark as held data
        // Serial.println("No gyroscope data available. Using previous sample.");
    }
    return gyroData;
}

IMUData getAccelData() {
    // Declare as static to retain the last known value between calls
    // Defaulting Z to 1g (or 9.8 depending on your unit scale) is safer than 0
    static IMUData accelData = {0.0f, 0.0f, 1.0f, false}; 
    
    if (IMU.accelerationAvailable()) {
        IMU.readAcceleration(accelData.x, accelData.y, accelData.z);
        accelData.valid = true; // Mark as fresh data
    }
    else {
        accelData.valid = false; // Mark as held data
        // Serial.println("No accelerometer data available. Using previous sample.");
    }
    return accelData;
}

IMUData getMagData() {
    // Declare as static to retain the last known value between calls
    static IMUData magData = {0.0f, 0.0f, 0.0f, false};
    
    if (IMU.magneticFieldAvailable()) {
        IMU.readMagneticField(magData.x, magData.y, magData.z);
        magData.valid = true; // Mark as fresh data
    }
    else {
        magData.valid = false; // Mark as held data
        // Serial.println("No magnetometer data available. Using previous sample.");
    }
    return magData;
}