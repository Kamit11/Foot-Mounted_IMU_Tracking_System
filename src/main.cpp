#include <Arduino.h>

uint32_t target_delta_t = 5000; //us
uint32_t nextTick = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial); // Wait for Serial to be ready
  Serial.println(F("seq,work_time_us,mismatches"));
  nextTick = micros() + target_delta_t; // Schedule the first tick
}

void loop() {
  uint32_t now = micros();

  // Cast to int32_t to avoid overflow issues when comparing unsigned long values
  if (int32_t(now - nextTick) < 0) return;
  nextTick += target_delta_t;

  // Declare prev as static to retain its value between loop iterations
  static uint32_t prev = 0;
  // uint32_t dt = now - prev;
  prev = now;

  // This means that the current time has reached or passed the next scheduled tick time
  if (int32_t(now - nextTick) >= 0) {
    nextTick = now + target_delta_t; // Schedule the next tick
  }

  uint32_t w0 = micros();
  // ---The work will be here---

  // Simulate some work that takes time, e.g., a floating-point calculation
  volatile float val = 1.2345f;
  for (int i = 0; i < 500; i++) {
    val = (val * 1.012f) + 0.056f;
  }

  // Save the expected answer on the very first loop
  static float expected_val = 0.0f;
  static bool first_loop = true;
  if (first_loop) {
    expected_val = val;
    first_loop = false;
  }

  static uint32_t mismatches = 0;
  if (abs(val - expected_val) > 0.0001f) {
    mismatches++;
  }


  uint32_t work_time = micros() - w0;

  static uint32_t seq = 0;
  // 50s of data, then stop printing to avoid flooding the serial output
  if (seq < 125000){
    Serial.print(seq);       Serial.print(',');
    Serial.print(work_time); Serial.print(',');
    Serial.println(mismatches);
  }
  seq++;
}