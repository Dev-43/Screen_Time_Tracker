#pragma once
#if defined(__linux__) || defined(__unix__)

#include "ProcessMonitor.hpp"
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <X11/extensions/scrnsaver.h>
#include <fstream>
#include <sstream>
#include <string>
#include <ctime>

// ─────────────────────────────────────────────────────────────────────────────
// LinuxMonitor — implements ProcessMonitor using X11 + /proc
// Same structural pattern as reference project's LinuxMonitor
// ─────────────────────────────────────────────────────────────────────────────
class LinuxMonitor : public ProcessMonitor {
public:
    explicit LinuxMonitor(int idleThresholdSec = 60)
        : idleThreshold_(idleThresholdSec) {}

    ScreenLog sampleOnce() override {
        ScreenLog log{};
        log.timestamp = static_cast<uint64_t>(std::time(nullptr));

        Display* dpy = XOpenDisplay(nullptr);
        if (!dpy) {
            log.app_name = "Unknown";
            log.active_window = "(X11 unavailable)";
            return log;
        }

        // ── Active window ────────────────────────────────────────────────
        Window activeWin = getActiveWindow(dpy);
        if (activeWin != None) {
            log.active_window = getWindowTitle(dpy, activeWin);
            unsigned long pid = getWindowPid(dpy, activeWin);
            log.pid = (int)pid;
            if (pid > 0) {
                log.app_name = readProcComm(pid);
                log.ram_kb   = readProcRamKB(pid);
            }
        }

        if (log.app_name.empty())   log.app_name = "Unknown";
        if (log.active_window.empty()) log.active_window = "(no title)";

        // ── Idle detection via XScreenSaver extension ────────────────────
        XScreenSaverInfo* info = XScreenSaverAllocInfo();
        if (info) {
            XScreenSaverQueryInfo(dpy, DefaultRootWindow(dpy), info);
            unsigned long idleSec = info->idle / 1000;
            log.is_idle = (idleSec >= (unsigned long)idleThreshold_) ? 1 : 0;
            XFree(info);
        }

        // ── System CPU from /proc/stat ───────────────────────────────────
        log.cpu_usage = readCpuPercent();

        XCloseDisplay(dpy);
        return log;
    }

private:
    int idleThreshold_;

    // Previous /proc/stat values for CPU delta
    unsigned long long prevIdle_  = 0;
    unsigned long long prevTotal_ = 0;

    // ── X11 helpers ──────────────────────────────────────────────────────
    static Window getActiveWindow(Display* dpy) {
        Atom prop = XInternAtom(dpy, "_NET_ACTIVE_WINDOW", True);
        if (prop == None) return None;
        Atom actualType; int fmt; unsigned long n, extra;
        unsigned char* data = nullptr;
        if (XGetWindowProperty(dpy, DefaultRootWindow(dpy), prop,
                               0, 1, False, XA_WINDOW,
                               &actualType, &fmt, &n, &extra, &data) != Success)
            return None;
        Window w = None;
        if (data) { w = *reinterpret_cast<Window*>(data); XFree(data); }
        return w;
    }

    static std::string getWindowTitle(Display* dpy, Window w) {
        Atom utf8  = XInternAtom(dpy, "UTF8_STRING", False);
        Atom nameA = XInternAtom(dpy, "_NET_WM_NAME", True);
        Atom actualType; int fmt; unsigned long n, extra;
        unsigned char* data = nullptr;
        if (nameA != None &&
            XGetWindowProperty(dpy, w, nameA, 0, 1024, False, utf8,
                               &actualType, &fmt, &n, &extra, &data) == Success
            && data) {
            std::string title(reinterpret_cast<char*>(data), n);
            XFree(data);
            return title;
        }
        char* name = nullptr;
        if (XFetchName(dpy, w, &name) && name) {
            std::string t(name); XFree(name); return t;
        }
        return "";
    }

    static unsigned long getWindowPid(Display* dpy, Window w) {
        Atom pidA = XInternAtom(dpy, "_NET_WM_PID", True);
        if (pidA == None) return 0;
        Atom actualType; int fmt; unsigned long n, extra;
        unsigned char* data = nullptr;
        if (XGetWindowProperty(dpy, w, pidA, 0, 1, False, XA_CARDINAL,
                               &actualType, &fmt, &n, &extra, &data) != Success)
            return 0;
        unsigned long pid = 0;
        if (data) { pid = *reinterpret_cast<unsigned long*>(data); XFree(data); }
        return pid;
    }

    // ── /proc helpers ─────────────────────────────────────────────────────
    static std::string readProcComm(unsigned long pid) {
        std::ifstream f("/proc/" + std::to_string(pid) + "/comm");
        std::string name;
        std::getline(f, name);
        return name;
    }

    static uint64_t readProcRamKB(unsigned long pid) {
        std::ifstream f("/proc/" + std::to_string(pid) + "/status");
        std::string line;
        while (std::getline(f, line)) {
            if (line.rfind("VmRSS:", 0) == 0) {
                unsigned long kb = 0;
                std::sscanf(line.c_str(), "VmRSS: %lu kB", &kb);
                return static_cast<uint64_t>(kb);
            }
        }
        return 0;
    }

    double readCpuPercent() {
        std::ifstream f("/proc/stat");
        std::string line;
        std::getline(f, line);  // first line = cpu total
        unsigned long long user, nice, sys, idle, iowait, irq, softirq, steal;
        std::sscanf(line.c_str(), "cpu  %llu %llu %llu %llu %llu %llu %llu %llu",
                    &user, &nice, &sys, &idle, &iowait, &irq, &softirq, &steal);

        unsigned long long totalIdle  = idle + iowait;
        unsigned long long totalAll   = user + nice + sys + idle + iowait + irq + softirq + steal;

        double cpu = 0.0;
        if (prevTotal_ > 0 && totalAll > prevTotal_) {
            unsigned long long dIdle  = totalIdle - prevIdle_;
            unsigned long long dTotal = totalAll  - prevTotal_;
            cpu = 100.0 * (1.0 - static_cast<double>(dIdle) / dTotal);
        }
        prevIdle_  = totalIdle;
        prevTotal_ = totalAll;
        return cpu;
    }
};

#endif // __linux__
