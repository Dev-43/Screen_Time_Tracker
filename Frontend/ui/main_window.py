"""
Screen Tracker — Main Application Window
==========================================
Ties all tabs, worker thread, tray icon, and popups together.
Structure is identical to BehaviorShield's MainWindow.
Entry point: run main.py
"""

from __future__ import annotations
import sys

from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QColor, QPixmap, QPainter, QPolygon
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QTabWidget, QWidget,
    QStatusBar, QLabel, QSystemTrayIcon, QMenu, QAction,
    QHBoxLayout, QFrame,
)
from PyQt5.QtCore import QPoint

from db_reader import DBReader
from worker import PollWorker
from ui.tab_dashboard import DashboardTab
from ui.tab_detail import AppDetailTab
from ui.warning_popup import TimeLimitPopup
from ui.theme import (
    STYLESHEET, BG_BASE, BG_PANEL, BORDER, ACCENT,
    DANGER, WARN, SAFE, TEXT, TEXT_DIM, FONT_UI, FONT_DATA,
)


# ── Tray Icon Generator — same as BehaviorShield ──────────────────────────────

def _make_tray_icon(color: str) -> QIcon:
    px = QPixmap(32, 32)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    # Clock/timer icon (simple circle)
    painter.drawEllipse(2, 2, 28, 28)
    painter.setBrush(QColor(BG_BASE))
    painter.drawEllipse(6, 6, 20, 20)
    painter.setBrush(QColor(color))
    # Clock hands
    painter.drawRect(15, 8, 2, 9)   # hour hand
    painter.drawRect(15, 15, 7, 2)  # minute hand
    painter.end()
    return QIcon(px)


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self, db_path: str):
        super().__init__()

        # ── Core objects ─────────────────────────────────────────────────
        self.db_reader      = DBReader(db_path)
        self._active_popup: TimeLimitPopup | None = None
        self._alerted_apps: set[str] = set()   # don't re-alert same app

        # ── Window setup ─────────────────────────────────────────────────
        self.setWindowTitle("Screen Tracker — Desktop Activity Monitor")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)

        # ── Build UI ─────────────────────────────────────────────────────
        self._build_tabs()
        self._build_statusbar()
        self._build_tray()
        self._start_worker()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Tab 0 — Dashboard
        self.tab_dashboard = DashboardTab(self.db_reader)
        self.tab_dashboard.app_selected.connect(self._open_detail)
        self.tabs.addTab(self.tab_dashboard, "  Dashboard  ")

        # Tab 1 — App Detail (hidden until app selected)
        self.tab_detail = AppDetailTab(self.db_reader)
        self.tab_detail.go_back.connect(self._go_back)
        self.tab_detail.limit_saved.connect(self._on_limit_saved)
        self.tabs.addTab(self.tab_detail, "  App Detail  ")
        self.tabs.setTabEnabled(1, False)

        self.setCentralWidget(self.tabs)

    def _build_statusbar(self):
        """Identical to BehaviorShield's status bar."""
        sb = self.statusBar()
        sb.setStyleSheet(f"""
            QStatusBar {{
                background:{BG_PANEL}; border-top:1px solid {BORDER};
                font-family:{FONT_DATA}; font-size:8pt; color:{TEXT_DIM};
            }}
        """)

        self._status_lbl = QLabel("Initializing…")
        self._status_lbl.setStyleSheet(f"color:{TEXT_DIM}; padding:0 8px;")
        sb.addWidget(self._status_lbl)

        sb.addPermanentWidget(QLabel("  "))

        self._db_lbl = QLabel(f"DB: {self.db_reader.db_path}")
        self._db_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; padding:0 8px; font-family:{FONT_DATA}; font-size:8pt;"
        )
        sb.addPermanentWidget(self._db_lbl)

        self._live_dot = QLabel("●")
        self._live_dot.setStyleSheet(f"color:{TEXT_DIM}; padding:0 8px;")
        sb.addPermanentWidget(self._live_dot)

        self._rows_lbl = QLabel("0 rows")
        self._rows_lbl.setStyleSheet(f"color:{TEXT_DIM}; padding:0 8px;")
        sb.addPermanentWidget(self._rows_lbl)

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_make_tray_icon(SAFE))
        self._tray.setToolTip("Screen Tracker — Running")

        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background:{BG_PANEL}; color:{TEXT}; border:1px solid {BORDER}; }}
            QMenu::item:selected {{ background:{ACCENT}; color:{BG_BASE}; }}
        """)

        show_action = QAction("Open Screen Tracker", self)
        show_action.triggered.connect(self.show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    # ── Worker ────────────────────────────────────────────────────────────────

    def _start_worker(self):
        self.worker = PollWorker(db_reader=self.db_reader)
        self.worker.live_tick.connect(self._on_live_tick)
        self.worker.full_refresh.connect(self._on_full_refresh)
        self.worker.limit_check.connect(self._on_limit_check)
        self.worker.row_count_ready.connect(self._on_row_count)
        self.worker.status_changed.connect(self._on_status)
        self.worker.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    @pyqtSlot(float, float, bool)
    def _on_live_tick(self, cpu: float, ram_mb: float, is_active: bool):
        self.tab_dashboard.push_live(cpu, ram_mb, is_active)

        if self.tabs.currentIndex() == 1:
            self.tab_detail.push_live(cpu, ram_mb)

        # Tray dot color
        color = SAFE if is_active else TEXT_DIM
        self._live_dot.setStyleSheet(f"color:{color}; padding:0 8px;")

    @pyqtSlot()
    def _on_full_refresh(self):
        self.tab_dashboard.refresh()

    @pyqtSlot()
    def _on_limit_check(self):
        exceeded = self.tab_dashboard.check_limits()
        for app_name, used_min, limit_min in exceeded:
            if app_name in self._alerted_apps:
                continue
            self._alerted_apps.add(app_name)
            self._show_limit_popup(app_name, used_min, limit_min)
            break  # one popup at a time

    @pyqtSlot(str, str)
    def _on_status(self, message: str, level: str):
        color = {"info": TEXT_DIM, "warn": WARN, "error": DANGER}.get(level, TEXT_DIM)
        self._status_lbl.setText(message)
        self._status_lbl.setStyleSheet(f"color:{color}; padding:0 8px;")

        dot_color = {"info": SAFE, "warn": WARN, "error": DANGER}.get(level, TEXT_DIM)
        self._live_dot.setStyleSheet(f"color:{dot_color}; padding:0 8px;")

    @pyqtSlot(int)
    def _on_row_count(self, count: int):
        self._rows_lbl.setText(f"{count:,} rows")

    @pyqtSlot(str, int)
    def _open_detail(self, app_name: str, seconds: int):
        self.tab_detail.load(app_name, seconds)
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1)

    @pyqtSlot()
    def _go_back(self):
        self.tabs.setCurrentIndex(0)
        self.tabs.setTabEnabled(1, False)
        self.tab_dashboard.refresh()

    @pyqtSlot(str, int)
    def _on_limit_saved(self, app_name: str, minutes: int):
        # Allow re-alerting after limit is changed
        self._alerted_apps.discard(app_name)
        self._on_status(
            f"Time limit for '{app_name}' set to {minutes} min/day", "info"
        )

    # ── Limit popup — identical flow to BehaviorShield ────────────────────────

    def _show_limit_popup(self, app_name: str, used_min: int, limit_min: int):
        if self._active_popup and self._active_popup.isVisible():
            return

        popup = TimeLimitPopup(app_name, used_min, limit_min, parent=self)
        popup.limit_changed.connect(self._on_popup_limit_changed)
        popup.dismissed.connect(self._on_popup_dismissed)
        self._active_popup = popup

        if hasattr(self, "_tray"):
            self._tray.showMessage(
                "⏰ Time Limit Reached",
                f"{app_name} has been used for {used_min} minutes today.",
                QSystemTrayIcon.Warning,
                5000,
            )
            self._tray.setIcon(_make_tray_icon(WARN))

        popup.show()
        popup.raise_()

    @pyqtSlot(str, int)
    def _on_popup_limit_changed(self, app_name: str, new_minutes: int):
        self.db_reader.set_time_limit(app_name, new_minutes)
        self._alerted_apps.discard(app_name)
        self._active_popup = None
        if hasattr(self, "_tray"):
            self._tray.setIcon(_make_tray_icon(SAFE))

    @pyqtSlot()
    def _on_popup_dismissed(self):
        self._active_popup = None
        if hasattr(self, "_tray"):
            self._tray.setIcon(_make_tray_icon(SAFE))

    # ── Tray ─────────────────────────────────────────────────────────────────

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_window()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Window Events ─────────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Minimize to tray — same as BehaviorShield."""
        if hasattr(self, "_tray") and self._tray.isVisible():
            self.hide()
            self._tray.showMessage(
                "Screen Tracker",
                "Still running in the background. Right-click tray icon to quit.",
                QSystemTrayIcon.Information,
                3000,
            )
            event.ignore()
        else:
            self._shutdown()
            event.accept()

    def _shutdown(self):
        if hasattr(self, "worker"):
            self.worker.stop()
            self.worker.wait(2000)
