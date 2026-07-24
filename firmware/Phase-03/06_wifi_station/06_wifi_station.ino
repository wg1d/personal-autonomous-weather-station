/*
 * Project: Personal Autonomous Weather Station
 * Phase 03: Wi-Fi & Data Transmission
 * File: 06_wifi_station.ino
 * 
 * Description:
 * This sketch builds on Phase 02 by adding Wi-Fi capabilities.
 * After reading sensors and logging to the SD card, the ESP32
 * connects to Wi-Fi and uploads the data to a local server
 * via an HTTP POST request before going back to deep sleep.
 *
 * Wiring:
 * - BME280:  3.3V -> VIN, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL
 * - DS3231:  3.3V -> VCC, GND -> GND, Pin 21 -> SDA, Pin 22 -> SCL, 
 *            Pin 36 -> SQW (Requires a 10k pull-up resistor to 3.3V)
 * - SD Card: 5V   -> VCC, GND -> GND, Pin 19 -> MISO, Pin 23 -> MOSI, 
 *            Pin 18 -> SCLK, Pin 5 -> CS, 
 *            Pin 13 -> OFF (Requires a 10k pull-down resistor to GND)
 */

#include <Arduino.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <SPI.h>
#include <SD.h>
#include <FS.h>
#include <RTClib.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "secrets.h"

#define SD_CS_PIN 5
#define SD_OFF_PIN 13
#define RTC_WAKEUP_PIN 36

Adafruit_BME280 bme;
RTC_DS3231 rtc;

// How often should the station wake up to take a reading? 
const int WAKEUP_INTERVAL_SECONDS = 30;

// Dummy server endpoint (Update with your computer's local IP address)
const char* serverName = "http://192.168.1.15:5000/upload";

void appendFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_APPEND);
  if (file) {
    file.print(message);
    file.close();
  }
}

void print_wakeup_reason(){
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  switch(wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0: 
      Serial.println("Wakeup by external signal using RTC_IO (RTC Alarm)"); 
      break;
    case ESP_SLEEP_WAKEUP_EXT1: 
      Serial.println("Wakeup by external signal using RTC_CNTL"); 
      break;
    case ESP_SLEEP_WAKEUP_TIMER: 
      Serial.println("Wakeup caused by timer"); 
      break;
    case ESP_SLEEP_WAKEUP_TOUCHPAD: 
      Serial.println("Wakeup caused by touchpad"); 
      break;
    case ESP_SLEEP_WAKEUP_ULP: 
      Serial.println("Wakeup caused by ULP program"); 
      break;
    default: 
      Serial.printf("Wakeup not caused by deep sleep: %d\n", wakeup_reason);
      break;
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n--- Waking up from Deep Sleep ---");
  print_wakeup_reason();

  // 1. Initialize RTC
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    Serial.flush();
    esp_deep_sleep_start();
  }
  
  // Set the time if the coin cell died or first boot
  if (rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
  
  DateTime now = rtc.now();
  
  // RTC Power optimizations & alarm resets (carried over from Phase 02)
  rtc.disable32K(); 
  rtc.writeSqwPinMode(DS3231_OFF); 
  rtc.disableAlarm(2); // Disable Alarm 2 to prevent accidental overlapping
  rtc.clearAlarm(1);
  rtc.clearAlarm(2);

  // 2. Initialize BME280 and read data
  if (!bme.begin(0x76)) {
    Serial.println("Could not find a valid BME280 sensor!");
  }
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;

  // Format the data string using the built-in toString method
  char timestamp[] = "YYYY-MM-DDThh:mm:ss";
  now.toString(timestamp);

  char dataString[100];
  sprintf(dataString, "%s;%.2f;%.2f;%.2f\n", 
          timestamp, temperature, humidity, pressure);
          
  Serial.print("Data: ");
  Serial.print(dataString);

  // 3. Power ON the SD Card and save data (CSV format for storage efficiency)
  pinMode(SD_OFF_PIN, OUTPUT);
  digitalWrite(SD_OFF_PIN, HIGH);
  delay(100); // Wait for the SD card to power up and stabilize

  if (SD.begin(SD_CS_PIN)) {
    // Create header if file doesn't exist
    if (!SD.exists("/weather_data.csv")) {
      File file = SD.open("/weather_data.csv", FILE_WRITE);
      if (file) {
        file.println("timestamp;temperature;humidity;pressure");
        file.close();
      }
    }
    appendFile(SD, "/weather_data.csv", dataString);
    Serial.println("Data saved to SD card.");
  } else {
    Serial.println("Failed to mount SD card.");
  }
  
  // Notice: We keep the SD card powered ON because we need to read it 
  // during the Wi-Fi upload step!

  // 4. Upload Data via Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi...");
  
  // Timeout after 10 seconds to save battery if network is down
  int wifi_timeout = 0;
  while (WiFi.status() != WL_CONNECTED && wifi_timeout < 20) {
    delay(500);
    Serial.print(".");
    wifi_timeout++;
  }

  if(WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnected to WiFi network");
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "text/csv");
    
    // Open the CSV file from the SD card
    File file = SD.open("/weather_data.csv");
    if (file) {
      Serial.print("Uploading CSV file to server: ");
      Serial.println(serverName);
      
      // Stream the file directly to the server to save RAM
      int httpResponseCode = http.sendRequest("POST", &file, file.size());
      
      if (httpResponseCode > 0) {
        Serial.printf("HTTP Response code: %d\n", httpResponseCode);
      } else {
        Serial.printf("Error code: %d\n", httpResponseCode);
      }
      file.close();
    } else {
      Serial.println("Failed to open CSV file for uploading.");
    }
    http.end();
  } else {
    Serial.println("\nWiFi connection failed, skipped upload");
  }

  // Turn off Wi-Fi to save power before sleeping
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);

  // Power OFF the SD card module now that the upload is complete
  SD.end();
  digitalWrite(SD_OFF_PIN, LOW);

  // 5. Set the next wake-up alarm exactly on the grid
  uint32_t currentUnix = now.unixtime();
  uint32_t remainder = currentUnix % WAKEUP_INTERVAL_SECONDS;
  uint32_t nextAlarmUnix = currentUnix - remainder + WAKEUP_INTERVAL_SECONDS;
  DateTime future(nextAlarmUnix);
  
  if (!rtc.setAlarm1(future, DS3231_A1_Hour)) {
      Serial.println("Error, alarm wasn't set!");
  } else {
      Serial.printf("Next reading scheduled for: %02d:%02d:%02d\n", 
                    future.hour(), future.minute(), future.second());
  }

  // 6. Configure ESP32 Deep Sleep Wake-up Source
  esp_sleep_enable_ext0_wakeup((gpio_num_t)RTC_WAKEUP_PIN, 0);

  // 7. Go to Sleep
  Serial.println("Entering Deep Sleep...");
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {
  // We never reach the loop() because esp_deep_sleep_start() halts execution!
}
