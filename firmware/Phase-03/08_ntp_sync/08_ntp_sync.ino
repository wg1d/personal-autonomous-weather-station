/*
 * Project: Personal Autonomous Weather Station
 * Phase 03: Wi-Fi & Data Transmission
 * File: 07_wifi_fallback_ap.ino
 * 
 * Description:
 * Implements a dual-boot logic. If woken by the RTC timer (EXT0), it logs
 * data, connects to Wi-Fi, uploads the CSV, and goes to sleep.
 * If woken by the Fallback Button on Pin 39 (EXT1), it starts a local
 * Access Point and hosts a web server to download or delete the CSV.
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
#include <ESPAsyncWebServer.h>
#include <time.h>
#include "secrets.h"

#define SD_CS_PIN 5
#define SD_OFF_PIN 13
#define RTC_WAKEUP_PIN 36
#define FALLBACK_BUTTON_PIN 39

Adafruit_BME280 bme;
RTC_DS3231 rtc;
AsyncWebServer server(80);

const int WAKEUP_INTERVAL_SECONDS = 30;
const char* serverName = "http://192.168.1.15:5000/upload";

void appendFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_APPEND);
  if (file) {
    file.print(message);
    file.close();
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n--- Waking up from Deep Sleep ---");
  
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  
  if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT1) {
    // ==========================================
    // PATH A: FALLBACK ACCESS POINT MODE
    // ==========================================
    Serial.println("Wakeup by Fallback Button! Starting AP Mode...");
    
    // 1. Power on SD Card to serve the file
    pinMode(SD_OFF_PIN, OUTPUT);
    digitalWrite(SD_OFF_PIN, HIGH); // Power on the SD card
    delay(500); // Wait for power to stabilize
    if (!SD.begin(SD_CS_PIN)) {
      Serial.println("Card Mount Failed in AP mode");
    }
    
    // 2. Start Wi-Fi Access Point
    WiFi.softAP("WeatherStation_AP", "12345678");
    Serial.print("AP IP address: ");
    Serial.println(WiFi.softAPIP());
    
    // 3. Setup Web Server Routes
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
      String html = "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>";
      html += "<style>body{font-family:Arial,sans-serif;text-align:center;padding:50px;}";
      html += "button{padding:15px 30px;font-size:18px;margin:10px;cursor:pointer;border:none;border-radius:8px;}";
      html += ".btn-down{background:#4CAF50;color:white;} .btn-del{background:#f44336;color:white;}</style></head>";
      html += "<body><h1>Weather Station</h1>";
      html += "<a href='/download'><button class='btn-down'>Download CSV</button></a><br><br>";
      html += "<form action='/delete' method='POST'><button type='submit' class='btn-del'>Delete Old Data</button></form>";
      html += "</body></html>";
      request->send(200, "text/html", html);
    });
    
    server.on("/download", HTTP_GET, [](AsyncWebServerRequest *request){
      if(!SD.exists("/weather_data.csv")) {
        request->send(404, "text/plain", "File not found.");
        return;
      }
      Serial.println("User is downloading weather_data.csv...");
      request->send(SD, "/weather_data.csv", "text/csv", true);
    });
    
    server.on("/delete", HTTP_POST, [](AsyncWebServerRequest *request){
      if(SD.exists("/weather_data.csv")) {
        SD.remove("/weather_data.csv");
        Serial.println("User deleted weather_data.csv!");
      }
      request->send(200, "text/html", "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'><style>body{font-family:Arial,text-align:center;padding:50px;}</style></head><body><h2>Data Deleted!</h2><a href='/'>Back</a></body></html>");
    });
    
    server.begin();
    Serial.println("Web server started.");
    
    // Return from setup() to allow loop() to handle the 3-minute timeout
    return;
  }
  
  // ==========================================
  // PATH B: STANDARD SENSOR & UPLOAD MODE
  // ==========================================
  Serial.println("Standard Wakeup (RTC Timer). Taking reading...");
  
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC");
    esp_deep_sleep_start();
  }
  if (rtc.lostPower()) rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));

  // Capture timestamp immediately before any delays!
  DateTime bootTime = rtc.now();
  
  rtc.disable32K(); 
  rtc.writeSqwPinMode(DS3231_OFF); 
  rtc.disableAlarm(2);
  rtc.clearAlarm(1);
  
  if (!bme.begin(0x76)) {
    Serial.println("Could not find a valid BME280 sensor, check wiring!");
    esp_deep_sleep_start();
  }

  pinMode(SD_OFF_PIN, OUTPUT);
  digitalWrite(SD_OFF_PIN, HIGH);
  delay(500); 
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("Card Mount Failed");
  } else {
    char timestamp[25];
    sprintf(timestamp, "%04d-%02d-%02dT%02d:%02d:%02d", 
            bootTime.year(), bootTime.month(), bootTime.day(), 
            bootTime.hour(), bootTime.minute(), bootTime.second());
    
    char dataString[100];
    sprintf(dataString, "%s;%.2f;%.2f;%.2f\n", 
            timestamp, bme.readTemperature(), bme.readHumidity(), bme.readPressure() / 100.0F);
    
    Serial.print("Data: ");
    Serial.print(dataString);
    
    if(!SD.exists("/weather_data.csv")) {
      appendFile(SD, "/weather_data.csv", "Timestamp;Temperature(C);Humidity(%);Pressure(hPa)\n");
    }
    appendFile(SD, "/weather_data.csv", dataString);
    Serial.println("Data saved to SD card.");
    
    // Connect to Wi-Fi and Upload
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to WiFi...");
    
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
      
      File file = SD.open("/weather_data.csv");
      if (file) {
        Serial.print("Uploading CSV file to server: ");
        Serial.println(serverName);
        int httpResponseCode = http.sendRequest("POST", &file, file.size());
        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode);
        file.close();
      } else {
        Serial.println("Failed to open file for uploading");
      }
      http.end();
      
      // Bonus: NTP Time Synchronization
      Serial.println("Synchronizing DS3231 RTC with NTP...");
      configTime(0, 0, "pool.ntp.org");
      
      struct tm timeinfo;
      if (getLocalTime(&timeinfo, 5000)) { // 5-second timeout
        Serial.println("NTP Time acquired!");
        
        // Convert NTP time to Unix timestamp
        time_t ntpUnix = mktime(&timeinfo);
        uint32_t rtcUnix = rtc.now().unixtime();
        
        // Only update if drift is greater than 2 seconds to prevent sub-second truncation
        if (abs((long)(ntpUnix - rtcUnix)) > 2) {
          Serial.println("Drift detected! Updating RTC...");
          rtc.adjust(DateTime(timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday, 
                              timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec));
        } else {
          Serial.println("RTC time is accurate. No update needed.");
        }
      } else {
        Serial.println("Failed to obtain time from NTP server.");
      }
      
    } else {
      Serial.println("\nWiFi connection failed, aborting upload.");
    }
    
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
  }
  
  digitalWrite(SD_OFF_PIN, LOW); // Power OFF SD card
  
  // 5. Set the next wake-up alarm exactly on the grid
  DateTime now = rtc.now();
  uint32_t currentUnix = now.unixtime();
  uint32_t remainder = currentUnix % WAKEUP_INTERVAL_SECONDS;
  uint32_t nextAlarmUnix = currentUnix - remainder + WAKEUP_INTERVAL_SECONDS;
  DateTime future(nextAlarmUnix);
  
  if (!rtc.setAlarm1(future, DS3231_A1_Hour)) {
    Serial.println("Error setting alarm!");
  } else {
      Serial.printf("Next reading scheduled for: %02d:%02d:%02d\n", 
                    future.hour(), future.minute(), future.second());
  }

  // Go to Deep Sleep
  esp_sleep_enable_ext0_wakeup((gpio_num_t)RTC_WAKEUP_PIN, 0);
  esp_sleep_enable_ext1_wakeup(1ULL << FALLBACK_BUTTON_PIN, ESP_EXT1_WAKEUP_ANY_HIGH);
  
  Serial.println("Entering Deep Sleep...");
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  if (wakeup_reason == ESP_SLEEP_WAKEUP_EXT1) {
    // AP Mode Timeout Logic (3 Minutes = 180000 ms)
    static unsigned long apStartTime = millis();
    static unsigned long lastPrintTime = millis();
    unsigned long elapsed = millis() - apStartTime;
    
    // Print remaining time every 10 seconds
    if (millis() - lastPrintTime >= 10000) {
      lastPrintTime = millis();
      int remainingSeconds = (180000 - elapsed) / 1000;
      Serial.printf("AP Mode shutting down in %d seconds...\n", remainingSeconds);
    }

    if (elapsed > 180000) {
      Serial.println("\nAP Timeout reached. Shutting down...");
      
      // Cleanup
      WiFi.softAPdisconnect(true);
      WiFi.mode(WIFI_OFF);
      digitalWrite(SD_OFF_PIN, LOW); // Power off SD Card
      
      // Arm wakeups again
      esp_sleep_enable_ext0_wakeup((gpio_num_t)RTC_WAKEUP_PIN, 0);
      esp_sleep_enable_ext1_wakeup(1ULL << FALLBACK_BUTTON_PIN, ESP_EXT1_WAKEUP_ANY_HIGH);
      
      Serial.println("Entering Deep Sleep...");
      Serial.flush();
      esp_deep_sleep_start();
    }
  }
}
