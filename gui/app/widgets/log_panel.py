"""Log / output panel."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel,
)

_STYLE = """
QTextEdit {
    background: #11111b;
    color: #cdd6f4;
    border: 1px solid #313244;
    border-radius: 6px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 6px;
}
QPushButton#clearBtn {
    background: transparent;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 3px 10px;
    color: #6c7086;
    font-size: 11px;
}
QPushButton#clearBtn:hover { color: #cdd6f4; border-color: #cdd6f4; }
"""

_COLORS = {
    "info":    "#cdd6f4",
    "success": "#a6e3a1",
    "error":   "#f38ba8",
    "warn":    "#fab387",
    "dim":     "#6c7086",
}


class LogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(_STYLE)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("Processing Log")
        title.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("clearBtn")
        clear_btn.setFixedHeight(24)
        clear_btn.clicked.connect(self.clear)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text)

    # ------------------------------------------------------------------
    def _append(self, text: str, color: str):
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._text.setTextCursor(cursor)
        self._text.insertHtml(
            f'<span style="color:{color};">{text.replace("<", "&lt;").replace(">", "&gt;")}</span><br>'
        )
        self._text.ensureCursorVisible()

    def append_log(self, text: str):
        """Route log-level prefixed strings from the worker."""
        if text.startswith("ERROR"):
            self._append(text, _COLORS["error"])
        elif text.startswith("WARNING"):
            self._append(text, _COLORS["warn"])
        elif "successfully" in text.lower() or "saved" in text.lower():
            self._append(text, _COLORS["success"])
        else:
            self._append(text, _COLORS["info"])

    def append_info(self, text: str):
        self._append(text, _COLORS["dim"])

    def append_success(self, text: str):
        self._append(text, _COLORS["success"])

    def append_error(self, text: str):
        self._append(text, _COLORS["error"])

    def clear(self):
        self._text.clear()
