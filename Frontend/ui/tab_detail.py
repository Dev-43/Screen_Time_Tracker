"""
Screen Tracker — App Detail Tab
=================================
Tab 2: Detailed view for a specific app.
Shows hourly bar chart + time limit controls.
Same panel/card style as BehaviorShield.
"""

from __future__ import annotations
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QSpinBox,
    QSizePolicy, QScrollArea,
)

from ui.theme import (
    BG_PANEL, BG_BASE, BG_INPUT, BORDER, BORDER_LIGHT,
    ACCENT, ACCENT_DIM, SAFE, SAFE_BG, WARN, WARN_BG, DANGER, DANGER_BG,
    TEXT, TEXT_DIM, FONT_DATA, FONT_UI,
    CHART_TIME, CHART_CPU, CHART_RAM, CHART_BG,
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


# ── Stat Cell ─────────────────────────────────────────────────────────────────

def make_stat(label: str, value: str, color: str = TEXT) -> QFrame:
    """Small labeled stat — same pattern as BehaviorShield detail fields."""
    frame = QFrame()
    frame.setStyleSheet(f"""
        QFrame {{
            background: {BG_INPUT};
            border: 1px solid {BORDER};
            border-radius: 4px;
        }}
    """)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(10, 8, 10, 8)
    lay.setSpacing(2)

    lbl = QLabel(label.upper())
    lbl.setStyleSheet(
        f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:8pt; "
        f"letter-spacing:1px; background:transparent; border:none;"
    )
    val = QLabel(value)
    val.setStyleSheet(
        f"color:{color}; font-family:{FONT_DATA}; font-size:12pt; "
        f"font-weight:bold; background:transparent; border:none;"
    )
    lay.addWidget(lbl)
    lay.addWidget(val)
    return frame


# ── App Detail Tab ────────────────────────────────────────────────────────────

class AppDetailTab(QWidget):
    """
    Detailed view for a selected app.
    Mirrors BehaviorShield's process detail panel layout.
    """
    go_back = pyqtSignal()
    limit_saved = pyqtSignal(str, int)   # app_name, minutes

    def __init__(self, db_reader, parent=None):
        super().__init__(parent)
        self.db       = db_reader
        self.app_name = ""
        self.seconds  = 0
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Top bar: back button + app name ─────────────────────────────
        top_bar = QFrame()
        top_bar.setStyleSheet(
            f"background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:6px;"
        )
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(12, 8, 12, 8)

        back_btn = QPushButton("← Back to Dashboard")
        back_btn.setFixedHeight(30)
        back_btn.clicked.connect(self.go_back.emit)
        top_lay.addWidget(back_btn)

        top_lay.addSpacing(16)

        self._app_title = QLabel("—")
        self._app_title.setStyleSheet(
            f"color:{ACCENT}; font-family:{FONT_UI}; font-size:13pt; "
            f"font-weight:bold; letter-spacing:1px; background:transparent; border:none;"
        )
        top_lay.addWidget(self._app_title)
        top_lay.addStretch()

        self._date_lbl = QLabel(datetime.now().strftime("%A, %d %b %Y"))
        self._date_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_DATA}; font-size:9pt; "
            f"background:transparent; border:none;"
        )
        top_lay.addWidget(self._date_lbl)
        root.addWidget(top_bar)

        # ── Stat cards row ───────────────────────────────────────────────
        self._stat_row = QHBoxLayout()
        self._stat_row.setSpacing(10)

        self._stat_total  = make_stat("Today's usage", "—", ACCENT)
        self._stat_limit  = make_stat("Time limit",    "—", WARN)
        self._stat_status = make_stat("Status",        "—", SAFE)
        self._stat_pct    = make_stat("Limit used",    "—", TEXT)

        for w in [self._stat_total, self._stat_limit, self._stat_status, self._stat_pct]:
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._stat_row.addWidget(w)

        root.addLayout(self._stat_row)

        # ── Charts row: hourly + metric cards ────────────────────────────
        charts_row = QHBoxLayout()
        charts_row.setSpacing(10)

        # Hourly bar chart (left, takes most space)
        hourly_frame = QFrame()
        hourly_frame.setStyleSheet(
            f"background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:6px;"
        )
        hourly_lay = QVBoxLayout(hourly_frame)
        hourly_lay.setContentsMargins(10, 8, 10, 8)
        hourly_lay.setSpacing(4)

        hourly_title = QLabel("HOURLY USAGE — TODAY")
        hourly_title.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:8pt; "
            f"letter-spacing:2px; background:transparent; border:none;"
        )
        hourly_lay.addWidget(hourly_title)

        self._hourly_plot = pg.PlotWidget()
        self._hourly_plot.setBackground(CHART_BG)
        self._hourly_plot.showGrid(x=False, y=True, alpha=0.15)
        self._hourly_plot.setMouseEnabled(False, False)
        self._hourly_plot.setMenuEnabled(False)
        self._hourly_plot.getAxis("bottom").setStyle(
            tickFont=QFont(FONT_DATA, 8)
        )
        self._hourly_plot.getAxis("left").setStyle(
            tickFont=QFont(FONT_DATA, 8)
        )
        self._hourly_plot.setMinimumHeight(160)
        hourly_lay.addWidget(self._hourly_plot)

        charts_row.addWidget(hourly_frame, 2)

        # Right column: CPU + RAM mini cards
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        from ui.tab_dashboard import MetricCard
        self.card_cpu = MetricCard("CPU", "%", CHART_CPU, y_max=100.0)
        self.card_cpu.setMaximumHeight(180)
        self.card_ram = MetricCard("RAM", " MB", CHART_RAM, y_max=32768.0)
        self.card_ram.setMaximumHeight(180)

        right_col.addWidget(self.card_cpu)
        right_col.addWidget(self.card_ram)
        charts_row.addLayout(right_col, 1)

        root.addLayout(charts_row, 1)

        # ── Time limit panel ─────────────────────────────────────────────
        limit_frame = QFrame()
        limit_frame.setStyleSheet(
            f"background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:6px;"
        )
        limit_lay = QHBoxLayout(limit_frame)
        limit_lay.setContentsMargins(16, 12, 16, 12)
        limit_lay.setSpacing(16)

        limit_title = QLabel("DAILY TIME LIMIT")
        limit_title.setStyleSheet(
            f"color:{ACCENT}; font-family:{FONT_UI}; font-size:9pt; "
            f"font-weight:bold; letter-spacing:2px; background:transparent; border:none;"
        )
        limit_lay.addWidget(limit_title)
        limit_lay.addStretch()

        lbl_set = QLabel("Set limit:")
        lbl_set.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:9pt; "
            f"background:transparent; border:none;"
        )
        limit_lay.addWidget(lbl_set)

        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(5, 480)
        self._limit_spin.setValue(60)
        self._limit_spin.setSuffix("  min / day")
        self._limit_spin.setFixedHeight(30)
        self._limit_spin.setFixedWidth(140)
        limit_lay.addWidget(self._limit_spin)

        save_btn = QPushButton("Save Limit")
        save_btn.setProperty("class", "accent")
        save_btn.setFixedHeight(30)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background:{ACCENT_DIM}; color:{BG_BASE};
                border:1px solid {ACCENT}; border-radius:4px;
                padding:0 16px; font-weight:bold;
                font-family:{FONT_UI}; font-size:{9}pt;
            }}
            QPushButton:hover {{ background:{ACCENT}; }}
        """)
        save_btn.clicked.connect(self._save_limit)
        limit_lay.addWidget(save_btn)

        clear_btn = QPushButton("Clear Limit")
        clear_btn.setFixedHeight(30)
        clear_btn.clicked.connect(self._clear_limit)
        limit_lay.addWidget(clear_btn)

        root.addWidget(limit_frame)

    # ── Load app data ─────────────────────────────────────────────────────

    def load(self, app_name: str, seconds: int):
        self.app_name = app_name
        self.seconds  = seconds

        self._app_title.setText(short_name(app_name).upper())
        self._date_lbl.setText(datetime.now().strftime("%A, %d %b %Y"))

        # Stat cards
        self._stat_total._find_val().setText(fmt_time(seconds))

        limit = self.db.get_time_limit(app_name)
        if limit:
            self._limit_spin.setValue(limit)
            self._stat_limit._find_val().setText(f"{limit} min/day")
            used_pct = min(100, int((seconds / 60) / limit * 100))
            self._stat_pct._find_val().setText(f"{used_pct}%")
            if (seconds // 60) >= limit:
                self._stat_status._find_val().setText("⚠ LIMIT HIT")
                self._stat_status._find_val().setStyleSheet(
                    f"color:{DANGER}; font-family:{FONT_DATA}; font-size:12pt; "
                    f"font-weight:bold; background:transparent; border:none;"
                )
            else:
                self._stat_status._find_val().setText("✓  OK")
                self._stat_status._find_val().setStyleSheet(
                    f"color:{SAFE}; font-family:{FONT_DATA}; font-size:12pt; "
                    f"font-weight:bold; background:transparent; border:none;"
                )
        else:
            self._stat_limit._find_val().setText("No limit")
            self._stat_pct._find_val().setText("—")
            self._stat_status._find_val().setText("✓  OK")

        # Hourly chart
        self._update_hourly()

    def _update_hourly(self):
        hourly = self.db.get_app_hourly(self.app_name)
        x = [h for h, _ in hourly]
        y = [s / 60 for _, s in hourly]   # minutes

        self._hourly_plot.clear()
        color = app_color(0)
        bars = pg.BarGraphItem(
            x=x, height=y, width=0.7,
            brush=pg.mkBrush(color + "CC"),
            pen=pg.mkPen(color, width=1),
        )
        self._hourly_plot.addItem(bars)

        labels = [(i, f"{i:02d}h") for i in range(0, 24, 3)]
        self._hourly_plot.getAxis("bottom").setTicks([labels])
        self._hourly_plot.setLabel("left", "minutes", color=TEXT_DIM,
                                   **{"font-size": "8pt"})

    # ── Live update ───────────────────────────────────────────────────────

    def push_live(self, cpu: float, ram_mb: float):
        self.card_cpu.push(cpu)
        self.card_ram.push(ram_mb)

    # ── Limit actions ─────────────────────────────────────────────────────

    def _save_limit(self):
        minutes = self._limit_spin.value()
        self.db.set_time_limit(self.app_name, minutes)
        self.limit_saved.emit(self.app_name, minutes)
        self._stat_limit._find_val().setText(f"{minutes} min/day")

    def _clear_limit(self):
        self.db.set_time_limit(self.app_name, 9999)
        self._stat_limit._find_val().setText("No limit")
        self._stat_pct._find_val().setText("—")


# ── Patch make_stat to expose val label ──────────────────────────────────────

def _find_val(self):
    """Helper to reach the value label inside a stat frame."""
    lay = self.layout()
    return lay.itemAt(1).widget()

QFrame._find_val = _find_val
