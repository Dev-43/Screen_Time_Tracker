"""
Screen Tracker - Poll Worker
Background thread that polls system + DB state.
"""

from __future__ import annotations

from pathlib import Path

import psutil
from PyQt5.QtCore import QThread, pyqtSignal


class PollWorker(QThread):
    """
    Polls DB and system metrics.

    Signals:
        live_tick(cpu_pct, ram_mb, is_active)
        full_refresh()
        limit_check()
        row_count_ready(int)
        status_changed(message, level)
    """

    live_tick = pyqtSignal(float, float, bool)
    full_refresh = pyqtSignal()
    limit_check = pyqtSignal()
    row_count_ready = pyqtSignal(int)
    status_changed = pyqtSignal(str, str)

    def __init__(self, db_reader, parent=None):
        super().__init__(parent)
        self.db = db_reader
        self._running = False
        self._tick = 0
        self._last_row_count = 0

    def run(self):
        self._running = True
        self.status_changed.emit("Connecting to database...", "info")

        while self._running:
            self._tick += 1
            self._do_tick()
            self.msleep(1000)

    def stop(self):
        self._running = False

    def _do_tick(self):
        cpu = psutil.cpu_percent(interval=None)
        ram_mb = psutil.virtual_memory().used / 1024 / 1024

        row = self.db.get_latest_row()
        is_active = True
        if row:
            try:
                is_active = row["is_idle"] == 0
            except (IndexError, KeyError, TypeError):
                is_active = True

        self.live_tick.emit(cpu, ram_mb, is_active)

        if self._tick % 30 == 0:
            self.full_refresh.emit()

        if self._tick % 60 == 0:
            self.limit_check.emit()

        if self._tick % 10 == 0:
            count = self.db.get_row_count()
            self.row_count_ready.emit(count)
            self._emit_db_status(count)
            self._last_row_count = count

    def _emit_db_status(self, count: int):
        db_exists = Path(self.db.db_path).exists()
        if not db_exists:
            self.status_changed.emit(
                f"Waiting for logger - DB not found: {self.db.db_path}",
                "warn",
            )
            return

        if not self.db.is_logger_schema_ready():
            self.status_changed.emit(
                "Database found, but logger table is missing (screen_logs)",
                "warn",
            )
            return

        if count <= 0:
            self.status_changed.emit(
                "Connected to database - waiting for first logger rows",
                "warn",
            )
            return

        if count > self._last_row_count:
            self.status_changed.emit(f"Logger active - {count:,} rows logged", "info")
        else:
            self.status_changed.emit(
                f"Database reachable, but no new rows in the last check ({count:,})",
                "warn",
            )
