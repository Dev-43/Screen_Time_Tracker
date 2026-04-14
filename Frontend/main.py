"""
Screen Tracker — Entry Point
==============================
Usage:
    python main.py
    python main.py --db /path/to/logs.db

Same structure as BehaviorShield's main.py.
"""

import sys
import os
import argparse

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from db_reader import get_default_db_path
from ui.main_window import MainWindow
from ui.theme import STYLESHEET


def parse_args():
    p = argparse.ArgumentParser(description="Screen Tracker — Desktop Activity Monitor")
    p.add_argument("--db", default=None, help="Path to the SQLite database written by the C++ logger")
    return p.parse_args()


def main():
    args = parse_args()

    db_path = args.db if args.db else get_default_db_path()
    print(f"[ScreenTracker] Using database: {db_path}")

    app = QApplication(sys.argv)
    app.setApplicationName("Screen Tracker")
    app.setOrganizationName("ScreenTracker")

    # High DPI
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Apply theme stylesheet globally — same as BehaviorShield
    app.setStyleSheet(STYLESHEET)

    window = MainWindow(db_path=db_path)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
