#include <Arduino.h>
#include "Arduino_BMI270_BMM150.h"
#include <ArduinoBLE.h>
#include "IMUHandler.h"
#include "helperFunctions.h"
#include "estimator.h"

struct __attribute__((packed)) StepPayload {
    uint16_t seq;
    int16_t x_mm;
    int16_t y_mm;
    uint16_t stance_dur;
    uint8_t quality;
    uint8_t state_flag;
    uint16_t missed;
};

uint32_t target_delta_t = 5000;
uint32_t nextTick = 0;
uint16_t step_seq = 0;

SystemState state{};
float last_pos_x = 0.0f;
float last_pos_y = 0.0f;

BLEService mapperService("28e1f1cd-733a-41d1-8d21-fb59e2c15db3");
BLECharacteristic stepChar("28e1f1cd-733a-41d1-8d21-fb59e2c15db2", BLERead | BLENotify, sizeof(StepPayload));

void initializeBLE(){
    BLE.setLocalName("Nano33_Mapper"); // Name restored for the normal Python receiver
    BLE.setAdvertisedService(mapperService);
    mapperService.addCharacteristic(stepChar);
    BLE.addService(mapperService);
    BLE.advertise();
}

void setup() {
    // No Serial.begin() needed for the untethered demo!
    
    if (!initIMU()) { while (1); }
    if (!BLE.begin()) { while(1); }
    initializeBLE();

    // Wait for ble_receiver.py to connect so the radio is under full load
    while (!BLE.central()) {
        delay(100); 
    }

    delay(3000); 
    nextTick = micros() + target_delta_t; 
}

void loop() {
    uint32_t now = micros();
    
    // Explicitly yield while waiting for the 5000us tick. 
    // This feeds the BLE radio all of the processor's idle time!
    if (int32_t(now - nextTick) < 0) {
        yield(); 
        return;
    }
    
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

    IMUData _IMUData = getIMUData();
    Vector3 accData = _IMUData.acc;
    Vector3 gyroData = _IMUData.gyro;

    // The explicit yield replacing the Serial.write mask
    yield();

    float dt_sec = dt / 1000000.0f;
    if (dt_sec > 0.0075f) { dt_sec = 0.005f; }

    bool is_zvw = update_zvw(state.zvw, accData.x, accData.y, accData.z, gyroData.x, gyroData.y, gyroData.z);
    update_mahony(state.mahony, accData.x, accData.y, accData.z, gyroData.x, gyroData.y, gyroData.z, dt_sec, state.zvw.instant_quiet);

    if (state.mahony.is_initialized) {
        update_kinematics(state.kinematics, state.mahony.q, accData.x, accData.y, accData.z, dt_sec, is_zvw, state.zvw.dwell_counter);
        
        if (state.zvw.dwell_counter == DWELL){
            StepPayload payload;
            payload.seq = step_seq;
            payload.x_mm = (int16_t)(state.kinematics.position[0] * 1000.0f);
            payload.y_mm = (int16_t)(state.kinematics.position[1] * 1000.0f);
            payload.stance_dur = 0; 
            payload.quality = 0;    
            payload.state_flag = 0; 
            payload.missed = (uint16_t)missed;

            stepChar.writeValue((uint8_t*)&payload, sizeof(payload));
            step_seq++;
        }
    }
}