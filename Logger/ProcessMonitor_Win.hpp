#pragma once
#ifdef _WIN32

#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif

#include "ProcessMonitor.hpp"
#include <windows.h>
#include <psapi.h>
#include <pdh.h>
#include <chrono>
#include <string>
#include <map>
#pragma comment(lib, "pdh.lib")
#pragma comment(lib, "psapi.lib")

// ─────────────────────────────────────────────────────────────────────────────
// CpuSampler — PDH-based system CPU % (matches reference NetByteTracker style)
// ─────────────────────────────────────────────────────────────────────────────
class CpuSampler {
public:
    CpuSampler() : query_(nullptr), counter_(nullptr), ready_(false) { init(); }
    ~CpuSampler() { if (query_) PdhCloseQuery(query_); }

    double sample() {
        if (!ready_) return 0.0;
        PdhCollectQueryData(query_);
        PDH_FMT_COUNTERVALUE val;
        if (PdhGetFormattedCounterValue(counter_, PDH_FMT_DOUBLE, nullptr, &val) == ERROR_SUCCESS)
            return val.doubleValue;
        return 0.0;
    }

private:
    PDH_HQUERY   query_;
    PDH_HCOUNTER counter_;
    bool         ready_;

    void init() {
        if (PdhOpenQuery(nullptr, 0, &query_) != ERROR_SUCCESS) return;
        if (PdhAddCounter(query_, L"\\Processor(_Total)\\% Processor Time",
                          0, &counter_) != ERROR_SUCCESS) return;
        PdhCollectQueryData(query_);  // baseline
        ready_ = true;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// IdleChecker — wraps GetLastInputInfo
// ─────────────────────────────────────────────────────────────────────────────
class IdleChecker {
public:
    // Returns seconds since last keyboard/mouse input.
    static unsigned long idleSecs() {
        LASTINPUTINFO lii;
        lii.cbSize = sizeof(LASTINPUTINFO);
        if (!GetLastInputInfo(&lii)) return 0;
        DWORD now = GetTickCount();
        return (now >= lii.dwTime) ? (now - lii.dwTime) / 1000 : 0;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
// WindowsMonitor — implements ProcessMonitor
// ─────────────────────────────────────────────────────────────────────────────
class WindowsMonitor : public ProcessMonitor {
public:
    explicit WindowsMonitor(int idleThresholdSec = 60)
        : idleThreshold_(idleThresholdSec) {}

    ScreenLog sampleOnce() override {
        ScreenLog log{};
        log.timestamp = static_cast<uint64_t>(std::time(nullptr));

        // ── Foreground window ───────────────────────────────────────────
        HWND hwnd = GetForegroundWindow();
        if (hwnd) {
            // Window title
            wchar_t title[512] = {};
            if (GetWindowTextW(hwnd, title, 512)) {
                char buf[1024] = {};
                WideCharToMultiByte(CP_UTF8, 0, title, -1, buf, sizeof(buf), nullptr, nullptr);
                log.active_window = buf;
            }

            // Process name + RAM
            DWORD pid = 0;
            GetWindowThreadProcessId(hwnd, &pid);
            log.pid = pid;

            HANDLE hProc = OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
            if (!hProc)
                hProc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);

            if (hProc) {
                // Process name
                wchar_t exePath[MAX_PATH] = {};
                DWORD sz = MAX_PATH;
                if (QueryFullProcessImageNameW(hProc, 0, exePath, &sz)) {
                    // Extract filename only
                    std::wstring full(exePath, sz);
                    auto pos = full.find_last_of(L"\\/");
                    std::wstring fname = (pos != std::wstring::npos) ? full.substr(pos + 1) : full;
                    char buf[512] = {};
                    WideCharToMultiByte(CP_UTF8, 0, fname.c_str(), -1, buf, sizeof(buf), nullptr, nullptr);
                    log.app_name = buf;
                }

                // RAM
                PROCESS_MEMORY_COUNTERS pmc;
                if (GetProcessMemoryInfo(hProc, &pmc, sizeof(pmc)))
                    log.ram_kb = pmc.WorkingSetSize / 1024;

                CloseHandle(hProc);
            }
        }

        if (log.app_name.empty()) log.app_name = "Unknown";
        if (log.active_window.empty()) log.active_window = "(no title)";

        // ── Idle detection ───────────────────────────────────────────────
        log.is_idle = (IdleChecker::idleSecs() >= (unsigned long)idleThreshold_) ? 1 : 0;

        // ── System CPU % ─────────────────────────────────────────────────
        log.cpu_usage = cpuSampler_.sample();

        return log;
    }

private:
    int        idleThreshold_;
    CpuSampler cpuSampler_;
};

#endif // _WIN32
