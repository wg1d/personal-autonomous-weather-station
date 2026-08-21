#ifndef RTCMANAGER_H
#define RTCMANAGER_H

#include <Arduino.h>
#include <RTClib.h>
#include "../config.h"

/**
 * @class RTCManager
 * @brief Manages the DS3231 Real-Time Clock, handling timekeeping and alarms.
 */
class RTCManager {
public:
    RTCManager();
    
    /**
     * @brief Initializes the DS3231, setting time if power was lost.
     * @return true if successfully found.
     */
    bool begin();
    
    /**
     * @brief Returns the current time formatted as an ISO 8601 string.
     * @return String formatted as YYYY-MM-DDTHH:MM:SS
     */
    String getISOTimestamp();
    
    /**
     * @brief Returns the current hour (0-23).
     */
    int getCurrentHour();
    
    /**
     * @brief Calculates and sets the next WAKEUP_INTERVAL_SECONDS alarm.
     */
    void setNextAlarm();
    
    /**
     * @brief Syncs the DS3231 time with pool.ntp.org.
     */
    void syncNTP();

private:
    RTC_DS3231 _rtc;
};

#endif // RTCMANAGER_H
