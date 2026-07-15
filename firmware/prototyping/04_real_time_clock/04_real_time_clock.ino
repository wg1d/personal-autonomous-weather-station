/*
 * 04_real_time_clock
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept:
 * The DS3231 Real-Time Clock (RTC) is highly accurate and temperature-compensated.
 * We use it to trigger periodic wakeups (e.g. every 1 minute) while keeping the
 * ESP32 in deep sleep.
 * 
 * Wakeup Trigger (EXT0):
 * - The RTC's SQW/INT pin is connected to GPIO 36 (VP pin).
 * - The SQW pin is active-low (goes LOW when an alarm fires).
 * - Because GPIO 36 is an input-only pin without internal pull-up capability on the ESP32,
 *   a physical external 10k pull-up resistor must be connected between GPIO 36 and 3.3V.
 * - We enable EXT0 wakeup on GPIO 36 to wake the ESP32 on a LOW signal (0).
 * 
 * Hardware Layout:
 * - DS3231 SDA -> GPIO 21 (shared I2C)
 * - DS3231 SCL -> GPIO 22 (shared I2C)
 * - DS3231 SQW/INT -> GPIO 36 with external 10k pull-up resistor to 3.3V
 */

#include <Arduino.h>
#include <Wire.h>
#include <RTClib.h>

#define I2C_SDA 21
#define I2C_SCL 22
#define RTC_INTERRUPT_PIN 36 // GPIO 36 (VP pin)

RTC_DS3231 rtc;

void printWakeupReason() {
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT0) {
    Serial.println("Wakeup caused by external RTC Alarm (EXT0 on GPIO 36)");
  } else {
    Serial.printf("Wakeup not caused by RTC alarm deep sleep (%d)\n", wakeup_reason);
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(1000);

  Serial.println("==================================================");
  Serial.println("PAWS Step 04: Real-Time Clock & Alarms (DS3231)");
  Serial.println("==================================================");

  // Set interrupt pin as INPUT
  pinMode(RTC_INTERRUPT_PIN, INPUT);

  // Initialize I2C
  Wire.begin(I2C_SDA, I2C_SCL);

  // Initialize RTC
  if (!rtc.begin(&Wire)) {
    Serial.println("CRITICAL ERROR: DS3231 RTC not found! Check I2C wiring.");
    while (1) {
      delay(10);
    }
  }

  // Adjust time to compile time if power was lost
  if (rtc.lostPower()) {
    Serial.println("RTC lost power, adjusting time to compile time...");
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  printWakeupReason();

  DateTime now = rtc.now();
  char buf[] = "YYYY-MM-DD hh:mm:ss";
  Serial.printf("Current RTC time: %s\n", now.toString(buf));

  // Reset/clear alarms
  rtc.disableAlarm(1);
  rtc.disableAlarm(2);
  rtc.clearAlarm(1);
  rtc.clearAlarm(2);

  // Set SQW pin to alarm interrupt mode (turns off square wave generator)
  rtc.writeSqwPinMode(DS3231_OFF);

  // Set Alarm 1 to trigger when seconds reach 00 (once per minute)
  // This causes the SQW/INT pin to drive LOW.
  DateTime nextAlarm = DateTime(now.year(), now.month(), now.day(), now.hour(), now.minute() + 1, 0);
  
  if (rtc.setAlarm1(nextAlarm, DS3231_A1_Minute)) {
    Serial.printf("Alarm 1 successfully set for: %02d:%02d:00\n", nextAlarm.hour(), nextAlarm.minute());
  } else {
    Serial.println("Error setting alarm 1!");
  }

  // Configure ESP32 to wake up when RTC_INTERRUPT_PIN goes LOW (0)
  esp_sleep_enable_ext0_wakeup((gpio_num_t)RTC_INTERRUPT_PIN, 0);

  Serial.println("Entering Deep Sleep. Will wake up at the start of the next minute.");
  Serial.flush();

  esp_deep_sleep_start();
}

void loop() {
  // Never reached
}
