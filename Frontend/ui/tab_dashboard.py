"""
Screen Tracker — Dashboard Tab
================================
Tab 1: Live metric cards (Screen Time, CPU, RAM) + App list table.
MetricCard is identical to BehaviorShield's MetricCard — Task Manager style
scrolling filled area chart.
"""

from __future__ import annotations
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QSplitter, QSizePolicy,
    QAbstractItemView,
)

from ui.theme import (
    BG_PANEL, BG_BASE, BORDER, ACCENT, SAFE, WARN, DANGER,
    TEXT, TEXT_DIM, FONT_DATA, FONT_UI,
    CHART_CPU, CHART_RAM, CHART_TIME, CHART_BG,
    app_color,
)

import pyqtgraph as pg
pg.setConfigOption("background", CHART_BG)
pg.setConfigOption("foreground", TEXT_DIM)
pg.setConfigOption("antialias", True)


def fmt_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h} hrs, {m} mins"
    return f"{m} mins"

def short_name(app: str) -> str:
    return app.replace(".exe", "").replace(".app", "")


# ── MetricCard — identical to BehaviorShield ─────────────────────────────────

class MetricCard(QFrame):
    """
    Task-Manager style live chart card.
    Scrolling filled area chart + current value overlay.
    Pixel-for-pixel match to BehaviorShield's MetricCard.
    """
    MAX_POINTS = 120

    def __init__(self, title: str, unit: str, color: str,
                 y_max: float = 100.0, parent=None):
        super().__init__(parent)
        self.title  = title
        self.unit   = unit
        self.color  = color
        self.y_max  = y_max
        self._data: list[float] = [0.0] * self.MAX_POINTS
        self._build()

    def _build(self):
        self.setMinimumHeight(160)
        self.setMinimumWidth(180)
        self.setStyleSheet(f"""
            MetricCard {{
                background: {BG_PANEL};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Title row
        title_row = QHBoxLayout()
        self._title_lbl = QLabel(self.title.upper())
        self._title_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:8pt; letter-spacing:2px;"
        )
        title_row.addWidget(self._title_lbl)
        title_row.addStretch()
        self._peak_lbl = QLabel("peak: —")
        self._peak_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_DATA}; font-size:8pt;"
        )
        title_row.addWidget(self._peak_lbl)
        layout.addLayout(title_row)

        # Value
        self._value_lbl = QLabel("—")
        self._value_lbl.setStyleSheet(
            f"color:{self.color}; font-family:{FONT_DATA}; font-size:18pt; font-weight:bold;"
        )
        layout.addWidget(self._value_lbl)

        # Chart
        self._plot = pg.PlotWidget()
        self._plot.setMinimumHeight(80)
        self._plot.setMaximumHeight(110)
        self._plot.showAxis("left",   False)
        self._plot.showAxis("bottom", False)
        self._plot.setMouseEnabled(False, False)
        self._plot.setMenuEnabled(False)
        self._plot.setYRange(0, self.y_max, padding=0.05)
        self._plot.getViewBox().setBackgroundColor(CHART_BG)
        self._plot.showGrid(x=False, y=True, alpha=0.15)

        pen   = pg.mkPen(color=self.color, width=1.5)
        brush = pg.mkBrush(color=self.color + "40")
        self._curve = self._plot.plot(
            list(range(self.MAX_POINTS)),
            self._data,
            pen=pen,
            fillLevel=0,
            brush=brush,
        )
        layout.addWidget(self._plot)

    def push(self, value: float):
        self._data.append(value)
        if len(self._data) > self.MAX_POINTS:
            self._data.pop(0)
        self._curve.setData(list(range(len(self._data))), self._data)
        self._value_lbl.setText(f"{value:.1f}{self.unit}")
        peak = max(self._data)
        self._peak_lbl.setText(f"peak: {peak:.1f}{self.unit}")

    def set_text_value(self, text: str):
        """For screen time card — show formatted time string."""
        self._value_lbl.setText(text)

    def push_binary(self, active: bool):
        """Push 1 (active) or 0 (idle) for the screen time bar chart."""
        self.push(self.y_max if active else 0.0)


# ── App List Table ────────────────────────────────────────────────────────────

class AppTable(QWidget):
    """
    App usage table matching BehaviorShield's ProcessTable style.
    Columns: App Name | Today's Usage | Time Limit | Status
    Row click → emits row_selected(app_name, seconds)
    """
    row_selected = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apps: list[tuple[str, int]] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QFrame()
        header.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(12, 8, 12, 8)

        title = QLabel("APP USAGE — TODAY")
        title.setStyleSheet(
            f"color:{ACCENT}; font-family:{FONT_UI}; font-size:9pt; font-weight:bold; letter-spacing:2px;"
        )
        h_lay.addWidget(title)
        h_lay.addStretch()

        self._count_lbl = QLabel("0 apps")
        self._count_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_DATA}; font-size:8pt;"
        )
        h_lay.addWidget(self._count_lbl)
        layout.addWidget(header)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["APP NAME", "TODAY'S USAGE", "TIME LIMIT", "STATUS"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setShowGrid(False)
        self._table.cellClicked.connect(self._on_click)
        layout.addWidget(self._table)

    def update_apps(self, apps: list[tuple[str, int]], limits: dict):
        self._apps = apps
        self._count_lbl.setText(f"{len(apps)} apps")
        self._table.setRowCount(len(apps))

        for row, (app_name, seconds) in enumerate(apps):
            self._table.setRowHeight(row, 32)

            # App name (colored like BehaviorShield process name column)
            name_item = QTableWidgetItem(f"  {short_name(app_name)}")
            name_item.setForeground(QBrush(QColor(app_color(row))))
            self._table.setItem(row, 0, name_item)

            # Usage
            usage_item = QTableWidgetItem(fmt_time(seconds))
            usage_item.setForeground(QBrush(QColor(TEXT)))
            usage_item.setFont(QFont(FONT_DATA, 9))
            self._table.setItem(row, 1, usage_item)

            # Time limit
            limit = limits.get(app_name)
            if limit:
                limit_item = QTableWidgetItem(f"{limit} min/day")
                limit_item.setForeground(QBrush(QColor(WARN)))
            else:
                limit_item = QTableWidgetItem("—  Set limit")
                limit_item.setForeground(QBrush(QColor(TEXT_DIM)))
            self._table.setItem(row, 2, limit_item)

            # Status — check if limit exceeded
            if limit and (seconds // 60) >= limit:
                status_item = QTableWidgetItem("  ⚠ LIMIT HIT")
                status_item.setForeground(QBrush(QColor(DANGER)))
            else:
                status_item = QTableWidgetItem("  ✓ OK")
                status_item.setForeground(QBrush(QColor(SAFE)))
            self._table.setItem(row, 3, status_item)

    def _on_click(self, row: int, _col: int):
        if row < len(self._apps):
            app_name, seconds = self._apps[row]
            self.row_selected.emit(app_name, seconds)


# ── Dashboard Tab ─────────────────────────────────────────────────────────────

class DashboardTab(QWidget):
    """
    Main dashboard — 3 metric cards + app usage table.
    Same layout as BehaviorShield's DashboardTab.
    """
    app_selected = pyqtSignal(str, int)   # app_name, seconds

    def __init__(self, db_reader, parent=None):
        super().__init__(parent)
        self.db = db_reader
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Metric Cards Row ─────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        # Screen Time card — shows today's total + live active/idle bar
        self.card_time = MetricCard(
            "Screen Time", "", CHART_TIME, y_max=1.0
        )
        self.card_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # CPU card
        self.card_cpu = MetricCard("CPU", "%", CHART_CPU, y_max=100.0)
        self.card_cpu.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # RAM card
        self.card_ram = MetricCard("RAM", " MB", CHART_RAM, y_max=32768.0)
        self.card_ram.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        cards_row.addWidget(self.card_time)
        cards_row.addWidget(self.card_cpu)
        cards_row.addWidget(self.card_ram)
        root.addLayout(cards_row)

        # ── App Table ────────────────────────────────────────────────────
        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:6px;"
        )
        t_layout = QVBoxLayout(table_frame)
        t_layout.setContentsMargins(0, 0, 0, 0)

        self.app_table = AppTable()
        self.app_table.row_selected.connect(self.app_selected.emit)
        t_layout.addWidget(self.app_table)

        root.addWidget(table_frame, stretch=1)

        # ── Schema banner (shown if DB not found) ────────────────────────
        self._banner = QLabel()
        self._banner.setStyleSheet(f"""
            background:{WARN_BG if hasattr(self, '_warn_shown') else '#1f1500'};
            color:{WARN}; border:1px solid {WARN};
            border-radius:4px; padding:6px 12px;
            font-family:{FONT_UI}; font-size:9pt;
        """)
        self._banner.setVisible(False)
        root.addWidget(self._banner)

        if not self.db.columns:
            self._banner.setText(
                "⚠  Logger not running or database not found. "
                f"Expected: {self.db.db_path}"
            )
            self._banner.setVisible(True)

    # ── Public API ────────────────────────────────────────────────────────

    def refresh(self):
        """Full data refresh — call every 30s."""
        apps  = self.db.get_today_apps()
        limits = self.db.get_all_time_limits()
        active_sec, idle_sec = self.db.get_today_totals()

        self.card_time.set_text_value(fmt_time(active_sec))
        self.app_table.update_apps(apps, limits)

    def push_live(self, cpu: float, ram_mb: float, is_active: bool):
        """Called every second by the worker timer."""
        self.card_cpu.push(cpu)
        self.card_ram.push(ram_mb)
        self.card_time.push_binary(is_active)

        # Update screen time value every push
        active_sec, _ = self.db.get_today_totals()
        self.card_time.set_text_value(fmt_time(active_sec))

    def check_limits(self) -> list[tuple[str, int, int]]:
        """
        Returns list of (app_name, used_min, limit_min) for apps that
        have exceeded their daily time limit.
        """
        apps   = self.db.get_today_apps()
        limits = self.db.get_all_time_limits()
        exceeded = []
        for app_name, seconds in apps:
            limit = limits.get(app_name)
            if limit and (seconds // 60) >= limit:
                exceeded.append((app_name, seconds // 60, limit))
        return exceeded
