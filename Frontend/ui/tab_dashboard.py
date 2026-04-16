"""
Screen Tracker — Dashboard Tab
================================
Tab 1: Live metric cards (Screen Time, CPU, RAM) + App list table.
MetricCard is identical to BehaviorShield's MetricCard — Task Manager style
scrolling filled area chart.

# ── CHANGES ──────────────────────────────────────────────────────────────────
# [CHANGED] Change 1: Screen Time card now shows a pill badge (today's total)
#           and a weekly bar chart (custom rounded bars via pg.GraphicsObject).
# [CHANGED] Change 3: App Usage Table — alternating row colors #0D1B2A/#0A1628.
#           Status column replaced with pill-shaped QLabel badges in cell widgets.
#           "LIMIT HIT" badge pulses via QPropertyAnimation on opacity.
# [UNCHANGED] CPU card, RAM card, table layout/sizes, dashboard proportions.
"""

from __future__ import annotations
from datetime import datetime

# [CHANGED] Additional imports for animations, graphics, and new widgets
from PyQt5.QtCore import (
    Qt, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QRectF, pyqtProperty,
)
from PyQt5.QtGui import (
    QColor, QBrush, QFont, QPainter, QPainterPath,
    QLinearGradient,
)
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QSplitter, QSizePolicy,
    QAbstractItemView, QGraphicsOpacityEffect,
)

from ui.theme import (
    BG_PANEL, BG_BASE, BORDER, ACCENT, SAFE, WARN, DANGER,
    TEXT, TEXT_DIM, FONT_DATA, FONT_UI,
    CHART_CPU, CHART_RAM, CHART_TIME, CHART_BG,
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


# ── [CHANGED] Custom Rounded Bar — used in weekly chart ──────────────────────

class RoundedBarItem(pg.GraphicsObject):
    """
    Custom pg.GraphicsObject that draws bars with rounded top corners only.
    Used in the Screen Time weekly bar chart.
    """
    def __init__(self, x_vals, y_vals, width=0.6, today_idx=None):
        super().__init__()
        self._x      = list(x_vals)
        self._y      = list(y_vals)
        self._width  = width
        self._today  = today_idx  # index of today's bar (cyan)
        self._picture = None
        self._build_picture()

    def _build_picture(self):
        from PyQt5.QtGui import QPicture
        self._picture = QPicture()
        p = QPainter(self._picture)
        p.setRenderHint(QPainter.Antialiasing)

        for i, (x, y) in enumerate(zip(self._x, self._y)):
            if y <= 0:
                continue
            color = QColor("#00E5FF") if i == self._today else QColor("#4A7FA5")
            p.setBrush(QBrush(color))
            p.setPen(Qt.NoPen)

            # Build a path: flat bottom, rounded top corners only
            # Uses quadTo bezier curves instead of the broken path.united() approach
            r  = min(5.0, self._width / 2.0, y / 2.0)   # safe radius
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
            (self._x[-1] - self._x[0]) + 2 * self._width,
            max_y * 1.1,
        )


# ── [CHANGED] Screen Time Card — pill badge + weekly bar chart ────────────────

class ScreenTimeCard(QFrame):
    """
    Replacement for the Screen Time MetricCard.
    Top: pill badge with today's total (⏱ Xh Ym).
    Bottom: weekly bar chart (Mon-Sun, rounded bars).
    Card size/position UNCHANGED — same min sizes as MetricCard.
    """
    def __init__(self, db_reader, parent=None):
        super().__init__(parent)
        self.db = db_reader
        self._build()

    def _build(self):
        # [UNCHANGED] — same minimum sizes as original MetricCard
        self.setMinimumHeight(160)
        self.setMinimumWidth(180)
        self.setStyleSheet(f"""
            ScreenTimeCard {{
                background: {BG_PANEL};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Title row — [UNCHANGED] same as MetricCard title row style
        title_row = QHBoxLayout()
        title_lbl = QLabel("SCREEN TIME")
        title_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:8pt; letter-spacing:2px;"
        )
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        layout.addLayout(title_row)

        # [CHANGED] Pill badge — constrained width so it doesn't expand full card
        self._pill = QLabel("⏱  —")
        self._pill.setAlignment(Qt.AlignCenter)
        self._pill.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._pill.setStyleSheet("""
            QLabel {
                background: #00E5FF;
                color: #0D1B2A;
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 10pt;
            }
        """)
        self._pill.setFixedHeight(28)
        pill_row = QHBoxLayout()
        pill_row.setContentsMargins(0, 0, 0, 0)
        pill_row.addWidget(self._pill)
        pill_row.addStretch()
        layout.addLayout(pill_row)

        # [CHANGED] Weekly bar chart — PyQtGraph PlotWidget
        self._plot = pg.PlotWidget()
        self._plot.setMinimumHeight(80)
        self._plot.setMaximumHeight(110)
        self._plot.setBackground("transparent")
        self._plot.showAxis("left",   False)
        self._plot.showAxis("bottom", True)
        self._plot.setMouseEnabled(False, False)
        self._plot.setMenuEnabled(False)

        # Grid: horizontal only, subtle color
        self._plot.showGrid(x=False, y=True, alpha=0.25)

        # Style grid lines colour via view box
        self._plot.getViewBox().setBackgroundColor("transparent")

        # X-axis: Mon-Sun labels
        self._days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        ticks = [(i, d) for i, d in enumerate(self._days)]
        ax = self._plot.getAxis("bottom")
        ax.setTicks([ticks])
        ax.setStyle(tickFont=QFont(FONT_DATA, 7))
        ax.setTextPen(pg.mkPen(TEXT_DIM))
        ax.setPen(pg.mkPen(None))      # no axis border line

        # [CHANGED] Permanently clamp Y >= 0 and disable auto-range
        self._plot.getViewBox().setLimits(yMin=0)
        self._plot.getViewBox().disableAutoRange()

        layout.addWidget(self._plot)

    # ── Public API ─────────────────────────────────────────────────────────

    def update_time(self, seconds: int):
        """Update pill badge text — called every live_tick."""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        if h > 0:
            self._pill.setText(f"⏱  {h}h {m}m")
        else:
            self._pill.setText(f"⏱  {m}m")

    def refresh_chart(self):
        """Re-query weekly data and redraw bars."""
        import math
        weekly = self.db.get_weekly_screen_time()
        today_abbr = datetime.now().strftime("%a")  # 'Mon', 'Tue', ...
        today_idx  = self._days.index(today_abbr) if today_abbr in self._days else None

        x_vals = list(range(len(self._days)))
        y_vals = [weekly.get(d, 0) / 60 for d in self._days]  # minutes → hours

        self._plot.clear()
        bar_item = RoundedBarItem(x_vals, y_vals, width=0.6, today_idx=today_idx)
        self._plot.addItem(bar_item)

        # [CHANGED] Dynamic Y scale: ceil to next whole hour so ticks are clean integers
        raw_max = max(y_vals) if any(y > 0 for y in y_vals) else 1.0
        nice_max = max(math.ceil(raw_max * 1.15), 1)   # at least 1 h ceiling
        self._plot.getViewBox().disableAutoRange()
        self._plot.setYRange(0, nice_max, padding=0)
        self._plot.setLabel("left", "hours", color=TEXT_DIM, **{"font-size": "7pt"})


# ── MetricCard — identical to BehaviorShield ─────────────────────────────────

# [UNCHANGED] — CPU and RAM cards use this exact class unchanged
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


# ── [CHANGED] Pill Badge Widget ───────────────────────────────────────────────

class StatusPill(QLabel):
    """
    Pill-shaped badge. Supports optional pulsing opacity animation (LIMIT HIT).
    """
    def __init__(self, text: str, limit_hit: bool = False, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self._anim = None

        if limit_hit:
            self.setStyleSheet("""
                QLabel {
                    background: #FF1744;
                    color: white;
                    border-radius: 10px;
                    padding: 3px 10px;
                    font-weight: bold;
                    font-size: 8pt;
                }
            """)
            # Pulsing opacity: 0.4 → 1.0, 800ms, loop
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
            self._anim = QPropertyAnimation(effect, b"opacity", self)
            self._anim.setDuration(800)
            self._anim.setStartValue(0.4)
            self._anim.setEndValue(1.0)
            self._anim.setEasingCurve(QEasingCurve.SineCurve)
            self._anim.setLoopCount(-1)
            self._anim.start()
        else:
            self.setStyleSheet("""
                QLabel {
                    background: #00C853;
                    color: white;
                    border-radius: 10px;
                    padding: 3px 10px;
                    font-weight: bold;
                    font-size: 8pt;
                }
            """)


# ── [CHANGED] App List Table — pill badges + alternating row colors ───────────

class AppTable(QWidget):
    """
    App usage table matching BehaviorShield's ProcessTable style.
    Columns: App Name | Today's Usage | Time Limit | Status
    Row click → emits row_selected(app_name, seconds)

    [CHANGED] Status column uses StatusPill badge widgets (inline QLabel).
    [CHANGED] Alternating row colors: #0D1B2A (odd) / #0A1628 (even).
    [UNCHANGED] Row heights, column widths, table size, table position.
    """
    row_selected = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apps: list[tuple[str, int]] = []
        self._pill_refs: list[StatusPill] = []   # keep refs to avoid GC
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # [UNCHANGED] Header bar
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

        # [UNCHANGED] Table configuration
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["APP NAME", "CATEGORY", "TODAY'S USAGE", "TIME LIMIT", "STATUS"]
        )
        self._table.setAlternatingRowColors(False)   # [CHANGED] We paint manually
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.setShowGrid(False)
        self._table.cellClicked.connect(self._on_click)

        # [CHANGED] Alternating row colors injected via stylesheet
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: #0A1628;
                alternate-background-color: #0D1B2A;
                border: none;
            }}
            QTableWidget::item {{
                padding: 4px 10px;
                border-bottom: 1px solid {BORDER};
            }}
        """)
        self._table.setAlternatingRowColors(True)

        layout.addWidget(self._table)

    def update_apps(self, apps: list[tuple[str, int]], limits: dict, categories: dict = None):
        self._apps = apps
        self._pill_refs = []
        self._count_lbl.setText(f"{len(apps)} apps")
        self._table.setRowCount(len(apps))
        if categories is None:
            categories = {}

        for row, (app_name, seconds) in enumerate(apps):
            # [UNCHANGED] row height
            self._table.setRowHeight(row, 32)

            # [UNCHANGED] App name column (col 0)
            name_item = QTableWidgetItem(f"  {short_name(app_name)}")
            name_item.setForeground(QBrush(QColor(app_color(row))))
            self._table.setItem(row, 0, name_item)

            # [NEW] Category column (col 1) — colored pill badge
            cat = categories.get(app_name, "Other")
            cat_color = CATEGORY_COLORS.get(cat, "#64748b")
            cat_pill = QLabel(cat)
            cat_pill.setAlignment(Qt.AlignCenter)
            cat_pill.setStyleSheet(f"""
                QLabel {{
                    background: {cat_color}22;
                    color: {cat_color};
                    border: 1px solid {cat_color}66;
                    border-radius: 9px;
                    padding: 2px 9px;
                    font-size: 8pt;
                    font-weight: bold;
                }}
            """)
            cat_pill.setFixedHeight(22)
            cat_container = QWidget()
            cat_container.setStyleSheet("background: transparent;")
            cc_lay = QHBoxLayout(cat_container)
            cc_lay.setContentsMargins(4, 4, 4, 4)
            cc_lay.addWidget(cat_pill)
            cc_lay.addStretch()
            self._table.setCellWidget(row, 1, cat_container)

            # [UNCHANGED] Usage column (col 2)
            usage_item = QTableWidgetItem(fmt_time(seconds))
            usage_item.setForeground(QBrush(QColor(TEXT)))
            usage_item.setFont(QFont(FONT_DATA, 9))
            self._table.setItem(row, 2, usage_item)

            # [UNCHANGED] Time limit column (col 3)
            limit = limits.get(app_name)
            if limit:
                limit_item = QTableWidgetItem(f"{limit} min/day")
                limit_item.setForeground(QBrush(QColor(WARN)))
            else:
                limit_item = QTableWidgetItem("—  Set limit")
                limit_item.setForeground(QBrush(QColor(TEXT_DIM)))
            self._table.setItem(row, 3, limit_item)

            # [UNCHANGED] Status column (col 4) — pill badge widget
            limit_hit = bool(limit and (seconds // 60) >= limit)
            pill_text = "LIMIT HIT" if limit_hit else "OK"
            pill = StatusPill(pill_text, limit_hit=limit_hit)
            self._pill_refs.append(pill)

            # Wrap pill in a centered container widget
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            c_lay = QHBoxLayout(container)
            c_lay.setContentsMargins(4, 2, 4, 2)
            c_lay.addWidget(pill)
            c_lay.addStretch()
            self._table.setCellWidget(row, 4, container)

    def _on_click(self, row: int, _col: int):
        if row < len(self._apps):
            app_name, seconds = self._apps[row]
            self.row_selected.emit(app_name, seconds)


# ── Dashboard Tab ─────────────────────────────────────────────────────────────

class DashboardTab(QWidget):
    """
    Main dashboard — 3 metric cards + app usage table.
    Same layout as BehaviorShield's DashboardTab.

    [CHANGED] card_time is now ScreenTimeCard instead of MetricCard.
    [UNCHANGED] card_cpu, card_ram, table, layout proportions.
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

        # [CHANGED] Screen Time card — now ScreenTimeCard with pill + weekly chart
        self.card_time = ScreenTimeCard(self.db)
        self.card_time.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # [UNCHANGED] CPU card
        self.card_cpu = MetricCard("CPU", "%", CHART_CPU, y_max=100.0)
        self.card_cpu.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # [UNCHANGED] RAM card
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
            background:#1f1500;
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
        apps       = self.db.get_today_apps()
        limits     = self.db.get_all_time_limits()
        categories = self.db.get_all_categories()
        active_sec, idle_sec = self.db.get_today_totals()

        self.card_time.update_time(active_sec)   # [CHANGED] pill badge
        self.card_time.refresh_chart()            # [CHANGED] weekly bar chart
        self.app_table.update_apps(apps, limits, categories)

    def push_live(self, cpu: float, ram_mb: float, is_active: bool):
        """Called every second by the worker timer."""
        self.card_cpu.push(cpu)
        self.card_ram.push(ram_mb)

        # [CHANGED] Update pill badge every live tick
        active_sec, _ = self.db.get_today_totals()
        self.card_time.update_time(active_sec)

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
