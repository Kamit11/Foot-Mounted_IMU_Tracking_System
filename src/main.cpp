#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"
#include "IMUHandler.h"

uint32_t target_delta_t = 100000; //us -> 10Hz/0.1s
uint32_t nextTick = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for Serial to be ready
  nextTick = micros() + target_delta_t; // Schedule the first tick

  if (!initIMU()) {
    while (1); // Stop execution if IMU initialization fails
  }
}

void loop() {

// --- "Tick Timing - 200Hz" --- Currently set to 100,000 microseconds (100ms) for a 10Hz loop frequency. Adjust target_delta_t for different frequencies.
  uint32_t now = micros();

  // Cast to int32_t to avoid overflow issues when comparing unsigned long values
  if (int32_t(now - nextTick) < 0) return;
  nextTick += target_delta_t;

  // Declare prev as static to retain its value between loop iterations
  static uint32_t prev = 0;
  uint32_t dt = now - prev;
  prev = now;

  // This means that the current time has reached or passed the next scheduled tick time
  if (int32_t(now - nextTick) >= 0) {
    nextTick = now + target_delta_t; // Schedule the next tick
  }

  uint32_t w0 = micros();
  // ---The work will be here---
  // Vector3 gyroData = getGyroData();
  // Serial.print("Gyro: ");
  // Serial.print(gyroData.x);
  // Serial.print(", ");
  // Serial.print(gyroData.y);
  // Serial.print(", ");
  // Serial.println(gyroData.z);

  Vector3 accelData = getAccelData();
  Serial.print("Accel: ");
  Serial.print(accelData.x);
  Serial.print(", ");
  Serial.print(accelData.y);
  Serial.print(", ");
  Serial.println(accelData.z);

  //uint32_t work_time = micros() - w0;

}


