#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"
#include "IMUHandler.h"

uint32_t target_delta_t = 5000; //us
uint32_t nextTick = 0;
uint32_t seq = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for Serial to be ready
  nextTick = micros() + target_delta_t; // Schedule the first tick

  if (!initIMU()) {
    while (1); // Stop execution if IMU initialization fails
  }

  Serial.println(F("t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu_us,t_serial_us,missed"));
}

void loop() {

// --- "Tick Timing - 200Hz" ---
  uint32_t now = micros();

  // Cast to int32_t to avoid overflow issues when comparing unsigned long values
  if (int32_t(now - nextTick) < 0) return;
  nextTick += target_delta_t;

  // Declare prev as static to retain its value between loop iterations
  // initialize prev to (now - 5000) so the first dt is a perfect nominal interval.
  static uint32_t prev = now - target_delta_t;
  uint32_t dt = now - prev;
  prev = now;

  static uint32_t missed = 0;
  // This means that the current time has reached or passed the next scheduled tick time
  // Use a while loop to count all dropped deadlines
  while (int32_t(now - nextTick) >= 0) {
    nextTick += target_delta_t; 
    missed++;
  }
  

  uint32_t t0 = micros();
  // ---The work will be here---
  IMUData accelData = getAccelData();
  IMUData gyroData = getGyroData();
  uint32_t current_t_imu = micros() - t0;

  uint32_t sample_valid = (accelData.valid && gyroData.valid) ? 1 : 0;


  // Store the previous times:
  static uint32_t last_t_imu = 0;
  static uint32_t last_t_serial = 0;

  // ----Serial write----
  uint32_t t1 = micros();
  char buf[128];

  int len = snprintf(buf, sizeof(buf), "%lu,%lu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%lu,%lu,%lu,%lu\n",
      now, seq, 
      accelData.x, accelData.y, accelData.z, 
      gyroData.x, gyroData.y, gyroData.z, 
      sample_valid, last_t_imu, last_t_serial, missed);
  
  seq++;

  Serial.write(buf, len);

  uint32_t current_t_serial = micros() - t1;

  // Save current timings for the next loop
  last_t_imu = current_t_imu;
  last_t_serial = current_t_serial;
}


