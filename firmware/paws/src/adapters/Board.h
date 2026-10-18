/*
 * Project: Personal Autonomous Weather Station
 * File: src/adapters/Board.h
 *
 * Description:
 * The pins of each board the firmware runs on, in a single place. The
 * environment of platformio.ini chooses the board: -D PAWS_BOARD_XIAO=1
 * for the XIAO ESP32-S3 of the outdoor station, nothing for the uPesy
 * ESP32 Wrover DevKit of the bench station. The rest of the firmware only
 * uses the names below.
 *
 * The I2C bus uses the default pins of each board, chosen by the Arduino
 * core: SDA = D4 and SCL = D5 on the XIAO, 21 and 22 on the uPesy.
 *
 * Dependencies: ESP32 Arduino core (gpio_num_t, esp_sleep.h).
 */

#pragma once

#include <Arduino.h>
#include <esp_sleep.h>

#if PAWS_BOARD_XIAO

/// Name printed at boot
const char kBoardName[] = "XIAO ESP32-S3";

/// DS3231 SQW output, on D0: pulled low when the alarm fires. The clock
/// module has its own pull-up resistor on this line.
const gpio_num_t kRtcAlarmPin = GPIO_NUM_1;

/// Maintenance button, on D1: it connects D1 to the ground while it is
/// pressed
const gpio_num_t kButtonPin = GPIO_NUM_2;

/// true when the button pulls its pin low; the internal pull-up resistor
/// of the chip then keeps the pin high the rest of the time, also during
/// deep sleep
const bool kButtonActiveLow = true;

/// The button wakes the station up when its pin goes low. The ESP32-S3
/// names this mode ANY_LOW: any of the watched pins low
const esp_sleep_ext1_wakeup_mode_t kButtonWakeMode = ESP_EXT1_WAKEUP_ANY_LOW;

/// true: the serial port is the USB port built into the ESP32-S3, not a
/// separate USB to serial chip. Its Serial.flush() waits until a computer
/// has read everything, forever if none reads it (Arduino core 2.0.x): it
/// must not be called before the deep sleep.
const bool kSerialIsNativeUsb = true;

#else

/// Name printed at boot
const char kBoardName[] = "uPesy ESP32 Wrover DevKit";

/// DS3231 SQW output, on pin 36: pulled low when the alarm fires, with a
/// 10k pull-up resistor to 3.3V on the breadboard
const gpio_num_t kRtcAlarmPin = GPIO_NUM_36;

/// Maintenance button, on pin 39: it connects the pin to 3.3V while it is
/// pressed, with a 10k pull-down resistor to GND on the breadboard (pins
/// 36 and 39 have no internal pull resistor)
const gpio_num_t kButtonPin = GPIO_NUM_39;

/// false: the button pulls its pin high
const bool kButtonActiveLow = false;

/// The button wakes the station up when its pin goes high
const esp_sleep_ext1_wakeup_mode_t kButtonWakeMode = ESP_EXT1_WAKEUP_ANY_HIGH;

/// false: the serial port goes through the USB to serial chip of the
/// board, a UART that Serial.flush() empties in a few milliseconds
const bool kSerialIsNativeUsb = false;

#endif
