"""
Screen Tracker — App Detail Tab
=================================
Tab 2: Detailed view for a specific app.
Shows hourly bar chart + time limit controls.
Same panel/card style as BehaviorShield.

# ── CHANGES ──────────────────────────────────────────────────────────────────
# [CHANGED] Change 2: "HOURLY USAGE — TODAY" label replaced with Today/This Week
#           toggle buttons (QHBoxLayout). Graph backed by custom RoundedGradientBars
#           (pg.GraphicsObject, gradient fill, hover tooltips). Toggle switches
#           between hourly (00h-23h) and weekly (Mon-Sun) data.
# [CHANGED] Change 3: App header gets a colored status dot (8px, red pulses).
# [UNCHANGED] Container sizes, layout proportions, CPU/RAM cards, limit panel.
"""

from __future__ import annotations
from datetime import datetime

# [CHANGED] Extra imports for animations, gradient painting, tooltips
from PyQt5.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF,
)
from PyQt5.QtGui import (
    QColor, QBrush, QFont, QPainter, QPainterPath,
    QLinearGradient,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QSpinBox, QComboBox,
    QSizePolicy, QScrollArea, QGraphicsOpacityEffect,
    QToolTip,
)

from ui.theme import (
    BG_PANEL, BG_BASE, BG_INPUT, BORDER, BORDER_LIGHT,
    ACCENT, ACCENT_DIM, SAFE, SAFE_BG, WARN, WARN_BG, DANGER, DANGER_BG,
    TEXT, TEXT_DIM, FONT_DATA, FONT_UI,
    CHART_TIME, CHART_CPU, CHART_RAM, CHART_BG,
    app_color, CATEGORY_COLORS,
)

import pyqtgraph as pg
pg.setConfigOption("background", CHART_BG)
pg.setConfigOption("foreground", TEXT_DIM)
pg.setConfigOption("antialias", True)


# [UNCHANGED]
def fmt_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h} hrs, {m} mins"
    return f"{m} mins"


# [UNCHANGED]
def short_name(app: str) -> str:
    return app.replace(".exe", "").replace(".app", "")


# ── [UNCHANGED] Stat Cell ─────────────────────────────────────────────────────

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


# ── [CHANGED] Custom Rounded Gradient Bar Item ────────────────────────────────

class RoundedGradientBars(pg.GraphicsObject):
    """
    Custom pg.GraphicsObject.
    Draws bars with rounded top corners + QLinearGradient fill (cyan→dark blue).
    Provides hover tooltip: "X mins at Yh" (hourly) or "X mins on Day" (weekly).
    """
    def __init__(self, x_vals, y_vals, labels, width=0.6, mode="hourly"):
        super().__init__()
        self._x      = list(x_vals)
        self._y      = list(y_vals)
        self._labels = list(labels)   # human-readable labels for tooltip
        self._width  = width
        self._mode   = mode           # "hourly" or "weekly"
        self._picture = None
        self.setAcceptHoverEvents(True)
        self._build_picture()

    def _build_picture(self):
        from PyQt5.QtGui import QPicture
        self._picture = QPicture()
        p = QPainter(self._picture)
        p.setRenderHint(QPainter.Antialiasing)

        for x, y in zip(self._x, self._y):
            if y <= 0:
                continue

            # Gradient: top=#00E5FF, bottom=#004D99
            grad = QLinearGradient(x, y, x, 0)
            grad.setColorAt(0.0, QColor("#004D99"))
            grad.setColorAt(1.0, QColor("#00E5FF"))

            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)

            # Build path: flat bottom, rounded top corners via quadTo
            r  = min(5.0, self._width / 2.0, y / 2.0)
            x0 = x - self._width / 2.0
            x1 = x + self._width / 2.0

            path = QPainterPath()
            path.moveTo(x0, 0)              # bottom-left
            path.lineTo(x0, y - r)          # left side up
            path.quadTo(x0, y, x0 + r, y)  # top-left rounded corner
            path.lineTo(x1 - r, y)          # top edge
            path.quadTo(x1, y, x1, y - r)  # top-right rounded corner
            path.lineTo(x1, 0)              # right side down
            path.closeSubpath()
            p.drawPath(path)

        p.end()

    def paint(self, p, *args):
        self._picture.play(p)

    def boundingRect(self):
        if not self._x or not self._y:
            return QRectF()
        max_y = max(self._y) if self._y else 1
        return QRectF(
            self._x[0] - self._width,
            0,
            (self._x[-1] - self._x[0] + 2 * self._width) if len(self._x) > 1 else self._width * 2,
            max_y * 1.1,
        )

    def hoverEvent(self, event):
        """Show QToolTip with X mins at/on label."""
        if event.isExit():
            QToolTip.hideText()
            return
        pos = event.pos()
        px  = pos.x()
        for i, (x, y) in enumerate(zip(self._x, self._y)):
            if abs(px - x) < self._width / 2:
                mins = int(round(y))
                lbl  = self._labels[i]
                if self._mode == "hourly":
                    tip = f"{mins} mins at {lbl}"
                else:
                    tip = f"{mins} mins on {lbl}"
                scene_pos = event.screenPos()
                QToolTip.showText(
                    scene_pos.toPoint(),
                    tip,
                )
                return
        QToolTip.hideText()


# ── [CHANGED] Status Dot for App Header ──────────────────────────────────────

class StatusDot(QLabel):
    """
    8px colored dot prepended to app name.
    If red (LIMIT HIT), pulses size via opacity animation (best proxy in QLabel).
    """
    def __init__(self, parent=None):
        super().__init__("●", parent)
        self._anim = None
        self._green()

    def _green(self):
        if self._anim:
            self._anim.stop()
            self._anim = None
        self.setGraphicsEffect(None)
        self.setStyleSheet(
            "color: #00C853; font-size: 8pt; background: transparent; border: none;"
        )

    def _red(self):
        self.setStyleSheet(
            "color: #FF1744; font-size: 8pt; background: transparent; border: none;"
        )
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self._anim = QPropertyAnimation(effect, b"opacity", self)
        self._anim.setDuration(800)
        self._anim.setStartValue(0.3)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.SineCurve)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def set_limit_hit(self, hit: bool):
        if hit:
            self._red()
        else:
            self._green()


# ── [CHANGED] Toggle Buttons for hourly/weekly graph ─────────────────────────

_TOGGLE_ACTIVE = """
    QPushButton {
        background: #00E5FF;
        color: #0D1B2A;
        border-radius: 5px;
        padding: 4px 12px;
        font-weight: bold;
        font-size: 8pt;
        border: none;
    }
"""
_TOGGLE_INACTIVE = """
    QPushButton {
        background: transparent;
        color: #607D8B;
        border: 1px solid #1E2A3A;
        border-radius: 5px;
        padding: 4px 12px;
        font-size: 8pt;
    }
"""


# ── App Detail Tab ────────────────────────────────────────────────────────────

class AppDetailTab(QWidget):
    """
    Detailed view for a selected app.
    Mirrors BehaviorShield's process detail panel layout.

    [CHANGED] Graph header → Today/This Week toggle buttons.
    [CHANGED] Bar chart → RoundedGradientBars with hover tooltip.
    [CHANGED] App title bar → prepended colored StatusDot.
    [UNCHANGED] All layout proportions, container sizes, limit panel.
    """
    go_back        = pyqtSignal()
    limit_saved    = pyqtSignal(str, int)   # app_name, minutes
    category_changed = pyqtSignal()          # tell dashboard to refresh

    def __init__(self, db_reader, parent=None):
        super().__init__(parent)
        self.db       = db_reader
        self.app_name = ""
        self.seconds  = 0
        self._view    = "today"   # "today" | "weekly"
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

        # [CHANGED] Status dot before app name
        self._status_dot = StatusDot()
        top_lay.addWidget(self._status_dot)

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

        # [CHANGED] Toggle button row replaces plain "HOURLY USAGE — TODAY" label
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(6)
        toggle_row.setContentsMargins(0, 0, 0, 0)

        self._btn_today = QPushButton("Today")
        self._btn_today.setFixedHeight(26)
        self._btn_today.clicked.connect(self._switch_today)

        self._btn_week = QPushButton("This Week")
        self._btn_week.setFixedHeight(26)
        self._btn_week.clicked.connect(self._switch_weekly)

        toggle_row.addWidget(self._btn_today)
        toggle_row.addWidget(self._btn_week)
        toggle_row.addStretch()
        hourly_lay.addLayout(toggle_row)

        # [CHANGED] PlotWidget with #0A1628 background, visible horizontal grid
        self._hourly_plot = pg.PlotWidget()
        self._hourly_plot.setBackground("#0A1628")
        self._hourly_plot.setMouseEnabled(False, False)
        self._hourly_plot.setMenuEnabled(False)

        # [CHANGED] Explicit grid pen — visible on dark background
        _grid_pen = pg.mkPen(color="#2A3F5F", width=1, style=Qt.SolidLine)
        self._hourly_plot.getPlotItem().getAxis("left").setGrid(180)   # y grid alpha 0-255
        self._hourly_plot.getPlotItem().getAxis("bottom").setGrid(0)    # no x grid
        # Override the grid pen used by the axes
        self._hourly_plot.getAxis("left").setPen(pg.mkPen(color="#1E2A3A", width=1))
        self._hourly_plot.getAxis("bottom").setPen(pg.mkPen(color="#1E2A3A", width=1))
        self._hourly_plot.getAxis("bottom").setTextPen(pg.mkPen(TEXT_DIM))
        self._hourly_plot.getAxis("left").setTextPen(pg.mkPen(TEXT_DIM))
        self._hourly_plot.getAxis("bottom").setStyle(tickFont=QFont(FONT_DATA, 8))
        self._hourly_plot.getAxis("left").setStyle(tickFont=QFont(FONT_DATA, 8))
        self._hourly_plot.setMinimumHeight(160)
        # [CHANGED] Permanently clamp Y >= 0 so negative axis never appears
        self._hourly_plot.getViewBox().setLimits(yMin=0)
        self._hourly_plot.getViewBox().disableAutoRange()
        hourly_lay.addWidget(self._hourly_plot)

        charts_row.addWidget(hourly_frame, 2)

        # [UNCHANGED] Right column: CPU + RAM mini cards
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

        # ── Category panel ────────────────────────────────────────
        cat_frame = QFrame()
        cat_frame.setStyleSheet(
            f"background:{BG_PANEL}; border:1px solid {BORDER}; border-radius:6px;"
        )
        cat_lay = QHBoxLayout(cat_frame)
        cat_lay.setContentsMargins(16, 10, 16, 10)
        cat_lay.setSpacing(16)

        cat_title = QLabel("APP CATEGORY")
        cat_title.setStyleSheet(
            f"color:{ACCENT}; font-family:{FONT_UI}; font-size:9pt; "
            f"font-weight:bold; letter-spacing:2px; background:transparent; border:none;"
        )
        cat_lay.addWidget(cat_title)
        cat_lay.addStretch()

        lbl_cat = QLabel("Category:")
        lbl_cat.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:9pt; "
            f"background:transparent; border:none;"
        )
        cat_lay.addWidget(lbl_cat)

        from db_reader import CATEGORIES
        self._cat_combo = QComboBox()
        self._cat_combo.addItems(CATEGORIES)
        self._cat_combo.setFixedHeight(30)
        self._cat_combo.setFixedWidth(160)
        cat_lay.addWidget(self._cat_combo)

        self._cat_dot = QLabel("■")
        self._cat_dot.setStyleSheet("font-size:14pt; color:#374151; background:transparent; border:none;")
        cat_lay.addWidget(self._cat_dot)

        save_cat_btn = QPushButton("Save Category")
        save_cat_btn.setFixedHeight(30)
        save_cat_btn.setStyleSheet(f"""
            QPushButton {{
                background:{ACCENT_DIM}; color:{BG_BASE};
                border:1px solid {ACCENT}; border-radius:4px;
                padding:0 16px; font-weight:bold;
                font-family:{FONT_UI}; font-size:9pt;
            }}
            QPushButton:hover {{ background:{ACCENT}; }}
        """)
        save_cat_btn.clicked.connect(self._save_category)
        cat_lay.addWidget(save_cat_btn)

        # Update dot color when selection changes
        self._cat_combo.currentTextChanged.connect(self._update_cat_dot)

        root.addWidget(cat_frame)

        # Set initial toggle state
        self._apply_toggle("today")

    # ── [CHANGED] Toggle helpers ──────────────────────────────────────────

    def _apply_toggle(self, view: str):
        """Style the buttons and store current view."""
        self._view = view
        if view == "today":
            self._btn_today.setStyleSheet(_TOGGLE_ACTIVE)
            self._btn_week.setStyleSheet(_TOGGLE_INACTIVE)
        else:
            self._btn_today.setStyleSheet(_TOGGLE_INACTIVE)
            self._btn_week.setStyleSheet(_TOGGLE_ACTIVE)

    def _switch_today(self):
        self._apply_toggle("today")
        self._update_hourly()

    def _switch_weekly(self):
        self._apply_toggle("weekly")
        self._update_weekly()

    # ── Load app data ─────────────────────────────────────────────────────

    def load(self, app_name: str, seconds: int):
        self.app_name = app_name
        self.seconds  = seconds

        self._app_title.setText(short_name(app_name).upper())
        self._date_lbl.setText(datetime.now().strftime("%A, %d %b %Y"))

        # Stat cards
        self._stat_total._find_val().setText(fmt_time(seconds))

        limit = self.db.get_time_limit(app_name)
        limit_hit = bool(limit and (seconds // 60) >= limit)

        # [CHANGED] Update status dot
        self._status_dot.set_limit_hit(limit_hit)

        if limit:
            self._limit_spin.setValue(limit)
            self._stat_limit._find_val().setText(f"{limit} min/day")
            used_pct = min(100, int((seconds / 60) / limit * 100))
            self._stat_pct._find_val().setText(f"{used_pct}%")
            if limit_hit:
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

        # Load current category into combo
        current_cat = self.db.get_app_category(app_name)
        idx = self._cat_combo.findText(current_cat)
        if idx >= 0:
            self._cat_combo.setCurrentIndex(idx)
        self._update_cat_dot(current_cat)

        # Draw chart in current view
        if self._view == "today":
            self._update_hourly()
        else:
            self._update_weekly()

    # [CHANGED] Hourly chart — custom rounded gradient bars, 00h-21h x-axis
    def _update_hourly(self):
        import math
        hourly = self.db.get_app_hourly(self.app_name)
        x_vals = [h for h, _ in hourly]
        y_vals = [s / 60 for _, s in hourly]   # seconds → minutes
        labels = [f"{h:02d}h" for h, _ in hourly]

        self._hourly_plot.clear()
        bars = RoundedGradientBars(x_vals, y_vals, labels, width=0.6, mode="hourly")
        self._hourly_plot.addItem(bars)

        # X-axis: 00h, 03h … 21h
        tick_labels = [(i, f"{i:02d}h") for i in range(0, 24, 3)]
        self._hourly_plot.getAxis("bottom").setTicks([tick_labels])
        self._hourly_plot.setLabel("left", "minutes", color=TEXT_DIM,
                                   **{"font-size": "8pt"})

        # [CHANGED] Dynamic Y: round up to next 5-minute mark for clean ticks
        raw_max = max(y_vals) if any(y > 0 for y in y_vals) else 5.0
        nice_max = max(math.ceil(raw_max * 1.15 / 5) * 5, 5)   # multiples of 5 min
        self._hourly_plot.getViewBox().disableAutoRange()
        self._hourly_plot.setYRange(0, nice_max, padding=0)

    # [CHANGED] Weekly chart — Mon-Sun, per-app data, Y axis in HOURS
    def _update_weekly(self):
        import math
        days   = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekly = self.db.get_app_weekly_screen_time(self.app_name)
        x_vals = list(range(len(days)))
        # [CHANGED] Convert minutes → hours for the Y axis
        y_vals = [weekly.get(d, 0) / 60 for d in days]
        labels = days

        self._hourly_plot.clear()
        bars = RoundedGradientBars(x_vals, y_vals, labels, width=0.6, mode="weekly")
        self._hourly_plot.addItem(bars)

        ticks = [(i, d) for i, d in enumerate(days)]
        self._hourly_plot.getAxis("bottom").setTicks([ticks])
        # [CHANGED] Label is now 'hours' not 'minutes'
        self._hourly_plot.setLabel("left", "hours", color=TEXT_DIM,
                                   **{"font-size": "8pt"})

        # [CHANGED] Dynamic Y: ceil to next whole hour for clean integer ticks
        raw_max = max(y_vals) if any(y > 0 for y in y_vals) else 1.0
        nice_max = max(math.ceil(raw_max * 1.15), 1)   # at least 1 h ceiling
        self._hourly_plot.getViewBox().disableAutoRange()
        self._hourly_plot.setYRange(0, nice_max, padding=0)

    # ── [UNCHANGED] Live update ───────────────────────────────────────────

    def push_live(self, cpu: float, ram_mb: float):
        self.card_cpu.push(cpu)
        self.card_ram.push(ram_mb)

    # ── [UNCHANGED] Limit actions ─────────────────────────────────────────

    def _save_limit(self):
        minutes = self._limit_spin.value()
        self.db.set_time_limit(self.app_name, minutes)
        self.limit_saved.emit(self.app_name, minutes)
        self._stat_limit._find_val().setText(f"{minutes} min/day")

    def _clear_limit(self):
        self.db.set_time_limit(self.app_name, 9999)
        self._stat_limit._find_val().setText("No limit")
        self._stat_pct._find_val().setText("—")

    def _save_category(self):
        """Persist the selected category and notify the dashboard to refresh."""
        cat = self._cat_combo.currentText()
        self.db.set_app_category(self.app_name, cat)
        self._update_cat_dot(cat)
        self.category_changed.emit()

    def _update_cat_dot(self, cat: str):
        """Update the colour swatch next to the combo to reflect the current category."""
        color = CATEGORY_COLORS.get(cat, "#374151")
        self._cat_dot.setStyleSheet(
            f"font-size:14pt; color:{color}; background:transparent; border:none;"
        )


# ── Patch make_stat to expose val label ──────────────────────────────────────

# [UNCHANGED]
def _find_val(self):
    """Helper to reach the value label inside a stat frame."""
    lay = self.layout()
    return lay.itemAt(1).widget()

QFrame._find_val = _find_val
