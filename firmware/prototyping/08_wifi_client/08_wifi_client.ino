/*
 * 08_wifi_client
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept:
 * Instead of manual download, this sketch demonstrates automated synchronization.
 * The ESP32 connects to the home Wi-Fi network, reads the raw contents of
 * `/data.csv` from the SD card, and performs an HTTP POST request to upload it
 * to a simple Python server running on your Linux host.
 * 
 * Operations:
 * 1. Initialize SD card (with power gating).
 * 2. Connect to local Wi-Fi router.
 * 3. Read `/data.csv` content.
 * 4. Issue HTTP POST to upload file content.
 * 5. Disconnect Wi-Fi, shut down SD card, and go to Deep Sleep.
 * 
 * Hardware Layout:
 * - SD Card (CS = GPIO 5, SCK = GPIO 18, MISO = GPIO 19, MOSI = GPIO 23, VCC Gated = GPIO 13)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <SD.h>

#define SD_POWER_PIN 13
#define SD_CS_PIN 5

// Wi-Fi Credentials - Update these to match your local setup!
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Linux Host Receiver Server Configuration
const char* serverIP = "192.168.1.50"; // Update to your Linux host's local IP address
const int serverPort = 8000;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(1000);

  Serial.println("==================================================");
  Serial.println("PAWS Step 08: Wi-Fi Client & Data Upload");
  Serial.println("==================================================");

  // 1. Power ON and mount the SD Card
  pinMode(SD_POWER_PIN, OUTPUT);
  digitalWrite(SD_POWER_PIN, HIGH);
  delay(100);

  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("CRITICAL ERROR: SD Card not found! Cannot upload data.");
    digitalWrite(SD_POWER_PIN, LOW);
    return;
  }

  // 2. Connect to Wi-Fi
  Serial.printf("Connecting to Wi-Fi SSID: %s...\n", ssid);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  // Try connecting for 10 seconds max (20 * 500ms)
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nFailed to connect to Wi-Fi. Aborting upload.");
    SD.end();
    digitalWrite(SD_POWER_PIN, LOW);
    return;
  }

  Serial.print("\nConnected successfully! IP address: ");
  Serial.println(WiFi.localIP());

  // 3. Read data from SD Card
  File file = SD.open("/data.csv", FILE_READ);
  if (file) {
    String csvData = "";
    // Note: In an actual deployment, if data.csv is very large, reading the entire
    // file into a String variable is not recommended due to limited RAM. For this
    // prototyping step, we read the entire file.
    while (file.available()) {
      csvData += (char)file.read();
    }
    file.close();

    // 4. Perform HTTP POST request
    HTTPClient http;
    String serverUrl = "http://" + String(serverIP) + ":" + String(serverPort) + "/api/upload";
    Serial.printf("Uploading CSV to %s...\n", serverUrl.c_str());

    http.begin(serverUrl);
    http.addHeader("Content-Type", "text/csv");

    int httpResponseCode = http.POST(csvData);
    if (httpResponseCode > 0) {
      Serial.printf("HTTP Response code: %d\n", httpResponseCode);
      if (httpResponseCode == 200) {
        String response = http.getString();
        Serial.printf("Server Response: %s\n", response.c_str());
      }
    } else {
      Serial.printf("HTTP POST failed, error: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    Serial.println("Error: /data.csv not found on SD card!");
  }

  // 5. Clean up and go to sleep
  WiFi.disconnect(true);
  SD.end();
  digitalWrite(SD_POWER_PIN, LOW); // Power gate OFF

  Serial.println("Upload process complete. Entering deep sleep (10 seconds timer)...");
  esp_sleep_enable_timer_wakeup(10 * 1000000ULL);
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {
  // Never reached
}
