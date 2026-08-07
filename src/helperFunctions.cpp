#include <Arduino.h>
#include <Wire.h>
#include "helperFunctions.h"

void writeRegister(uint8_t reg, uint8_t value) {
    Wire1.beginTransmission(0x68);
    Wire1.write(reg);
    Wire1.write(value);
    Wire1.endTransmission();
}

uint8_t readRegister(uint8_t reg) {
    Wire1.beginTransmission(0x68);
    Wire1.write(reg);
    Wire1.endTransmission(false);
    Wire1.requestFrom(0x68, 1);
    return Wire1.read();
}