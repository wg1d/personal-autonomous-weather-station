#include "RTCManager.h"
#include <time.h>

RTCManager::RTCManager() {}

bool RTCManager::begin() {
    if (!_rtc.begin()) {
        Serial.println("Error: Couldn't find RTC");
        return false;
    }
    
    if (_rtc.lostPower()) {
        Serial.println("RTC lost power, setting to compile time!");
        _rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    }
    
    // Clear alarms and configure SQW pin
    _rtc.disable32K(); 
    _rtc.writeSqwPinMode(DS3231_OFF); 
    _rtc.disableAlarm(2);
    _rtc.clearAlarm(1);
    
    return true;
}

String RTCManager::getISOTimestamp() {
    DateTime now = _rtc.now();
    char timestamp[25];
    sprintf(timestamp, "%04d-%02d-%02dT%02d:%02d:%02d", 
            now.year(), now.month(), now.day(), 
            now.hour(), now.minute(), now.second());
    return String(timestamp);
}

int RTCManager::getCurrentHour() {
    return _rtc.now().hour();
}

void RTCManager::setNextAlarm() {
    DateTime now = _rtc.now();
    uint32_t currentUnix = now.unixtime();
    uint32_t remainder = currentUnix % WAKEUP_INTERVAL_SECONDS;
    uint32_t nextAlarmUnix = currentUnix - remainder + WAKEUP_INTERVAL_SECONDS;
    DateTime future(nextAlarmUnix);
    
    if (!_rtc.setAlarm1(future, DS3231_A1_Hour)) {
        Serial.println("Error setting alarm!");
    } else {
        Serial.printf("Next reading scheduled for: %02d:%02d:%02d\n", 
                      future.hour(), future.minute(), future.second());
    }
}

void RTCManager::syncNTP() {
    Serial.println("Synchronizing DS3231 RTC with NTP...");
    configTime(0, 0, "pool.ntp.org");
    
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 5000)) { // 5-second timeout
        Serial.println("NTP Time acquired!");
        
        // Convert NTP time to Unix timestamp
        time_t ntpUnix = mktime(&timeinfo);
        uint32_t rtcUnix = _rtc.now().unixtime();
        
        // Only update if drift is greater than 2 seconds
        if (abs((long)(ntpUnix - rtcUnix)) > 2) {
            Serial.println("Drift detected! Updating RTC...");
            _rtc.adjust(DateTime(timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday, 
                                timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec));
        } else {
            Serial.println("RTC time is accurate. No update needed.");
        }
    } else {
        Serial.println("Failed to obtain time from NTP server.");
    }
}
