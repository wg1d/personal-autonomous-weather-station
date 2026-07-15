/*
 * 06_full_datalogger
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept:
 * This sketch integrates the BME280 sensor, DS3231 RTC, and SD card logging
 * with Deep Sleep power management. It functions as a complete offline datalogger.
 * 
 * Operations Flow on Wakeup:
 * 1. Read wakeup cause.
 * 2. Power on SD card, initialize SPI.
 * 3. Initialize I2C, read temperature, humidity, pressure from BME280.
 * 4. Read timestamp from RTC.
 * 5. Log timestamped sensors readings to CSV.
 * 6. Power down SD card.
 * 7. Schedule next RTC alarm (e.g. 1 minute later).
 * 8. Enable EXT0 wakeup (RTC Alarm) and EXT1 wakeup (Button).
 * 9. Re-enter deep sleep.
 * 
 * Hardware Layout:
 * - Built-in LED on GPIO 2
 * - Push Button on GPIO 39 (EXT1 wakeup, active-low)
 * - DS3231 SQW/INT on GPIO 36 (EXT0 wakeup, active-low)
 * - Shared I2C (SDA = GPIO 21, SCL = GPIO 22) for BME280 & RTC
 * - SD Card (CS = GPIO 5, SCK = GPIO 18, MISO = GPIO 19, MOSI = GPIO 23, VCC Gated = GPIO 13)
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <RTClib.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

// Pin Definitions
#define LED_PIN 2
#define BUTTON_PIN 39
#define RTC_INTERRUPT_PIN 36
#define SD_POWER_PIN 13
#define SD_CS_PIN 5

#define I2C_SDA 21
#define I2C_SCL 22

// Measurement Interval
#define LOG_INTERVAL_MINUTES 1

// Libraries
Adafruit_BME280 bme;
RTC_DS3231 rtc;

// Global log configuration
const char* filename = "/data.csv";
const char* csvHeader = "timestamp,temp_c,hum_pct,pres_hpa,light_lux,uv_idx,soil_pct,rain_mm,wind_spd_ms,wind_dir_deg,bat_v";

RTC_DATA_ATTR int bootCount = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(1000);

  bootCount++;

  Serial.println("==================================================");
  Serial.println("PAWS Step 06: Integrated Datalogger");
  Serial.println("==================================================");
  Serial.printf("Boot number: %d\n", bootCount);

  // Read wakeup cause
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  bool triggeredByRTC = (wakeup_reason == ESP_SLEEP_WAKEUP_EXT0);
  bool triggeredByButton = (wakeup_reason == ESP_SLEEP_WAKEUP_EXT1);

  if (triggeredByRTC) {
    Serial.println("Wakeup Source: RTC Alarm");
  } else if (triggeredByButton) {
    Serial.println("Wakeup Source: Manual Button Press");
  } else {
    Serial.println("Wakeup Source: Fresh Power-on / Reset");
  }

  // Initialize I2C and RTC
  Wire.begin(I2C_SDA, I2C_SCL);
  if (!rtc.begin(&Wire)) {
    Serial.println("Error: RTC not found!");
  }
  if (rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  // Clear RTC Alarms
  rtc.disableAlarm(1);
  rtc.disableAlarm(2);
  rtc.clearAlarm(1);
  rtc.clearAlarm(2);
  rtc.writeSqwPinMode(DS3231_OFF);

  // Initialize BME280
  bool bmeStatus = bme.begin(0x76, &Wire) || bme.begin(0x77, &Wire);
  float temp = NAN, hum = NAN, pres = NAN;
  if (bmeStatus) {
    temp = bme.readTemperature();
    hum  = bme.readHumidity();
    pres = bme.readPressure() / 100.0F;
    Serial.printf("Sensor Read -> Temp: %.2f °C | Hum: %.2f %% | Pres: %.2f hPa\n", temp, hum, pres);
  } else {
    Serial.println("Warning: BME280 sensor not found! Logging blank readings.");
  }

  // Read current time from RTC
  DateTime now = rtc.now();
  char timeBuf[25];
  sprintf(timeBuf, "%04d-%02d-%02dT%02d:%02d:%02d", 
          now.year(), now.month(), now.day(), 
          now.hour(), now.minute(), now.second());

  // Power on and mount SD card
  pinMode(SD_POWER_PIN, OUTPUT);
  digitalWrite(SD_POWER_PIN, HIGH);
  delay(100);

  if (SD.begin(SD_CS_PIN)) {
    // Write CSV header if file doesn't exist
    if (!SD.exists(filename)) {
      File file = SD.open(filename, FILE_WRITE);
      if (file) {
        file.println(csvHeader);
        file.close();
      }
    }

    // Append data row
    File file = SD.open(filename, FILE_APPEND);
    if (file) {
      // Schema format: timestamp,temp_c,hum_pct,pres_hpa,light_lux,uv_idx,soil_pct,rain_mm,wind_spd_ms,wind_dir_deg,bat_v
      // Write temperature, humidity, pressure, and placeholders
      file.printf("%s,", timeBuf);
      if (!isnan(temp)) file.printf("%.2f,", temp); else file.print(",");
      if (!isnan(hum)) file.printf("%.2f,", hum); else file.print(",");
      if (!isnan(pres)) file.printf("%.2f,", pres); else file.print(",");
      file.println(",,,,,,"); // Blank fields for other sensors, no battery voltage yet
      file.close();
      Serial.printf("Logged row to SD card: %s, %.2f, %.2f, %.2f\n", timeBuf, temp, hum, pres);
    } else {
      Serial.println("Error opening file for append!");
    }

    // Close SD card connection
    SD.end();
  } else {
    Serial.println("Error: Failed to initialize SD card!");
  }

  // Turn SD Card power off
  digitalWrite(SD_POWER_PIN, LOW);

  // Schedule the next RTC alarm 1 minute later
  DateTime nextAlarm = DateTime(now.year(), now.month(), now.day(), now.hour(), now.minute() + LOG_INTERVAL_MINUTES, 0);
  rtc.setAlarm1(nextAlarm, DS3231_A1_Minute);
  rtc.clearAlarm(1);

  // Configure Wakeup Sources
  // 1. EXT0 Wakeup (RTC Alarm) on GPIO 36 (LOW)
  pinMode(RTC_INTERRUPT_PIN, INPUT);
  esp_sleep_enable_ext0_wakeup((gpio_num_t)RTC_INTERRUPT_PIN, 0);

  // 2. EXT1 Wakeup (Button) on GPIO 39 (LOW)
  pinMode(BUTTON_PIN, INPUT);
  uint64_t pinMask = 1ULL << BUTTON_PIN;
  esp_sleep_enable_ext1_wakeup(pinMask, ESP_EXT1_WAKEUP_ALL_LOW);

  Serial.printf("Entering deep sleep. Next alarm set for: %02d:%02d:00\n", nextAlarm.hour(), nextAlarm.minute());
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {
  // Never reached
}
