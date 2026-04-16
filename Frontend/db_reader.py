"""
Screen Tracker — DB Reader
===========================
Reads from the SQLite database written by the C++ logger.
Same pattern as BehaviorShield's DBReader.

# ── CHANGES ──────────────────────────────────────────────────────────────────
# [CHANGED] Added get_weekly_screen_time() — Mon-Sun totals across all apps
# [CHANGED] Added get_app_weekly_screen_time(app_name) — Mon-Sun totals per app
# [UNCHANGED] All other methods preserved exactly as-is
"""

from __future__ import annotations
import sqlite3
import os
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional


# [UNCHANGED]
def get_default_db_path() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", ".")
        return os.path.join(base, "ScreenTracker", "logs.db")
    else:
        home = os.environ.get("HOME", ".")
        return os.path.join(home, ".local", "share", "screen_tracker", "logs.db")


class DBReader:
    # [UNCHANGED]
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._check_schema()

    # [UNCHANGED]
    def _connect(self) -> Optional[sqlite3.Connection]:
        if not Path(self.db_path).exists():
            return None
        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            return None

    # [UNCHANGED]
    def _check_schema(self):
        """Check which columns exist — same pattern as BehaviorShield."""
        conn = self._connect()
        if not conn:
            self.columns = []
            return
        try:
            cur = conn.execute("PRAGMA table_info(screen_logs)")
            self.columns = [row["name"] for row in cur.fetchall()]
            conn.close()
        except Exception:
            self.columns = []
            conn.close()

    # [UNCHANGED]
    def is_logger_schema_ready(self) -> bool:
        return bool(self.columns)

    # ── Live data ─────────────────────────────────────────────────────────

    # [UNCHANGED]
    def get_recent_rows(self, limit: int = 60) -> list:
        """Last N rows from screen_logs — for live chart."""
        conn = self._connect()
        if not conn:
            return self._fake_recent(limit)
        try:
            cur = conn.execute(
                "SELECT * FROM screen_logs ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = list(reversed(cur.fetchall()))
            conn.close()
            return rows if rows else self._fake_recent(limit)
        except Exception:
            conn.close()
            return self._fake_recent(limit)

    # [UNCHANGED]
    def get_latest_row(self) -> Optional[object]:
        """Single most recent row."""
        conn = self._connect()
        if not conn:
            return None
        try:
            cur = conn.execute(
                "SELECT * FROM screen_logs ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            conn.close()
            return row
        except Exception:
            conn.close()
            return None

    # [UNCHANGED]
    def get_row_count(self) -> int:
        conn = self._connect()
        if not conn:
            return 0
        try:
            cur = conn.execute("SELECT COUNT(*) FROM screen_logs")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            conn.close()
            return 0

    # ── Today stats ───────────────────────────────────────────────────────

    # [UNCHANGED]
    def get_today_apps(self) -> List[Tuple[str, int]]:
        """Returns (app_name, active_seconds) for today, sorted desc."""
        conn = self._connect()
        today_ts_start = int(datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp())
        if not conn:
            return self._fake_apps()
        try:
            cur = conn.execute("""
                SELECT app_name, COUNT(*) as active_sec
                FROM screen_logs
                WHERE timestamp >= ? AND is_idle = 0
                GROUP BY app_name
                ORDER BY active_sec DESC
            """, (today_ts_start,))
            rows = cur.fetchall()
            conn.close()
            if rows:
                return [(r["app_name"], r["active_sec"]) for r in rows]
        except Exception:
            conn.close()
        return self._fake_apps()

    # [UNCHANGED]
    def get_today_totals(self) -> Tuple[int, int]:
        """Returns (active_seconds, idle_seconds) for today."""
        conn = self._connect()
        today_ts = int(datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp())
        if not conn:
            return (random.randint(3600, 28800), random.randint(1800, 7200))
        try:
            cur = conn.execute("""
                SELECT
                    SUM(CASE WHEN is_idle=0 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN is_idle=1 THEN 1 ELSE 0 END) as idle
                FROM screen_logs WHERE timestamp >= ?
            """, (today_ts,))
            row = cur.fetchone()
            conn.close()
            if row and row["active"] is not None:
                return (row["active"] or 0, row["idle"] or 0)
        except Exception:
            conn.close()
        return (0, 0)

    # ── Week data ─────────────────────────────────────────────────────────

    # [UNCHANGED]
    def get_week_daily_totals(self) -> List[Tuple[str, int]]:
        """(date_str, active_sec) for last 7 days."""
        result = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            result.append((d, 0))

        conn = self._connect()
        if not conn:
            return self._fake_week()
        try:
            start_ts = int((datetime.now() - timedelta(days=6)).replace(
                hour=0, minute=0, second=0).timestamp())
            cur = conn.execute("""
                SELECT
                    date(timestamp, 'unixepoch', 'localtime') as day,
                    SUM(CASE WHEN is_idle=0 THEN 1 ELSE 0 END) as active
                FROM screen_logs
                WHERE timestamp >= ? GROUP BY day ORDER BY day
            """, (start_ts,))
            rows = {r["day"]: r["active"] for r in cur.fetchall()}
            conn.close()
            result = [(d, rows.get(d, 0)) for d, _ in result]
            if any(v > 0 for _, v in result):
                return result
        except Exception:
            conn.close()
        return self._fake_week()

    # [CHANGED] Weekly totals across ALL apps grouped by Mon-Sun day of week
    def get_weekly_screen_time(self) -> dict:
        """
        Returns dict {day_label: minutes} for Mon-Sun of the current week
        (all apps combined). Falls back to zero-filled dict on DB error.
        """
        order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        result = {k: 0 for k in order}
        conn = self._connect()
        if not conn:
            # Fallback: fake demo data so the chart still renders
            return {k: random.randint(30, 480) for k in order}
        try:
            now = datetime.now()
            monday = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0)
            week_start_ts = int(monday.timestamp())
            week_end_ts = int((monday + timedelta(days=7)).timestamp())

            cur = conn.execute("""
                SELECT
                    strftime('%w', timestamp, 'unixepoch', 'localtime') AS dow,
                    COUNT(*) AS active_sec
                FROM screen_logs
                WHERE timestamp >= ? AND timestamp < ? AND is_idle = 0
                GROUP BY dow
            """, (week_start_ts, week_end_ts))
            rows = cur.fetchall()
            # SQLite strftime('%w'): 0=Sun,1=Mon,...,6=Sat
            idx_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu",
                       5: "Fri", 6: "Sat", 0: "Sun"}
            for row in rows:
                key = idx_map.get(int(row["dow"]))
                if key:
                    result[key] = int((row["active_sec"] or 0) / 60)
            conn.close()
            return result
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return result

    # [CHANGED] Per-app weekly totals grouped by Mon-Sun day of week
    def get_app_weekly_screen_time(self, app_name: str) -> dict:
        """
        Returns dict {day_label: minutes} for Mon-Sun of the current week
        for a specific app. Falls back to zero-filled dict on DB error.
        """
        order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        result = {k: 0 for k in order}
        conn = self._connect()
        if not conn:
            return {k: random.randint(0, 120) for k in order}
        try:
            now = datetime.now()
            monday = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0)
            week_start_ts = int(monday.timestamp())
            week_end_ts = int((monday + timedelta(days=7)).timestamp())

            cur = conn.execute("""
                SELECT
                    strftime('%w', timestamp, 'unixepoch', 'localtime') AS dow,
                    COUNT(*) AS active_sec
                FROM screen_logs
                WHERE timestamp >= ? AND timestamp < ?
                  AND app_name = ? AND is_idle = 0
                GROUP BY dow
            """, (week_start_ts, week_end_ts, app_name))
            rows = cur.fetchall()
            idx_map = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu",
                       5: "Fri", 6: "Sat", 0: "Sun"}
            for row in rows:
                key = idx_map.get(int(row["dow"]))
                if key:
                    result[key] = int((row["active_sec"] or 0) / 60)
            conn.close()
            return result
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return result

    # ── App detail ────────────────────────────────────────────────────────

    # [UNCHANGED]
    def get_app_hourly(self, app_name: str) -> List[Tuple[int, int]]:
        """Per-hour active seconds for app today."""
        conn = self._connect()
        today_ts = int(datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0).timestamp())
        if not conn:
            return self._fake_hourly()
        try:
            cur = conn.execute("""
                SELECT
                    CAST(strftime('%H', timestamp, 'unixepoch', 'localtime') AS INTEGER) as hr,
                    COUNT(*) as secs
                FROM screen_logs
                WHERE timestamp >= ? AND app_name=? AND is_idle=0
                GROUP BY hr ORDER BY hr
            """, (today_ts, app_name))
            rows = cur.fetchall()
            conn.close()
            hourly = {r["hr"]: r["secs"] for r in rows}
            return [(h, hourly.get(h, 0)) for h in range(24)]
        except Exception:
            conn.close()
        return self._fake_hourly()

    # ── Time limits ───────────────────────────────────────────────────────

    # [UNCHANGED]
    def get_time_limit(self, app_name: str) -> Optional[int]:
        conn = self._connect()
        if not conn:
            return None
        try:
            cur = conn.execute(
                "SELECT daily_limit_min FROM time_limits WHERE app_name=?",
                (app_name,)
            )
            row = cur.fetchone()
            conn.close()
            return row["daily_limit_min"] if row else None
        except Exception:
            conn.close()
            return None

    # [UNCHANGED]
    def set_time_limit(self, app_name: str, minutes: int):
        conn = self._connect()
        if not conn:
            return
        try:
            conn.execute("""
                INSERT INTO time_limits(app_name, daily_limit_min) VALUES(?,?)
                ON CONFLICT(app_name) DO UPDATE SET daily_limit_min=excluded.daily_limit_min
            """, (app_name, minutes))
            conn.commit()
            conn.close()
        except Exception:
            conn.close()

    # [UNCHANGED]
    def get_all_time_limits(self) -> dict:
        conn = self._connect()
        if not conn:
            return {}
        try:
            cur = conn.execute("SELECT app_name, daily_limit_min FROM time_limits")
            result = {r["app_name"]: r["daily_limit_min"] for r in cur.fetchall()}
            conn.close()
            return result
        except Exception:
            conn.close()
            return {}

    # ── CPU history (last N seconds from DB) ──────────────────────────────

    # [UNCHANGED]
    def get_cpu_history(self, limit: int = 120) -> List[float]:
        conn = self._connect()
        if not conn:
            return [random.uniform(5, 40) for _ in range(limit)]
        try:
            cur = conn.execute(
                "SELECT cpu_usage FROM screen_logs ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = list(reversed(cur.fetchall()))
            conn.close()
            vals = [r["cpu_usage"] for r in rows]
            if vals:
                return vals
        except Exception:
            conn.close()
        return [random.uniform(5, 40) for _ in range(limit)]

    # [UNCHANGED]
    def get_ram_history(self, limit: int = 120) -> List[float]:
        conn = self._connect()
        if not conn:
            return [random.uniform(200000, 800000) for _ in range(limit)]
        try:
            cur = conn.execute(
                "SELECT ram_kb FROM screen_logs ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = list(reversed(cur.fetchall()))
            conn.close()
            vals = [r["ram_kb"] / 1024 for r in rows]   # KB → MB
            if vals:
                return vals
        except Exception:
            conn.close()
        return [random.uniform(200, 800) for _ in range(limit)]

    # ── Fake data for demo ────────────────────────────────────────────────

    # [UNCHANGED]
    def _fake_apps(self):
        return [
            ("chrome.exe", 4320), ("code.exe", 3600), ("slack.exe", 1800),
            ("discord.exe", 900),  ("explorer.exe", 720), ("spotify.exe", 540),
        ]

    # [UNCHANGED]
    def _fake_week(self):
        result = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            result.append((d, random.randint(3600, 28800)))
        return result

    # [UNCHANGED]
    def _fake_hourly(self):
        return [(h, random.randint(0, 3600) if 9 <= h <= 18 else random.randint(0, 300))
                for h in range(24)]

    # [UNCHANGED]
    def _fake_recent(self, limit: int):
        return []
