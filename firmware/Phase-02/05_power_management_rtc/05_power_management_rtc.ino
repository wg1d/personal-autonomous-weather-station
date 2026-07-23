/*
 * Project: Personal Autonomous Weather Station
 * Phase 02: Power Management
 * File: 05_power_management_rtc.ino
 * 
 * Description:
 * This sketch implements a fully autonomous deep sleep architecture.
 * The ESP32 relies on a DS3231 RTC to wake it up via an external
 * interrupt (EXT0).
 * Upon waking, it reads the BME280 sensor, powers ON the SD card, saves the 
 * data with an accurate timestamp, schedules the next RTC alarm, and
 * immediately returns to deep sleep to conserve battery.
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

#define SD_CS_PIN 5
#define SD_OFF_PIN 13
#define RTC_WAKEUP_PIN 36

Adafruit_BME280 bme;
RTC_DS3231 rtc;

// How often should the station wake up to take a reading? 
// (In seconds for testing)
const int WAKEUP_INTERVAL_SECONDS = 30;

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
      Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason);
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
    esp_deep_sleep_start(); // Sleep forever if RTC fails
  }

  // If the RTC lost power (e.g., battery died or first time use),
  // set the time to the compile time. We don't do this unconditionally
  // to avoid resetting the time on every deep sleep wake-up.
  if (rtc.lostPower()) {
    Serial.println("RTC lost power, setting the time to compile time!");
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  // Read the time immediately after waking up for maximum accuracy!
  DateTime now = rtc.now();

  // Power optimizations & alarm resets
  rtc.disable32K(); // Disable the 32kHz output to save power
  // Stop oscillating signals at SQW Pin (required for alarms)
  rtc.writeSqwPinMode(DS3231_OFF); 
  rtc.disableAlarm(2); // Disable Alarm 2 so it doesn't accidentally trigger
  
  // Clear any existing alarm flags so the SQW pin goes back HIGH
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

  // 3. Power ON the SD Card and save data
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

  // Power OFF the SD card module
  SD.end();
  digitalWrite(SD_OFF_PIN, LOW);

  // 4. Set the next wake-up alarm
  // To ensure the station wakes up perfectly on the grid (e.g., exactly at 
  // :00 and :30 seconds) and doesn't drift over time, we calculate the next 
  // perfect interval using Unix time (seconds since 1970).
  uint32_t currentUnix = now.unixtime();
  uint32_t remainder = currentUnix % WAKEUP_INTERVAL_SECONDS;
  uint32_t nextAlarmUnix = currentUnix - remainder + WAKEUP_INTERVAL_SECONDS;
  DateTime future(nextAlarmUnix);
  
  // Set Alarm 1 to trigger when the time matches.
  // Note: DS3231_A1_Hour is confusingly named! It actually means 
  // "Match Hours, Minutes, and Seconds". This ensures the alarm fires 
  // exactly once at the future time we just calculated.
  if (!rtc.setAlarm1(future, DS3231_A1_Hour)) {
      Serial.println("Error, alarm wasn't set!");
  } else {
      Serial.printf("Next reading scheduled for: %02d:%02d:%02d\n", 
                    future.hour(), future.minute(), future.second());
  }

  // 5. Configure ESP32 Deep Sleep Wake-up Source
  // We use EXT0 to wake up when the RTC pulls pin 36 LOW
  esp_sleep_enable_ext0_wakeup((gpio_num_t)RTC_WAKEUP_PIN, 0);

  // 6. Go to Sleep
  Serial.println("Entering Deep Sleep...");
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {
  // We never reach the loop() because esp_deep_sleep_start() halts execution!
}
