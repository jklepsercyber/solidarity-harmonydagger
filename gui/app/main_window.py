"""Main application window."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QLabel, QPushButton, QProgressBar,
)

from .widgets.file_panel import FilePanel
from .widgets.settings_panel import SettingsPanel
from .widgets.log_panel import LogPanel
from .workers.process_worker import ProcessWorker

_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 13px;
}
QPushButton#processBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 10px 28px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton#processBtn:hover { background-color: #b4befe; }
QPushButton#processBtn:disabled { background-color: #45475a; color: #6c7086; }
QProgressBar {
    border: 1px solid #45475a;
    border-radius: 4px;
    background: #313244;
    height: 10px;
    text-align: center;
}
QProgressBar::chunk { background-color: #89b4fa; border-radius: 4px; }
QSplitter::handle { background: #45475a; width: 2px; height: 2px; }
QStatusBar { background: #181825; color: #6c7086; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Solidarity - Artist Independence from AI Scraping - Based on HarmonyDagger")
        self.setMinimumSize(960, 640)
        self.setStyleSheet(_STYLE)

        self._worker: ProcessWorker | None = None
        self._setup_ui()
        self._initial_sized = False

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(10)

        # Header
        header = QLabel("Solidarity - Artist Independence from AI Scraping")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #89b4fa; padding-bottom: 2px;")
        subtitle = QLabel("Protect your audio against use by generative AI or unauthorized scraping.")
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px;")
        root.addWidget(header)
        root.addWidget(subtitle)

        # File panel
        self._file_panel = FilePanel()
        root.addWidget(self._file_panel)

        # Horizontal splitter: settings | log
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._settings_panel = SettingsPanel()
        splitter.addWidget(self._settings_panel)

        self._log_panel = LogPanel()
        splitter.addWidget(self._log_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, stretch=1)

        # Bottom bar: progress + button
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setFixedHeight(10)

        self._process_btn = QPushButton("Protect Audio")
        self._process_btn.setObjectName("processBtn")
        self._process_btn.setFixedHeight(42)
        self._process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._process_btn.clicked.connect(self._on_process)

        bottom.addWidget(self._progress, stretch=1)
        bottom.addWidget(self._process_btn)
        root.addLayout(bottom)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

    # ------------------------------------------------------------------
    def _on_process(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._process_btn.setText("Protect Audio")
            self._progress.setVisible(False)
            self._status_bar.showMessage("Cancelled")
            return

        input_paths = self._file_panel.input_paths()
        output_path = self._file_panel.output_path()

        if not input_paths:
            self._status_bar.showMessage("Please select an input file or folder first.")
            return

        params = self._settings_panel.get_params()
        params["inputs"] = input_paths
        params["output"] = output_path
        params["clobber"] = self._file_panel.clobber()

        self._log_panel.clear()
        self._log_panel.append_info(f"Starting: {', '.join(input_paths)}")

        self._process_btn.setText("Cancel")
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._status_bar.showMessage("Processing…")

        self._worker = ProcessWorker(params)
        self._worker.log_message.connect(self._log_panel.append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, success: bool, message: str):
        self._process_btn.setText("Protect Audio")
        self._progress.setRange(0, 1)
        self._progress.setValue(1 if success else 0)
        self._progress.setVisible(False)

        if success:
            self._log_panel.append_success(message)
            self._status_bar.showMessage(f"Done — {message}")
        else:
            self._log_panel.append_error(message)
            self._status_bar.showMessage(f"Failed — {message}")

    def showEvent(self, event):
        super().showEvent(event)
        if self._initial_sized:
            return
        self._initial_sized = True

        content_h = self._settings_panel.contentSizeHint().height()
        deficit = max(0, content_h - self._settings_panel.height())
        if deficit == 0:
            return

        available = self.screen().availableGeometry()
        new_h = min(self.height() + deficit, available.height() - 80)
        self.resize(self.width(), new_h)
