"""Main application window."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QLabel, QPushButton, QProgressBar,
    QTabWidget, QSizePolicy,
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
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 6px;
}
QTabBar::tab {
    background: #313244;
    color: #a6adc8;
    padding: 8px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
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
        self.setWindowTitle("HarmonyDagger — Audio AI Protection")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)
        self.setStyleSheet(_STYLE)

        self._worker: ProcessWorker | None = None
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(10)

        # Header
        header = QLabel("HarmonyDagger")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #89b4fa; padding-bottom: 2px;")
        subtitle = QLabel("Protect your audio against AI voice cloning and generative models")
        subtitle.setStyleSheet("color: #6c7086; font-size: 12px;")
        root.addWidget(header)
        root.addWidget(subtitle)

        # Tabs: Single File / Batch
        self._tabs = QTabWidget()
        root.addWidget(self._tabs, stretch=1)

        self._build_single_tab()
        self._build_batch_tab()

        # Bottom bar: progress + button
        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate initially
        self._progress.setRange(0, 1)  # hide until processing
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

    def _build_single_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._file_panel = FilePanel(batch_mode=False)
        layout.addWidget(self._file_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._settings_panel = SettingsPanel()
        splitter.addWidget(self._settings_panel)

        self._log_panel = LogPanel()
        splitter.addWidget(self._log_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, stretch=1)

        self._tabs.addTab(tab, "Single File")

    def _build_batch_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._batch_file_panel = FilePanel(batch_mode=True)
        layout.addWidget(self._batch_file_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._batch_settings_panel = SettingsPanel(show_batch_options=True)
        splitter.addWidget(self._batch_settings_panel)

        self._batch_log_panel = LogPanel()
        splitter.addWidget(self._batch_log_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, stretch=1)

        self._tabs.addTab(tab, "Batch Folder")

    # ------------------------------------------------------------------
    def _active_panels(self):
        if self._tabs.currentIndex() == 0:
            return self._file_panel, self._settings_panel, self._log_panel
        return self._batch_file_panel, self._batch_settings_panel, self._batch_log_panel

    def _on_process(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._process_btn.setText("Protect Audio")
            self._progress.setVisible(False)
            self._status_bar.showMessage("Cancelled")
            return

        file_panel, settings_panel, log_panel = self._active_panels()
        input_path = file_panel.input_path()
        output_path = file_panel.output_path()

        if not input_path:
            self._status_bar.showMessage("Please select an input file or folder first.")
            return

        params = settings_panel.get_params()
        params["input"] = input_path
        params["output"] = output_path
        params["batch"] = self._tabs.currentIndex() == 1

        log_panel.clear()
        log_panel.append_info(f"Starting processing: {input_path}")

        self._process_btn.setText("Cancel")
        self._progress.setRange(0, 0)  # indeterminate spinner
        self._progress.setVisible(True)
        self._status_bar.showMessage("Processing…")

        self._worker = ProcessWorker(params)
        self._worker.log_message.connect(log_panel.append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, success: bool, message: str):
        self._process_btn.setText("Protect Audio")
        self._progress.setRange(0, 1)
        self._progress.setValue(1 if success else 0)
        self._progress.setVisible(False)

        _, _, log_panel = self._active_panels()
        if success:
            log_panel.append_success(message)
            self._status_bar.showMessage(f"Done — {message}")
        else:
            log_panel.append_error(message)
            self._status_bar.showMessage(f"Failed — {message}")
