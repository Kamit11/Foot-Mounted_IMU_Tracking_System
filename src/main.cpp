#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"
#include "IMUHandler.h"
#include "helperFunctions.h"

uint32_t target_delta_t = 5000; //us
uint32_t nextTick = 0;
uint32_t seq = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for Serial to be ready

  // --- WAIT FOR PYTHON SCRIPT ---
  // Block execution until at least one byte is received over Serial
  while (Serial.available() == 0) {
    // Wait infinitely for the start signal
  }

  Serial.read(); // Consume the start signal ('S')

  if (!initIMU()) {
    while (1); // Stop execution if IMU initialization fails
  }

  initialize();
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

  // ---IMU DATA---
  IMUData accelData = getAccelData();
  IMUData gyroData = getGyroData();

  // ---The work will be here---
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

void initialize(){
  // OVERRIDE THE DEFAULT I2C SPEED
  Wire1.setClock(400000);

  // Accel ODR to 200 Hz
  writeRegister(0x40, 0xA9);
  // Accel Range to +/- 16g
  writeRegister(0x41, 0x03);
  // Gyro ODR to 200 Hz
  writeRegister(0x42, 0xE9);
  

  // Initialize timing variables immediately before loop() starts 
  // to prevent a massive spike in the 'missed' deadline counter.
  nextTick = micros() + target_delta_t; // Schedule the first tick

  // Send the CSV header
  Serial.println(F("t_us,seq,ax,ay,az,gx,gy,gz,valid,t_imu,t_serial,missed"));}