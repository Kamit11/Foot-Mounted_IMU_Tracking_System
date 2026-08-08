#include "IMUHandler.h"
#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"
#include "helperFunctions.h"

const int8_t BMI270_ADDR = 0x68;

/**
 * @brief Initializes the IMU and configures its high-speed settings.
 * 
 * Attempts to start the IMU sensor. If successful, it overrides the I2C 
 * clock to 400kHz for faster data transfer and configures the 
 * accelerometer/gyroscope Output Data Rates (ODR) to 200Hz 
 * with an acceleration range of +/- 16g.
 * 
 * @return true if initialization and configuration are successful, 
 * @return false if IMU.begin() fails.
 */
bool initIMU() {
    if (!IMU.begin()) {
        Serial.println("IMU initialization failed!");
        return false;
    }

    // OVERRIDE THE DEFAULT I2C SPEED TO 400kHz
    Wire1.setClock(400000);

    // Accel ODR to 200 Hz, keeping the default OSR2
    writeRegister(0x40, 0x99);
    // Accel Range to +/- 16g
    writeRegister(0x41, 0x03);
    // Gyro ODR to 200 Hz
    writeRegister(0x42, 0xE9);

    return true;
}

IMUData getIMUData(){

    // Make variables static so they retain their value between loop iterations (ZOH)
    static float ax = 0, ay = 0, az = 0;
    static float gx = 0, gy = 0, gz = 0;
    bool valid_sample = false;

    Wire1.beginTransmission(BMI270_ADDR);
    Wire1.write(0x0C); // Place pointer on the beginning of the status register.
    Wire1.endTransmission(false); // Send data without releasing bus.
    
    // Guarantee a 12 byte read and a safe byte assembly using buffer[x].
    // Automatically sends a stop signal once we finish reading 12 bytes.
    if (Wire1.requestFrom(BMI270_ADDR,12) == 12){
        uint8_t buffer[12];

        for (int i = 0; i<12; i++){
            buffer[i] = Wire1.read();
        }

        // The status register 
        // [image-comments/image-20260807-123848-i1nejr.png]
        int16_t acc_x_raw = buffer[0] | (buffer[1] << 8); // 0x0C + 0x0D
        int16_t acc_y_raw = buffer[2] | (buffer[3] << 8); // 0x0E + 0x0F
        int16_t acc_z_raw = buffer[4] | (buffer[5] << 8); // 0x10 + 0x11
        int16_t gyr_x_raw = buffer[6] | (buffer[7] << 8); // 0x12 + 0x13
        int16_t gyr_y_raw = buffer[8] | (buffer[9] << 8); // 0x14 + 0x15
        int16_t gyr_z_raw = buffer[10] | (buffer[11] << 8); // 0x16 + 0x17

        // Apply scale factors
        // [image-comments/image-20260807-130005-4r8hfv.png]
        ax = -acc_y_raw/2048.0f;
        ay = -acc_x_raw/2048.0f;
        az = acc_z_raw/2048.0f;
    
        gx = -gyr_y_raw/16.384f;
        gy = -gyr_x_raw/16.384f;
        gz = gyr_z_raw/16.384f;

        valid_sample = true;
    }

    return IMUData{{ax, ay, az}, {gx, gy, gz}, valid_sample};

}