/*
 * 05_sd_card_logger
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept:
 * SD card readers can draw considerable current (up to 2mA) even when idle.
 * To achieve long battery life, we implement Power Gating.
 * 
 * Power Gating Details:
 * - The SD Card reader VCC pin is powered through a GPIO pin (GPIO 13)
 *   or controlled by a PNP transistor/P-channel MOSFET switched by GPIO 13.
 * - When waking up: Set GPIO 13 HIGH, wait 100ms, and run SD.begin().
 * - When sleeping: Run SD.end() to release SPI pins, then set GPIO 13 LOW
 *   to cut VCC entirely.
 * 
 * Hardware Layout (SPI):
 * - SD MOSI -> GPIO 23 (Shared SPI)
 * - SD MISO -> GPIO 19 (Shared SPI)
 * - SD SCK  -> GPIO 18 (Shared SPI)
 * - SD CS   -> GPIO 5  (Dedicated Chip Select)
 * - SD VCC  -> GPIO 13 (Power Gate control pin)
 */

#include <Arduino.h>
#include <SPI.h>
#include <SD.h>

#define SD_POWER_PIN 13  // Power gate pin
#define SD_CS_PIN 5      // Chip Select pin

const char* filename = "/data.csv";
const char* csvHeader = "timestamp,temp_c,hum_pct,pres_hpa,light_lux,uv_idx,soil_pct,rain_mm,wind_spd_ms,wind_dir_deg,bat_v";

RTC_DATA_ATTR int writeCount = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(1000);

  Serial.println("==================================================");
  Serial.println("PAWS Step 05: SD Card Logger & Power Gating");
  Serial.println("==================================================");

  // 1. Power ON the SD Card module
  pinMode(SD_POWER_PIN, OUTPUT);
  Serial.println("Powering ON the SD Card reader (GPIO 13 -> HIGH)...");
  digitalWrite(SD_POWER_PIN, HIGH);
  delay(100); // Give the module time to stabilize voltage

  // 2. Initialize SD Card
  Serial.println("Mounting SD Card...");
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("CRITICAL ERROR: Failed to mount SD card!");
    // Turn off power before failing
    digitalWrite(SD_POWER_PIN, LOW);
    while (1) {
      delay(10);
    }
  }
  Serial.println("SD Card mounted successfully.");

  // 3. Write CSV header if the file does not exist
  if (!SD.exists(filename)) {
    Serial.println("data.csv not found. Creating file and writing header...");
    File file = SD.open(filename, FILE_WRITE);
    if (file) {
      file.println(csvHeader);
      file.close();
    } else {
      Serial.println("Error creating data.csv!");
    }
  }

  // 4. Log a mock measurement row
  writeCount++;
  File file = SD.open(filename, FILE_APPEND);
  if (file) {
    // Schema format: timestamp,temp_c,hum_pct,pres_hpa,light_lux,uv_idx,soil_pct,rain_mm,wind_spd_ms,wind_dir_deg,bat_v
    // Using simple simulated data
    file.printf("2026-07-15T12:00:%02d,23.50,55.40,1012.30,,,,,,,3.95\n", writeCount);
    file.close();
    Serial.println("Successfully logged mock measurement to data.csv.");
  } else {
    Serial.println("Error opening file for appending!");
  }

  // 5. Read and dump data.csv contents to Serial for verification
  File readFile = SD.open(filename, FILE_READ);
  if (readFile) {
    Serial.println("\n--- Current data.csv Contents ---");
    while (readFile.available()) {
      Serial.write(readFile.read());
    }
    readFile.close();
    Serial.println("---------------------------------");
  }

  // 6. Close SD card connection and power OFF
  SD.end();
  Serial.println("Closing SD communication and powering OFF SD card (GPIO 13 -> LOW)...");
  digitalWrite(SD_POWER_PIN, LOW);

  // We go to a standard 10-second timer deep sleep for this demo
  esp_sleep_enable_timer_wakeup(10 * 1000000ULL); // 10 seconds in microseconds
  Serial.println("Entering Deep Sleep for 10 seconds...");
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {
  // Never reached
}
