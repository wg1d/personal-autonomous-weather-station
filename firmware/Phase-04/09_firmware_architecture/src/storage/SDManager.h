#ifndef SDMANAGER_H
#define SDMANAGER_H

#include <Arduino.h>
#include <SPI.h>
#include <SD.h>
#include <FS.h>
#include "../sensors/SensorManager.h"
#include "../config.h"

/**
 * @class SDManager
 * @brief Handles all interactions with the SD Card including power management.
 */
class SDManager {
public:
    SDManager();
    
    /**
     * @brief High-level function that powers on, mounts, writes data, and powers off.
     * @param data The SensorData struct containing readings.
     * @return true if data was successfully written.
     */
    bool logData(const SensorData& data);

    /**
     * @brief Powers on the SD card via MOSFET and mounts the filesystem.
     * @return true if mounted successfully.
     */
    bool beginSession();

    /**
     * @brief Safely powers off the SD card.
     */
    void endSession();

    /**
     * @brief Returns a reference to the SD filesystem.
     * @return The underlying fs::FS reference (SD).
     */
    fs::FS& getFS();

private:
    void powerOn();
    void powerOff();
    bool mount();
    void appendCSVRow(const SensorData& data);
    void writeHeaderIfMissing();
};

#endif // SDMANAGER_H
