# Screen Tracker — Desktop Activity Monitor

Cross-platform desktop screen time tracker.
C++ logger writes process data to SQLite. Python GUI reads and displays it.

---

## Project Structure

```
screen_tracker/
├── logger/                         ← C++ Logger (Increment 1)
│   ├── main.cpp                 ← Entry point — same as reference logger
│   ├── Shared.hpp               ← ScreenLog struct
│   ├── ProcessMonitor.hpp       ← Abstract base class
│   ├── ProcessMonitor_Win.hpp   ← Windows: WinAPI + PDH
│   ├── ProcessMonitor_Lin.hpp   ← Linux: X11 + /proc
│   ├── Database.hpp             ← SQLite writer with WAL mode
│   ├── sqlite3.h                ← Place here (download from sqlite.org)
│   └── sqlite3.c                ← Place here (download from sqlite.org)
│
├── python/                      ← Python GUI (Increment 3)
│   ├── main.py                  ← Entry point
│   ├── requirements.txt
│   ├── core/
│   │   ├── db_reader.py         ← Database reader
│   │   └── worker.py            ← Background poll thread
│   └── ui/
│       ├── theme.py             ← All colors + stylesheet (BehaviorShield theme)
│       ├── main_window.py       ← Main window + tabs + tray
│       ├── tab_dashboard.py     ← MetricCard (Task Manager style) + App table
│       ├── tab_detail.py        ← App detail + hourly chart + time limit
│       └── warning_popup.py     ← Time limit notification popup
│
├── install_windows.bat
├── install_linux.sh
└── README.md
```

---

## Database Schema

Both the C++ logger and Python GUI read/write the same SQLite file:

```sql
-- Written by C++ logger every second
screen_logs (
    id, pid, app_name, active_window,
    is_idle, cpu_usage, ram_kb, timestamp
)

-- Written by Python GUI (time limits, categories)
time_limits   (app_name, daily_limit_min)
app_categories(app_name, category)
```

---

## Windows Setup

### Step 1 — Get SQLite amalgamation
Download from https://www.sqlite.org/download.html  
Extract `sqlite3.h` and `sqlite3.c` into the `cpp/` folder.

### Step 2 — Build and run
```batch
install_windows.bat
```

### Step 3 — Run logger (terminal 1)
```batch
dist\screen_tracker.exe
```

### Step 4 — Run GUI (terminal 2)
```batch
cd python
python main.py
```

---

## Linux Setup

```bash
chmod +x install_linux.sh
./install_linux.sh

# Terminal 1 — logger
./dist/screen_tracker

# Terminal 2 — GUI
cd python && python3 main.py
```

---

## CLI Options (Logger)

```
screen_tracker [--db <path>] [--idle <seconds>] [--interval <seconds>]

--db        Path to SQLite database (default: platform AppData/local path)
--idle      Seconds of no input before marking as idle (default: 60)
--interval  Seconds between samples (default: 1)
```

---

## UI Theme

Same dark theme as reference BehaviorShield project:
- Background: `#0a0e14`
- Panels: `#111827`
- Accent: `#00d4ff` (cyan)
- Charts: Task Manager style scrolling filled area (pyqtgraph)
- Fonts: Consolas (data) + Segoe UI (UI) on Windows
