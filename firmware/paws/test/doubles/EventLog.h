/*
 * Project: Personal Autonomous Weather Station
 * File: test/doubles/EventLog.h
 *
 * Description:
 * A list of events shared by several test doubles, to check the order of
 * calls across interfaces (for example: stored before connecting, F2).
 *
 * Dependencies: none (standard C++ only).
 */

#pragma once

#include <string>
#include <vector>

/**
 * @brief Events recorded by several test doubles, in call order.
 */
struct EventLog {
    std::vector<std::string> events;  ///< The events, oldest first

    /**
     * @brief Records an event.
     *
     * @param[in] event Its name, for example "connect".
     */
    void add(const std::string& event) { events.push_back(event); }

    /**
     * @brief Position of the first occurrence of an event.
     *
     * @param[in] event The name of the event.
     * @return Its position, or -1 if it was never recorded.
     */
    int indexOf(const std::string& event) const {
        for (size_t i = 0; i < events.size(); ++i) {
            if (events[i] == event) {
                return static_cast<int>(i);
            }
        }
        return -1;
    }

    /**
     * @brief Number of occurrences of an event.
     *
     * @param[in] event The name of the event.
     * @return How many times it was recorded.
     */
    int count(const std::string& event) const {
        int n = 0;
        for (const std::string& e : events) {
            if (e == event) {
                ++n;
            }
        }
        return n;
    }
};
