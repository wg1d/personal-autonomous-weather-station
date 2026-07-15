/*
 * 03_temp_humidity_sensor
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept:
 * Environmental monitoring is done via the BME280 sensor over I2C. 
 * I2C uses two shared lines: SDA (Data) and SCL (Clock) to address multiple devices.
 * 
 * Deep Sleep Power Management:
 * - The BME280 sensor is extremely low power: in standby mode, it draws only 0.1 uA.
 * - When the ESP32 enters deep sleep, we can leave the BME280 connected because its
 *   standby current is negligible.
 * - To read the sensor, we wake the ESP32, read the values, and immediately put the
 *   ESP32 back to deep sleep (we use a simple delay loop in this test to watch real-time readings).
 * 
 * Hardware Layout:
 * - BME280 SDA -> GPIO 21
 * - BME280 SCL -> GPIO 22
 * - BME280 VCC -> 3.3V
 * - BME280 GND -> GND
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

// I2C pins
#define I2C_SDA 21
#define I2C_SCL 22

Adafruit_BME280 bme; // Create sensor instance

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(1000);

  Serial.println("==================================================");
  Serial.println("PAWS Step 03: Temperature/Humidity/Pressure (BME280)");
  Serial.println("==================================================");

  // Initialize I2C with specified pins
  Wire.begin(I2C_SDA, I2C_SCL);

  // Attempt to initialize BME280 (common address is 0x76, fallback to 0x77)
  Serial.println("Scanning for BME280 sensor...");
  bool status = bme.begin(0x76, &Wire);
  if (!status) {
    status = bme.begin(0x77, &Wire);
  }

  if (!status) {
    Serial.println("CRITICAL ERROR: BME280 sensor not found! Check wiring and pull-ups.");
    while (1) {
      delay(1000);
    }
  }

  Serial.println("BME280 sensor initialized successfully.");
}

void loop() {
  // Read and print temperature, humidity, and pressure
  float temp = bme.readTemperature();
  float hum  = bme.readHumidity();
  float pres = bme.readPressure() / 100.0F; // Convert Pascal (Pa) to Hectopascal (hPa)

  Serial.printf("Temp: %.2f °C | Humidity: %.2f %% | Pressure: %.2f hPa\n", temp, hum, pres);

  // Wait 5 seconds before the next reading
  delay(5000);
}
