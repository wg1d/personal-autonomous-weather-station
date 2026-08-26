/*
 * Project: Personal Autonomous Weather Station
 * Phase 01: Data Storage
 * File: 02_data_storage.ino
 * 
 * Description:
 * This sketch initializes the BME280 sensor and the SD Card module.
 * It continuously reads the temperature, humidity, and atmospheric pressure. 
 * The data is appended to a CSV file on the SD card every 5 seconds.
 *
 * Wiring:
 * - BME280: 3V3 -> VIN, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL
 * - SD Card: 5V -> VCC, GND -> GND, Pin 19 -> MISO, 
 *   Pin 23 -> MOSI, Pin 18 -> SCLK, Pin 5 -> CS
 */

#include <Arduino.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <SPI.h>
#include <SD.h>
#include <FS.h>

#define SD_CS_PIN 5

Adafruit_BME280 bme;

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
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
    while (1) delay(10);
  }

  // Initialize SD Card
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("Card Mount Failed. Check wiring "
                   "and make sure an SD card is inserted.");
    while (1) delay(10);
  }

  // Check if an SD card is actually attached
  uint8_t cardType = SD.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("No SD card attached");
    while (1) delay(10);
  }

  // Create the CSV file header if the file doesn't exist
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
  // 1. Read data from BME280
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;

  // Print to Serial for debugging
  Serial.println("-------------------------");
  Serial.printf("Temperature: %.2f *C\n", temperature);
  Serial.printf("Humidity: %.2f %%\n", humidity);
  Serial.printf("Pressure: %.2f hPa\n", pressure);

  // 2. Format the data into a CSV string
  // Note: We don't have a real-time clock yet, 
  // so we'll use millis() as a placeholder timestamp
  char dataString[100];
  sprintf(dataString, "%lu;%.2f;%.2f;%.2f\n", 
          millis(), temperature, humidity, pressure);

  // 3. Save to SD Card
  appendFile(SD, "/weather_data.csv", dataString);
  Serial.println("Data saved to SD card.");

  // Wait for 5 seconds before taking the next reading
  delay(5000); 
}
