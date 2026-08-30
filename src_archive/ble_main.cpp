#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"
#include <ArduinoBLE.h>
#include "IMUHandler.h"
#include "helperFunctions.h"
#include "estimator.h"

// packed 12 byte payload struct
struct __attribute__((packed)) StepPayload {
    uint16_t seq;
    int16_t x_mm;
    int16_t y_mm;
    uint16_t stance_dur;
    uint8_t quality;
    uint8_t state_flag;
    uint16_t missed;
};

uint32_t target_delta_t = 5000; //us
uint32_t nextTick = 0;
uint16_t seq = 0;

SystemState state{};
float last_pos_x = 0.0f;
float last_pos_y = 0.0f;

// Unique UUID
BLEService mapperService("28e1f1cd-733a-41d1-8d21-fb59e2c15db3");
// Defind step vector -> string, max 20 bytes.
BLECharacteristic stepChar("28e1f1cd-733a-41d1-8d21-fb59e2c15db2", BLERead | BLENotify, sizeof(StepPayload));

void initializeBLE(){
    // Set the advertised local name and service UUID
    BLE.setLocalName("Nano33_Mapper");
    BLE.setAdvertisedService(mapperService);
    
    // Add the characteristic to the service, and the service to the peripheral
    mapperService.addCharacteristic(stepChar);
    BLE.addService(mapperService);

    // Start advertising
    BLE.advertise();
}

void setup() {
    Serial.begin(115200);
    // No need when going wireless
    // while (!Serial);

    Serial.println("Arduino Ready. Press ENTER in the Serial Monitor to start...");

    // No need when going wireless
    // Block execution until at least one byte is received over Serial
    // while (Serial.available() == 0) {
    //     // Wait infinitely for the start signal
    // }

    Serial.read(); // Consume the start signal ('S')

    Serial.println("Initializing IMU...");

    if (!initIMU()) {
        Serial.println("IMU FAILED TO INITIALIZE! Check wiring/power.");
        while (1); // Stop execution if IMU initialization fails
    }

    if (!BLE.begin()){
        Serial.println("BLE FAILED TO INITIALIZE! :[");
        while(1);
    }

    initializeBLE();

    while (!BLE.central()) {
        delay(100); 
    }

    Serial.println("IMU Initialized. Walk in 3 seconds...");
    delay(3000); // Reposition

    Serial.println("===========\nCapturing Started.\n===========");

    nextTick = micros() + target_delta_t; // Schedule the first tick
}

void loop() {
    // 200Hz
    uint32_t now = micros();

    // Cast to int32_t to avoid overflow issues when comparing unsigned long values
    if (int32_t(now - nextTick) < 0) return;
    nextTick += target_delta_t;

    BLE.poll();

    static uint32_t prev = now - target_delta_t;
    uint32_t dt = now - prev;
    prev = now;

    static uint32_t missed = 0;
    while (int32_t(now - nextTick) >= 0) {
        nextTick += target_delta_t; 
        missed++;
    }

    // --- Work ---
    IMUData _IMUData = getIMUData();
    Vector3 accData = _IMUData.acc;
    Vector3 gyroData = _IMUData.gyro;

    float dt_sec = dt / 1000000.0f;
    // Clamp dt to 5ms if it exceeds 1.5x nominal (7.5ms) to prevent mid-swing explosion
    if (dt_sec > 0.0075f) {
        dt_sec = 0.005f; 
    }

    bool is_zvw = update_zvw(state.zvw, accData.x, accData.y, accData.z, gyroData.x, gyroData.y, gyroData.z);
    update_mahony(state.mahony, accData.x, accData.y, accData.z, gyroData.x, gyroData.y, gyroData.z, dt_sec, state.zvw.instant_quiet);

    if (state.mahony.is_initialized) {
        update_kinematics(state.kinematics, state.mahony.q, accData.x, accData.y, accData.z, dt_sec, is_zvw, state.zvw.dwell_counter);
        
        if (state.zvw.dwell_counter == DWELL){
            // Pack the binary struct
            StepPayload payload;
            payload.seq = seq;
            // Convert float meters to int16 millimeters
            payload.x_mm = (int16_t)(state.kinematics.position[0] * 1000.0f);
            payload.y_mm = (int16_t)(state.kinematics.position[1] * 1000.0f);
            payload.stance_dur = 0; // Placeholder for Phase 5
            payload.quality = 0;    // Placeholder for Phase 5
            payload.state_flag = 0; // Placeholder for Phase 5
            payload.missed = (uint16_t)missed;

            // Transmit over BLE as a raw byte array
            stepChar.writeValue((uint8_t*)&payload, sizeof(payload));

            // If plugged into USB, print for debugging
            if (Serial) { 
                char debug[64];
                snprintf(debug, sizeof(debug), "%u,%d,%d,%u", payload.seq, payload.x_mm, payload.y_mm, missed);
                Serial.println(debug); 
            }
            
            last_pos_x = state.kinematics.position[0]; 
            last_pos_y = state.kinematics.position[1];
            seq++;
        }
    }
}