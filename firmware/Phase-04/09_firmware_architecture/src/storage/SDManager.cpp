#include "SDManager.h"

SDManager::SDManager() {}

bool SDManager::logData(const SensorData& data) {
    if (!beginSession()) {
        return false;
    }
    
    writeHeaderIfMissing();
    appendCSVRow(data);
    
    endSession();
    return true;
}

bool SDManager::beginSession() {
    powerOn();
    return mount();
}

void SDManager::endSession() {
    powerOff();
}

fs::FS& SDManager::getFS() {
    return SD;
}

void SDManager::powerOn() {
    pinMode(SD_OFF_PIN, OUTPUT);
    digitalWrite(SD_OFF_PIN, HIGH);
    delay(500); // Wait for power to stabilize
}

void SDManager::powerOff() {
    digitalWrite(SD_OFF_PIN, LOW);
}

bool SDManager::mount() {
    if (!SD.begin(SD_CS_PIN)) {
        Serial.println("Error: Card Mount Failed");
        return false;
    }
    return true;
}

void SDManager::writeHeaderIfMissing() {
    if (!SD.exists("/weather_data.csv")) {
        File file = SD.open("/weather_data.csv", FILE_APPEND);
        if (file) {
            file.print("Timestamp;Temperature(C);Humidity(%);Pressure(hPa)\n");
            file.close();
        }
    }
}

void SDManager::appendCSVRow(const SensorData& data) {
    char dataString[100];
    sprintf(dataString, "%s;%.2f;%.2f;%.2f\n", 
            data.timestamp.c_str(), data.temperature, data.humidity, data.pressure);
            
    Serial.print("Data: ");
    Serial.print(dataString);
            
    File file = SD.open("/weather_data.csv", FILE_APPEND);
    if (file) {
        file.print(dataString);
        file.close();
        Serial.println("Data saved to SD card.");
    } else {
        Serial.println("Error: Failed to open file for appending");
    }
}
