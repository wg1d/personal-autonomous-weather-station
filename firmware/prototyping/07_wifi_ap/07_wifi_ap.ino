/*
 * 07_wifi_ap
 * 
 * Part of the Personal Autonomous Weather Station (PAWS) prototyping guide.
 * 
 * Concept:
 * When the station is in the field, we need a way to manually download the logged
 * data. When the user presses the button, the ESP32 wakes up and enters AP (Access Point) Mode,
 * hosting a local Wi-Fi hotspot and a simple Web Server.
 * 
 * Operations:
 * - Starts softAP with SSID "PAWS-Station" and password "password123".
 * - Starts a WebServer on port 80.
 * - Serves an HTML page listing files on the SD card, with download links.
 * - Shuts down and goes back to deep sleep after 3 minutes (180,000 ms) of inactivity
 *   to avoid draining the battery if left unattended.
 * 
 * Hardware Layout:
 * - Built-in LED on GPIO 2
 * - Push Button on GPIO 39
 * - SD Card (CS = GPIO 5, SCK = GPIO 18, MISO = GPIO 19, MOSI = GPIO 23, VCC Gated = GPIO 13)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <SPI.h>
#include <SD.h>

#define BUTTON_PIN 39
#define SD_POWER_PIN 13
#define SD_CS_PIN 5

// Inactivity timeout: 3 minutes (180,000 milliseconds)
#define RUNTIME_LIMIT_MS 180000 

WebServer server(80);
unsigned long lastActivityTime;

// Handle requests to "/"
void handleRoot() {
  lastActivityTime = millis(); // Reset inactivity timer
  
  String html = "<!DOCTYPE html><html><head><meta charset='utf-8'><title>PAWS Data Download</title>";
  html += "<style>body{font-family:sans-serif;background:#eceff1;margin:40px;}";
  html += ".box{background:#fff;padding:30px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);max-width:500px;margin:auto;}";
  html += "h1{color:#37474f;} ul{padding:0;} li{margin:10px 0;display:flex;justify-content:space-between;}</style></head><body>";
  html += "<div class='box'><h1>🌦️ PAWS Station CSV Download</h1><ul>";

  // List files on SD card
  File root = SD.open("/");
  if (!root) {
    html += "<li>Failed to open SD Card!</li>";
  } else {
    File file = root.openNextFile();
    int count = 0;
    while (file) {
      String fName = String(file.name());
      // Clean leading slash if present
      if (fName.startsWith("/")) {
        fName = fName.substring(1);
      }
      html += "<li><span>📄 " + fName + "</span> <a href='/download?file=" + fName + "'>Download</a></li>";
      file = root.openNextFile();
      count++;
    }
    if (count == 0) {
      html += "<li>No files found on SD card.</li>";
    }
    root.close();
  }
  html += "</ul></div></body></html>";
  
  server.send(200, "text/html", html);
}

// Handle requests to "/download?file=..."
void handleDownload() {
  lastActivityTime = millis(); // Reset inactivity timer

  if (!server.hasArg("file")) {
    server.send(400, "text/plain", "Bad Request: Missing 'file' parameter");
    return;
  }

  String path = "/" + server.arg("file");
  File file = SD.open(path, FILE_READ);
  if (!file) {
    server.send(404, "text/plain", "File Not Found");
    return;
  }

  // Force download behavior in browser
  server.sendHeader("Content-Disposition", "attachment; filename=" + server.arg("file"));
  server.streamFile(file, "text/csv");
  file.close();
}

void shutdownAndSleep() {
  Serial.println("\nInactivity timeout or shutdown triggered. Powering down...");
  
  // Disconnect Wi-Fi and shut down AP
  WiFi.softAPdisconnect(true);
  
  // Power gate SD card OFF
  SD.end();
  digitalWrite(SD_POWER_PIN, LOW);

  // Configure button to wake up next time (EXT1 wakeup, LOW)
  uint64_t pinMask = 1ULL << BUTTON_PIN;
  esp_sleep_enable_ext1_wakeup(pinMask, ESP_EXT1_WAKEUP_ALL_LOW);

  Serial.println("Entering deep sleep...");
  Serial.flush();
  esp_deep_sleep_start();
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  delay(1000);

  Serial.println("==================================================");
  Serial.println("PAWS Step 07: Wi-Fi Access Point & Server Mode");
  Serial.println("==================================================");

  // Power on and mount SD Card
  pinMode(SD_POWER_PIN, OUTPUT);
  digitalWrite(SD_POWER_PIN, HIGH);
  delay(100);

  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("Warning: SD Card not found! Web server will start without SD access.");
  } else {
    Serial.println("SD Card mounted.");
  }

  // Start Access Point
  Serial.println("Starting Wi-Fi Access Point 'PAWS-Station'...");
  WiFi.softAP("PAWS-Station", "password123");
  
  IPAddress apIP = WiFi.softAPIP();
  Serial.print("AP IP Address: ");
  Serial.println(apIP);

  // Configure Server Routes
  server.on("/", handleRoot);
  server.on("/download", handleDownload);
  server.begin();
  Serial.println("HTTP Web server started on port 80.");

  lastActivityTime = millis();
}

void loop() {
  server.handleClient();

  // Shut down if there is no activity for the timeout duration
  if (millis() - lastActivityTime > RUNTIME_LIMIT_MS) {
    Serial.println("Inactivity timeout reached.");
    shutdownAndSleep();
  }
  
  delay(1);
}
