#include <Arduino.h>
#include <Wire.h>
#include "helperFunctions.h"

const uint8_t BMI270_ADDR = 0x68;

void writeRegister(uint8_t reg, uint8_t value) {
    Wire1.beginTransmission(BMI270_ADDR);
    Wire1.write(reg);
    Wire1.write(value);
    Wire1.endTransmission();
}

uint8_t readRegister(uint8_t reg) {
    Wire1.beginTransmission(BMI270_ADDR);
    Wire1.write(reg);
    Wire1.endTransmission(false);
    Wire1.requestFrom(BMI270_ADDR, 1);
    return Wire1.read();
}