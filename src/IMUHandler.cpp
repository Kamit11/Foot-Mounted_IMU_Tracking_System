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

IMUData getIMUData(){
    Wire1.beginTransmission(0x68);
    Wire1.write(0x0C); // Place pointer on the beginning of the status register.
    Wire1.endTransmission(false); // Send data without releasing bus.
    
    // Request all 12 bytes in a single burst
    // Automatically sends a stop signal once we finish reading 12 bytes.
    Wire1.requestFrom(0x68, 12);

    // The status register 
    // [image-comments/image-20260807-123848-i1nejr.png]
    int16_t acc_x_raw = Wire1.read() | (Wire1.read() << 8); // 0x0C + 0x0D
    int16_t acc_y_raw = Wire1.read() | (Wire1.read() << 8); // 0x0E + 0x0F
    int16_t acc_z_raw = Wire1.read() | (Wire1.read() << 8); // 0x10 + 0x11
    int16_t gyr_x_raw = Wire1.read() | (Wire1.read() << 8); // 0x12 + 0x13
    int16_t gyr_y_raw = Wire1.read() | (Wire1.read() << 8); // 0x14 + 0x15
    int16_t gyr_z_raw = Wire1.read() | (Wire1.read() << 8); // 0x16 + 0x17

    // Apply scale factors
    // [image-comments/image-20260807-130005-4r8hfv.png]
    float ax = -acc_y_raw/2048.0f;
    float ay = -acc_x_raw/2048.0f;
    float az = acc_z_raw/2048.0f;
    
    float gx = -gyr_y_raw/16.384f;
    float gy = -gyr_x_raw/16.384f;
    float gz = gyr_z_raw/16.384f;


    IMUData data = {
        {ax, ay, az},
        {gx, gy, gz},
    };

    return data;  
}