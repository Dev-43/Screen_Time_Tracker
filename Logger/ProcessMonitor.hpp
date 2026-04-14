#pragma once
#include "Shared.hpp"

// ─────────────────────────────────────────────────────────────────────────────
// ProcessMonitor (abstract base — same pattern as reference project)
//
// Both Windows and Linux implementations derive from this.
// main.cpp calls sampleOnce() — it never knows which OS it's on.
// ─────────────────────────────────────────────────────────────────────────────
class ProcessMonitor {
public:
    virtual ~ProcessMonitor() = default;

    // Returns one ScreenLog for the current foreground window + system stats.
    // Returns a log with app_name="" if detection fails.
    virtual ScreenLog sampleOnce() = 0;
};
