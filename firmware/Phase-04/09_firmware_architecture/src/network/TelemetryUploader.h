#ifndef TELEMETRYUPLOADER_H
#define TELEMETRYUPLOADER_H

#include <Arduino.h>
#include <HTTPClient.h>
#include "../storage/SDManager.h"
#include "../config.h"

/**
 * @class TelemetryUploader
 * @brief Responsible for pushing data to the backend REST API via HTTP POST.
 */
class TelemetryUploader {
public:
    TelemetryUploader();
    
    /**
     * @brief Reads the weather_data.csv from the SD card and uploads it.
     * @param sd Reference to the SDManager to handle file access and power.
     * @return true if the server returns a 200 OK.
     */
    bool uploadCSV(SDManager& sd);
};

#endif // TELEMETRYUPLOADER_H
