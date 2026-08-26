/*
 * Project: Personal Autonomous Weather Station
 * Phase 01: Real-Time Clock
 * File: 03_real_time_clock.ino
 * 
 * Description:
 * This sketch initializes the BME280 sensor, DS3231 RTC, and the SD Card.
 * It reads temperature, humidity, pressure, and absolute time.
 * The data is appended to a CSV file every 5 seconds.
 */

#include <Arduino.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <SPI.h>
#include <SD.h>
#include <FS.h>
#include <RTClib.h>

#define SD_CS_PIN 5

Adafruit_BME280 bme;
RTC_DS3231 rtc;

// Helper function to append a string to a file on the SD card
void appendFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_APPEND);
  if (!file) {
    Serial.println("Failed to open file for appending");
    return;
  }
  if (!file.print(message)) {
    Serial.println("Append failed");
  }
  file.close();
}

void setup() {
  Serial.begin(115200);
  Serial.println("\nInitializing Weather Station...");

  // Initialize BME280
  if (!bme.begin(0x76)) {
    Serial.println("Could not find a valid BME280 sensor!");
    while (1) delay(10);
  }

  // Initialize DS3231 RTC
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1) delay(10);
  }
  
  if (rtc.lostPower()) {
    Serial.println("RTC lost power, let's set the time!");
    // When time needs to be set on a new device, or after a power loss, the
    // following line sets the RTC to the date & time this sketch was compiled
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  // 1. Disable the 32K output (we don't need it)
  rtc.disable32K();

  // 2. Stop the SQW pin from oscillating 
  // (It must be turned off for the alarms to control this pin later)
  rtc.writeSqwPinMode(DS3231_OFF);

  // 3. Turn off both Alarm 1 and Alarm 2
  // (Settings are kept on battery, so we must explicitly disable them)
  rtc.disableAlarm(1);
  rtc.disableAlarm(2);

  // 4. Clear any existing alarm flags
  // (Ensures the RTC doesn't think an alarm just went off)
  rtc.clearAlarm(1);
  rtc.clearAlarm(2);

  // Initialize SD Card
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("Card Mount Failed.");
    while (1) delay(10);
  }

  uint8_t cardType = SD.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("No SD card attached");
    while (1) delay(10);
  }

  // Create the CSV file header
  if (!SD.exists("/weather_data.csv")) {
    File file = SD.open("/weather_data.csv", FILE_WRITE);
    if (file) {
      file.println("timestamp;temperature;humidity;pressure");
      file.close();
      Serial.println("Created weather_data.csv with header.");
    }
  }
}

void loop() {
  // Read absolute time from RTC
  DateTime now = rtc.now();
  
  // Read data from BME280
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;

  // Format timestamp (YYYY-MM-DDTHH:MM:SS)
  char timestamp[20];
  sprintf(timestamp, "%04d-%02d-%02dT%02d:%02d:%02d", 
          now.year(), now.month(), now.day(),
          now.hour(), now.minute(), now.second());

  // Print to Serial for debugging
  Serial.println("-------------------------");
  Serial.printf("Time: %s\n", timestamp);
  Serial.printf("Temperature: %.2f *C\n", temperature);
  Serial.printf("Humidity: %.2f %%\n", humidity);
  Serial.printf("Pressure: %.2f hPa\n", pressure);

  // Format the data into a CSV string
  char dataString[100];
  sprintf(dataString, "%s;%.2f;%.2f;%.2f\n", 
          timestamp, temperature, humidity, pressure);

  // Save to SD Card
  appendFile(SD, "/weather_data.csv", dataString);
  Serial.println("Data saved to SD card.");

  // Wait for 5 seconds
  delay(5000); 
}
