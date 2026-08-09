#include <Arduino.h>

#pragma once

constexpr int8_t BMI270_ADDR = 0x68;
void writeRegister(uint8_t reg, uint8_t value);
uint8_t readRegister(uint8_t reg);