# Screen Time Tracker

A cross-platform, highly efficient desktop screen time tracker. This project consists of a lightweight C++ background logger that captures your active application data and a sleek, dynamic Python GUI that visualizes your screen time, sets limits, and categorizes your usage.

---

## 📖 What is this Project?

Screen Time Tracker is designed to give you precise insights into how you spend your time on your computer. Unlike traditional trackers that just look at what programs are open, this tracker actively monitors the **foreground window** (the app you are actually interacting with) and pauses tracking if you walk away from your computer.

### The Architecture (How It Works)
The system is built on a decoupled architecture using a shared database:
1. **The Logger (C++)**: Runs invisibly in the background. It is written in C++ for maximum performance and minimal system overhead. It continuously monitors what you are doing.
2. **The Database (SQLite)**: The logger writes every second of activity into a local SQLite database (`logs.db`).
3. **The Frontend (Python/PyQt5)**: The user interface reads from this database to generate live charts, daily summaries, and weekly statistics. It also writes user preferences (like time limits and app categories) back to the database.

---

## 🔍 The Logger: What It Fetches and When

The C++ logger runs continuously in a loop. By default, it samples your system **every 1 second**. 

At every timestamp, it fetches the following information for the currently active foreground window:
* **Timestamp**: The exact UNIX time the sample was taken.
* **Process ID (PID)**: The OS identifier for the running application.
* **App Name**: The name of the executable (e.g., `chrome.exe`, `code.exe`).
* **Active Window**: The exact title of the window (e.g., "Screen_Time_Tracker - Visual Studio Code").
* **CPU Usage (%)**: How much of your processor the active app is currently using.
* **RAM (KB)**: How much memory the active app is consuming.

### 💤 The Idle State Case (Ideal State Tracking)
One of the most important features is the **Idle State detection**. 
* The logger constantly monitors your system for keyboard and mouse input. 
* If there is **no user input for 60 seconds** (this threshold is configurable via the `--idle` flag), the logger flags the current sample with `is_idle = 1`.
* **Why this matters**: If you leave a YouTube video paused and walk away to make lunch, the frontend will see `is_idle = 1` and **exclude** that time from your active screen time totals. Your data remains perfectly accurate to your actual active computer usage.

---

## 💻 The Frontend & Code Structure

The frontend is a modern, dark-themed desktop application built using Python, PyQt5, and PyQtGraph.

### Code Structure
```text
Screen_Time_Tracker/
├── Logger/                         ← C++ Background tracking engine
│   ├── main.cpp                    ← Entry point & polling loop
│   ├── ProcessMonitor_Win.hpp      ← Windows-specific tracking (WinAPI)
│   ├── install_windows.bat         ← Sets up the logger as a background task
│   └── ...
│
├── Frontend/                       ← Python GUI Application
│   ├── main.py                     ← Application entry point
│   ├── db_reader.py                ← Database interface (The connection layer)
│   ├── worker.py                   ← Background QThread for live UI updates
│   ├── requirements.txt            
│   └── ui/                         ← Visual components
│       ├── theme.py                ← Global styling, colors, and Qt stylesheets
│       ├── main_window.py          ← Core window frame and tab routing
│       ├── tab_dashboard.py        ← The main view (Live charts & daily totals)
│       ├── tab_detail.py           ← Deep dive into specific apps & time limits
│       └── warning_popup.py        ← Animated alert when time limits are exceeded
│
└── Demo_Bundle/                    ← Packaged bundle for easy demonstration
    ├── ScreenTrackerFrontend.exe   
    ├── logger.exe
    ├── start_demo.bat              ← One-click script to run everything
    └── stop_demo.bat
```

### The Data Flow & Connection
1. **The Database Connection**: `Frontend/db_reader.py` is the single point of truth for the GUI. It connects to the SQLite database created by the logger.
2. **The Worker Thread**: Because database queries can freeze a UI, `Frontend/worker.py` runs a background thread that polls `db_reader.py` every second and emits PyQt signals with fresh data.
3. **The UI Update**: The UI components (`tab_dashboard.py` and `tab_detail.py`) listen to these signals and seamlessly animate the charts and update the text without any lag.

### Key Frontend Features
* **Categorization**: Users can assign apps to categories (Productivity, Entertainment, System, etc.). The frontend automatically groups daily summaries based on these categories.
* **Time Limits**: You can set daily minute limits for distracting apps. If the limit is crossed, a glowing `warning_popup.py` appears on screen.
* **Live Telemetry**: Real-time Task Manager-style charts showing the CPU and RAM usage of the current foreground app.

---

## 🚀 How to Run the Demo

If you just want to run the project and see it in action without installing Python or C++ compilers:

1. Open the `Demo_Bundle` folder.
2. Double-click **`start_demo.bat`**.
3. This will launch the C++ logger silently in a minimized window and immediately open the Python GUI.
4. When you are finished, double-click **`stop_demo.bat`** to safely close all background tracking processes.

*Note: The demo automatically saves your database locally so your screen time is preserved across restarts.*
