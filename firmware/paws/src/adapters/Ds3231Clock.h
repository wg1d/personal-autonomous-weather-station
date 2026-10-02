/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Ds3231Clock.h
 *
 * Description:
 * Clock adapter for the DS3231 real-time clock: the time comes from the
 * DS3231, and its alarm 1 wakes the ESP32 up through the SQW pin.
 *
 * Wiring:
 * - DS3231: 3.3V -> VCC, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL,
 *           Pin 36 -> SQW (10k pull-up resistor to 3.3V)
 * Dependencies: ESP32 Arduino core, RTClib.
 */

#pragma once

#include <Arduino.h>
#include <RTClib.h>

#include "IClock.h"

/// Time of the last setTime(), kept in RTC memory across deep sleep
RTC_DATA_ATTR static uint32_t ds3231LastSet = 0;

/**
 * @brief Clock adapter for the DS3231 real-time clock.
 *
 * Call begin() once at boot, before the state machine runs. If the
 * DS3231 does not answer, the clock reports an invalid time and refuses
 * the alarms, so the safety timer wakes the station up (N2).
 */
class Ds3231Clock : public IClock {
public:
    /**
     * @brief Connects to the DS3231 and prepares its alarm.
     *
     * @return true if the DS3231 answered on the I2C bus.
     */
    bool begin() {
        responding_ = rtc_.begin();
        if (!responding_) {
            Serial.println("   DS3231 not responding");
            return false;
        }
        // The 32 kHz output is not used: turn it off to save power
        rtc_.disable32K();
        // SQW is used as the alarm output, not as a square wave
        rtc_.writeSqwPinMode(DS3231_OFF);
        // Only alarm 1 is used, reprogrammed at every wake-up. Alarm 2 is
        // disabled: its registers keep the settings left by a previous
        // firmware, which could otherwise fire at any time
        rtc_.disableAlarm(2);
        // An alarm that fired keeps SQW low until its flag is cleared,
        // whichever alarm it was: clear both flags, or the station would
        // wake up again at once
        rtc_.clearAlarm(1);
        rtc_.clearAlarm(2);
        return true;
    }

    uint32_t now() override {
        return responding_ ? rtc_.now().unixtime() : 0;
    }

    bool isValid() override {
        // lostPower() reads the Oscillator Stop Flag, set by a power loss
        return responding_ && !rtc_.lostPower();
    }

    void setTime(uint32_t unixTime) override {
        if (!responding_) {
            return;
        }
        // adjust() also clears the Oscillator Stop Flag
        rtc_.adjust(DateTime(unixTime));
        ds3231LastSet = unixTime;
    }

    uint32_t lastSetTime() override { return ds3231LastSet; }

    bool setAlarm(uint32_t unixTime) override {
        if (!responding_) {
            return false;
        }
        rtc_.clearAlarm(1);
        // DS3231_A1_Hour means "match hours, minutes and seconds": the
        // alarm fires once, at that time, for any interval below one day
        DateTime alarm(unixTime);
        if (!rtc_.setAlarm1(alarm, DS3231_A1_Hour)) {
            return false;
        }
        Serial.printf("   alarm set for %02d:%02d:%02d\n", alarm.hour(),
                      alarm.minute(), alarm.second());
        return true;
    }

private:
    RTC_DS3231 rtc_;
    bool responding_ = false;
};
