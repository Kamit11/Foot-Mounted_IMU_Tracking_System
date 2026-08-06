#include <Arduino.h>

#pragma once

void writeRegister(uint8_t reg, uint8_t value);
uint8_t readRegister(uint8_t reg);