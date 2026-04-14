"""
Screen Tracker — Time Limit Warning Popup
==========================================
Non-blocking popup when an app exceeds its daily time limit.
Pixel-for-pixel match to BehaviorShield's WarningPopup structure:
  - Red header bar with icon + title
  - App info card with usage details
  - Response buttons: Keep Limit / Change Limit / Dismiss
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QSpinBox,
    QApplication, QScrollArea, QWidget,
)

from ui.theme import (
    BG_BASE, BG_PANEL, BG_INPUT, BORDER,
    DANGER, DANGER_BG, WARN, WARN_BG, SAFE, SAFE_BG,
    ACCENT, ACCENT_DIM,
    TEXT, TEXT_DIM, FONT_DATA, FONT_UI,
)


def fmt_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h} hrs, {m} mins"
    return f"{m} mins"

def short_name(app: str) -> str:
    return app.replace(".exe", "").replace(".app", "")


class TimeLimitPopup(QDialog):
    """
    Non-blocking time limit alert.
    Same pattern as BehaviorShield's WarningPopup — modal=False,
    WindowStaysOnTopHint, red header bar, response buttons.

    Emits:
        limit_changed(app_name, new_minutes)
        dismissed()
    """
    limit_changed = pyqtSignal(str, int)
    dismissed     = pyqtSignal()

    def __init__(self, app_name: str, used_minutes: int,
                 limit_minutes: int, parent=None):
        super().__init__(parent)
        self.app_name     = app_name
        self.used_minutes = used_minutes
        self.limit_minutes = limit_minutes
        self._build()
        self._play_alert()

    def _build(self):
        self.setWindowTitle("⚠  Screen Tracker — Time Limit Reached")
        self.setMinimumWidth(480)
        self.setMaximumWidth(580)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(False)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BG_BASE};
                color: {TEXT};
            }}
            QLabel {{ font-family: {FONT_UI}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Red/amber header bar — identical to BehaviorShield ─────────
        header = QFrame()
        header.setStyleSheet(f"background:{WARN_BG}; border-bottom:2px solid {WARN};")
        header.setFixedHeight(72)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)

        icon_lbl = QLabel("⏰")
        icon_lbl.setStyleSheet(f"color:{WARN}; font-size:26pt; border:none;")
        h_lay.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_lbl = QLabel("TIME LIMIT REACHED")
        title_lbl.setStyleSheet(
            f"color:{WARN}; font-family:{FONT_UI}; font-size:13pt; "
            f"font-weight:bold; letter-spacing:3px; border:none;"
        )
        text_col.addWidget(title_lbl)

        from datetime import datetime
        sub_lbl = QLabel(
            f"{short_name(self.app_name)}  ·  {datetime.now().strftime('%H:%M')}"
        )
        sub_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_DATA}; font-size:9pt; border:none;"
        )
        text_col.addWidget(sub_lbl)

        h_lay.addLayout(text_col)
        h_lay.addStretch()
        root.addWidget(header)

        # ── App info card ────────────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {BG_PANEL};
                border: 1px solid {WARN};
                border-radius: 5px;
                margin: 14px 16px 0 16px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(8)

        # App name + usage
        name_row = QHBoxLayout()
        name_lbl = QLabel(short_name(self.app_name))
        name_lbl.setStyleSheet(
            f"color:{WARN}; font-family:{FONT_DATA}; font-size:14pt; "
            f"font-weight:bold; background:transparent; border:none;"
        )
        name_row.addWidget(name_lbl)
        name_row.addStretch()

        used_lbl = QLabel(f"Used: {self.used_minutes} min today")
        used_lbl.setStyleSheet(
            f"color:{TEXT}; font-family:{FONT_DATA}; font-size:10pt; "
            f"background:transparent; border:none;"
        )
        name_row.addWidget(used_lbl)
        card_lay.addLayout(name_row)

        # Details grid
        details = QHBoxLayout()
        details.setSpacing(12)

        for label, value, color in [
            ("TIME USED",    f"{self.used_minutes} min",  WARN),
            ("DAILY LIMIT",  f"{self.limit_minutes} min", TEXT_DIM),
            ("OVER BY",      f"{self.used_minutes - self.limit_minutes} min", DANGER),
        ]:
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:8pt; "
                f"letter-spacing:1px; background:transparent; border:none;"
            )
            val = QLabel(value)
            val.setStyleSheet(
                f"color:{color}; font-family:{FONT_DATA}; font-size:11pt; "
                f"font-weight:bold; background:transparent; border:none;"
            )
            col.addWidget(lbl)
            col.addWidget(val)
            details.addLayout(col)
            details.addStretch()

        card_lay.addLayout(details)

        # Change limit section
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background:{WARN_BG}; border:none; max-height:1px; margin:4px 0;")
        card_lay.addWidget(div)

        change_row = QHBoxLayout()
        change_lbl = QLabel("Change limit:")
        change_lbl.setStyleSheet(
            f"color:{TEXT_DIM}; font-family:{FONT_UI}; font-size:9pt; "
            f"background:transparent; border:none;"
        )
        change_row.addWidget(change_lbl)

        self._spin = QSpinBox()
        self._spin.setRange(5, 480)
        self._spin.setValue(self.limit_minutes)
        self._spin.setSuffix(" min")
        self._spin.setFixedHeight(28)
        self._spin.setFixedWidth(100)
        self._spin.setStyleSheet(f"""
            QSpinBox {{
                background:{BG_INPUT}; color:{TEXT};
                border:1px solid {BORDER}; border-radius:3px;
                padding:2px 6px; font-family:{FONT_DATA}; font-size:9pt;
            }}
        """)
        change_row.addWidget(self._spin)
        change_row.addStretch()
        card_lay.addLayout(change_row)

        root.addWidget(card)

        # ── Footer buttons — identical layout to BehaviorShield ──────────
        footer = QFrame()
        footer.setStyleSheet(
            f"background:{BG_PANEL}; border-top:1px solid {BORDER}; margin-top:14px;"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(16, 10, 16, 10)
        f_lay.setSpacing(8)

        f_lay.addStretch()

        # Save new limit
        save_btn = QPushButton("Save New Limit")
        save_btn.setFixedHeight(30)
        save_btn.setStyleSheet(self._btn_style(SAFE, SAFE_BG))
        save_btn.clicked.connect(self._save_limit)
        f_lay.addWidget(save_btn)

        # Keep limit (do nothing)
        keep_btn = QPushButton("Keep Limit")
        keep_btn.setFixedHeight(30)
        keep_btn.setStyleSheet(self._btn_style(TEXT_DIM, BG_BASE))
        keep_btn.clicked.connect(self._dismiss)
        f_lay.addWidget(keep_btn)

        # Dismiss
        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setFixedHeight(30)
        dismiss_btn.setStyleSheet(self._btn_style(WARN, WARN_BG))
        dismiss_btn.clicked.connect(self._dismiss)
        f_lay.addWidget(dismiss_btn)

        root.addWidget(footer)

    def _save_limit(self):
        new_limit = self._spin.value()
        self.limit_changed.emit(self.app_name, new_limit)
        self.close()

    def _dismiss(self):
        self.dismissed.emit()
        self.close()

    def _play_alert(self):
        try:
            import platform
            if platform.system() == "Windows":
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            else:
                QApplication.beep()
        except Exception:
            QApplication.beep()

    @staticmethod
    def _btn_style(fg: str, bg: str) -> str:
        return f"""
            QPushButton {{
                background:{bg}; color:{fg};
                border:1px solid {fg}; border-radius:4px;
                padding:4px 14px; font-family:{FONT_UI}; font-size:9pt;
            }}
            QPushButton:hover {{ background:{fg}; color:{BG_BASE}; }}
        """
