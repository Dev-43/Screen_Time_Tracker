#include <iostream>
#include <iomanip>
#include <string>
#include <ctime>
#include <csignal>

#ifdef __linux__
    #include <unistd.h>
#endif

#include "Shared.hpp"
#include "ProcessMonitor.hpp"
#include "Database.hpp"

#ifdef _WIN32
    #include "ProcessMonitor_Win.hpp"
#elif defined(__linux__)
    #include "ProcessMonitor_Lin.hpp"
#else
    #error "Unsupported Operating System"
#endif

// ─────────────────────────────────────────────────────────────────────────────
// Resolve DB path — same pattern as reference project
// Priority: --db CLI arg → platform default → fallback
// ─────────────────────────────────────────────────────────────────────────────
static std::string resolveDbPath(int argc, char* argv[]) {
    for (int i = 1; i < argc - 1; i++) {
        if (std::string(argv[i]) == "--db")
            return argv[i + 1];
    }

#ifdef _WIN32
    const char* appdata = getenv("LOCALAPPDATA");
    if (appdata) return std::string(appdata) + "\\ScreenTracker\\logs.db";
    const char* pd = getenv("PROGRAMDATA");
    if (pd) return std::string(pd) + "\\ScreenTracker\\logs.db";
#elif defined(__linux__)
    const char* home = getenv("HOME");
    if (home) return std::string(home) + "/.local/share/screen_tracker/logs.db";
#endif

    return "logs.db";
}

// ─────────────────────────────────────────────────────────────────────────────
// Idle threshold — seconds of no input before marking as idle
// Override: --idle <seconds>   (default: 60)
// ─────────────────────────────────────────────────────────────────────────────
static int resolveIdleThreshold(int argc, char* argv[]) {
    for (int i = 1; i < argc - 1; i++) {
        if (std::string(argv[i]) == "--idle")
            return std::stoi(argv[i + 1]);
    }
    return 60;
}

// ─────────────────────────────────────────────────────────────────────────────
// Poll interval — seconds between samples
// Override: --interval <seconds>   (default: 1)
// ─────────────────────────────────────────────────────────────────────────────
static int resolvePollInterval(int argc, char* argv[]) {
    for (int i = 1; i < argc - 1; i++) {
        if (std::string(argv[i]) == "--interval")
            return std::stoi(argv[i + 1]);
    }
    return 1;
}

// ─────────────────────────────────────────────────────────────────────────────
// Signal handler — clean shutdown on Ctrl+C / SIGTERM
// ─────────────────────────────────────────────────────────────────────────────
static volatile bool g_running = true;

void signal_handler(int) {
    std::cout << "\n[ScreenTracker] Shutdown signal received. Exiting cleanly.\n";
    g_running = false;
}

// ─────────────────────────────────────────────────────────────────────────────
// Print header (same style as reference project)
// ─────────────────────────────────────────────────────────────────────────────
void printHeader() {
    std::cout << std::left
              << std::setw(8)  << "PID"
              << std::setw(28) << "App Name"
              << std::setw(10) << "CPU%"
              << std::setw(12) << "RAM (KB)"
              << std::setw(8)  << "Idle"
              << "Window Title"
              << std::endl;
    std::cout << std::string(100, '-') << std::endl;
}

// ─────────────────────────────────────────────────────────────────────────────
// main
// ─────────────────────────────────────────────────────────────────────────────
int main(int argc, char* argv[]) {
    std::cout << "=== Screen Activity Tracker ===\n";

    std::string dbPath      = resolveDbPath(argc, argv);
    int         idleSec     = resolveIdleThreshold(argc, argv);
    int         intervalSec = resolvePollInterval(argc, argv);

    std::cout << "Database:       " << dbPath      << "\n";
    std::cout << "Idle threshold: " << idleSec     << "s\n";
    std::cout << "Poll interval:  " << intervalSec << "s\n\n";

    // ── OS-specific monitor ───────────────────────────────────────────────
    ProcessMonitor* monitor = nullptr;

#ifdef _WIN32
    std::cout << "Detected OS: Windows\n";
    monitor = new WindowsMonitor(idleSec);
#elif defined(__linux__)
    std::cout << "Detected OS: Linux\n";
    monitor = new LinuxMonitor(idleSec);
#endif

    if (!monitor) {
        std::cerr << "Failed to create monitor!\n";
        return 1;
    }

    // ── Database ──────────────────────────────────────────────────────────
    Database database(dbPath);

    // ── Signal handlers ───────────────────────────────────────────────────
    std::signal(SIGINT,  signal_handler);
    std::signal(SIGTERM, signal_handler);

    std::cout << "Logger running. Press Ctrl+C to stop.\n\n";

    long long sampleCount = 0;

    while (g_running) {
        ScreenLog log = monitor->sampleOnce();

        // Print every 10 samples to avoid flooding stdout
        if (sampleCount % 10 == 0) {
            if (sampleCount % 100 == 0) printHeader();
            std::cout << std::left
                      << std::setw(8)  << log.pid
                      << std::setw(28) << log.app_name.substr(0, 27)
                      << std::setw(10) << std::fixed << std::setprecision(1) << log.cpu_usage
                      << std::setw(12) << log.ram_kb
                      << std::setw(8)  << (log.is_idle ? "IDLE" : "active")
                      << log.active_window.substr(0, 50)
                      << "\n";
        }

        database.insertLog(log);
        ++sampleCount;

#ifdef _WIN32
        Sleep(intervalSec * 1000);
#else
        sleep(intervalSec);
#endif
    }

    delete monitor;
    std::cout << "[ScreenTracker] " << sampleCount << " samples written. Done.\n";
    return 0;
}
