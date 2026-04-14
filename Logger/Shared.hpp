#pragma once
#include <string>
#include <stdint.h>

// ─────────────────────────────────────────────────────────────────────────────
// ScreenLog
//
// One row written to the SQLite database per sample cycle.
// Matches the reference logger's ProcessLog but extended for screen tracking:
//   - active_window  : title bar text of the foreground window
//   - app_name       : process name (chrome.exe / chrome)
//   - is_idle        : 1 if no keyboard/mouse input >= idle_threshold_sec
//   - cpu_usage      : system CPU % at time of sample
//   - ram_kb         : RAM used by foreground process (KB)
//   - timestamp      : Unix epoch seconds
// ─────────────────────────────────────────────────────────────────────────────
struct ScreenLog {
    int         pid;
    std::string app_name;       // foreground process name
    std::string active_window;  // window title bar text
    int         is_idle;        // 0 = active, 1 = idle
    double      cpu_usage;      // system CPU %
    uint64_t    ram_kb;         // foreground process RAM in KB
    uint64_t    timestamp;      // Unix epoch
};
