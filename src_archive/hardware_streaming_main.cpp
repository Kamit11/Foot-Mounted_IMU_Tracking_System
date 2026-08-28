#include <Arduino.h>
#include <string.h>
#include "estimator.h"

// Hardware replay harness.
//
// PC -> Arduino: fixed 35-byte binary frame (always inside one 64-byte USB CDC packet)
//   [0]     0xAA        sync
//   [1]     0x55        sync
//   [2..5]  uint32 seq          (little endian)
//   [6..9]  uint32 t_us         (little endian)
//   [10..33] 6x float32 ax, ay, az, gx, gy, gz
//   [34]    uint8 checksum = XOR of bytes [2..33]
//
// Arduino -> PC: one ASCII line (this direction is not size limited in practice).
//
// Retries are safe: a frame whose seq matches the previous one is treated as a
// duplicate and the cached result is re-sent WITHOUT re-running the filters.
// Without this, a lost response line would cause the same sample to be
// integrated twice.

static constexpr uint8_t SYNC0 = 0xAA;
static constexpr uint8_t SYNC1 = 0x55;
static constexpr size_t  DATA_LEN    = 32;             // seq + t_us + 6 floats
static constexpr size_t  PAYLOAD_LEN = DATA_LEN + 1;   // + checksum

SystemState state{};
uint32_t t_last = 0;
bool first_row = true;

// Cached outputs so a duplicate frame can be answered without touching state.
static uint32_t last_seq = 0;
static bool     have_last = false;
static uint8_t  last_is_zvw = 0;
static uint8_t  last_instant_quiet = 0;

static void send_response(uint32_t seq, uint8_t is_zvw, uint8_t instant_quiet) {
    Serial.print(seq);                          Serial.print(",");
    Serial.print(is_zvw);                       Serial.print(",");
    Serial.print(instant_quiet);                Serial.print(",");
    Serial.print(state.mahony.q[0], 7);         Serial.print(",");
    Serial.print(state.mahony.q[1], 7);         Serial.print(",");
    Serial.print(state.mahony.q[2], 7);         Serial.print(",");
    Serial.print(state.mahony.q[3], 7);         Serial.print(",");
    Serial.print(state.kinematics.position[0], 6); Serial.print(",");
    Serial.print(state.kinematics.position[1], 6); Serial.print(",");
    Serial.print(state.kinematics.position[2], 6); Serial.println();
}

// Hunt for the sync pattern, then pull the fixed-length payload.
// Returns true only when a full, checksum-valid payload is in `out`.
static bool read_frame(uint8_t *out) {
    while (Serial.available() > 0) {
        if (Serial.read() != SYNC0) continue;

        int second = Serial.read();             // readBytes-free peek at the next byte
        if (second < 0) {
            uint32_t t0 = millis();
            while (Serial.available() == 0 && millis() - t0 < 50) { /* spin */ }
            second = Serial.read();
        }
        if (second != SYNC1) continue;          // false positive, keep hunting

        size_t n = Serial.readBytes(out, PAYLOAD_LEN);
        if (n != PAYLOAD_LEN) {
            Serial.println("NACK short");
            return false;
        }

        uint8_t cs = 0;
        for (size_t i = 0; i < DATA_LEN; i++) cs ^= out[i];
        if (cs != out[DATA_LEN]) {
            Serial.println("NACK checksum");
            return false;
        }
        return true;
    }
    return false;
}

void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }
    Serial.setTimeout(200);                     // guard for readBytes
    Serial.println("READY");
}

void loop() {
    uint8_t frame[PAYLOAD_LEN];
    if (!read_frame(frame)) return;

    uint32_t seq, t_current;
    float imu[6];
    memcpy(&seq,       frame + 0, 4);
    memcpy(&t_current, frame + 4, 4);
    memcpy(imu,        frame + 8, 24);

    const float ax = imu[0], ay = imu[1], az = imu[2];
    const float gx = imu[3], gy = imu[4], gz = imu[5];

    // Duplicate frame (PC retried because it lost our reply): re-send, do not re-integrate.
    if (have_last && seq == last_seq) {
        send_response(seq, last_is_zvw, last_instant_quiet);
        return;
    }

    float dt = 0.005f;
    if (first_row) {
        t_last = t_current;
        first_row = false;
    } else {
        dt = (uint32_t)(t_current - t_last) / 1000000.0f;   // unsigned math survives micros() rollover
        if (dt <= 0.0f) dt = 0.005f;
        t_last = t_current;
    }

    bool is_zvw = update_zvw(state.zvw, ax, ay, az, gx, gy, gz);
    update_mahony(state.mahony, ax, ay, az, gx, gy, gz, dt, state.zvw.instant_quiet);

    if (state.mahony.is_initialized) {
        update_kinematics(state.kinematics, state.mahony.q, ax, ay, az, dt, is_zvw, state.zvw.dwell_counter);
    }

    last_seq = seq;
    have_last = true;
    last_is_zvw = (uint8_t)is_zvw;
    last_instant_quiet = (uint8_t)state.zvw.instant_quiet;

    send_response(seq, last_is_zvw, last_instant_quiet);
}