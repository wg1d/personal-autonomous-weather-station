#include "TelemetryUploader.h"

TelemetryUploader::TelemetryUploader() {}

bool TelemetryUploader::uploadCSV(SDManager& sd) {
    HTTPClient http;
    http.begin(SERVER_ENDPOINT);
    http.addHeader("Content-Type", "text/csv");
    
    // Delegate power management to the SDManager
    if (!sd.beginSession()) {
        Serial.println("Error: Failed to mount SD card for upload");
        return false;
    }
    
    bool success = false;
    File file = sd.getFS().open("/weather_data.csv");
    if (file) {
        Serial.print("Uploading CSV file to server: ");
        Serial.println(SERVER_ENDPOINT);
        int httpResponseCode = http.sendRequest("POST", &file, file.size());
        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode);
        
        if (httpResponseCode == 200) {
            success = true;
        }
        file.close();
    } else {
        Serial.println("Failed to open file for uploading");
    }
    http.end();
    
    // Safely power off the SD card when done
    sd.endSession();
    
    return success;
}
