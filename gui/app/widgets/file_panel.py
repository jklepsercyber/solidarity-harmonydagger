"""File input/output selection panel with drag-and-drop support."""
from pathlib import Path

from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QFrame,
)

_PANEL_STYLE = """
QFrame#dropZone {
    border: 2px dashed #45475a;
    border-radius: 8px;
    background: #181825;
}
QFrame#dropZone:hover { border-color: #89b4fa; }
QLineEdit {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 10px;
    color: #cdd6f4;
}
QLineEdit:focus { border-color: #89b4fa; }
QPushButton#browseBtn {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 6px 14px;
    color: #89b4fa;
    font-weight: bold;
}
QPushButton#browseBtn:hover { background: #45475a; }
"""


class FilePanel(QWidget):
    """Input + output path pickers. Set batch_mode=True to pick folders."""

    def __init__(self, batch_mode: bool = False):
        super().__init__()
        self._batch = batch_mode
        self.setStyleSheet(_PANEL_STYLE)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Drop zone
        drop_zone = QFrame()
        drop_zone.setObjectName("dropZone")
        drop_zone.setFixedHeight(72)
        drop_zone.setAcceptDrops(True)
        drop_zone.dragEnterEvent = self._drag_enter
        drop_zone.dropEvent = self._drop
        dz_layout = QVBoxLayout(drop_zone)
        dz_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label = QLabel("Drop audio file here" if not self._batch else "Drop folder here")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("color: #6c7086; font-size: 13px;")
        self._drop_hint = icon_label
        dz_layout.addWidget(icon_label)
        layout.addWidget(drop_zone)

        # Input row
        in_row = QHBoxLayout()
        in_label = QLabel("Input:" if not self._batch else "Input folder:")
        in_label.setFixedWidth(90)
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText(
            "Path to audio file (WAV, MP3, FLAC, OGG)"
            if not self._batch
            else "Path to folder containing audio files"
        )
        in_browse = QPushButton("Browse")
        in_browse.setObjectName("browseBtn")
        in_browse.setFixedWidth(80)
        in_browse.clicked.connect(self._browse_input)
        in_row.addWidget(in_label)
        in_row.addWidget(self._input_edit)
        in_row.addWidget(in_browse)
        layout.addLayout(in_row)

        # Output row
        out_row = QHBoxLayout()
        out_label = QLabel("Output:" if not self._batch else "Output folder:")
        out_label.setFixedWidth(90)
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText(
            "Optional — defaults to <input>_protected.wav"
            if not self._batch
            else "Optional — defaults to <input>/protected/"
        )
        out_browse = QPushButton("Browse")
        out_browse.setObjectName("browseBtn")
        out_browse.setFixedWidth(80)
        out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(out_label)
        out_row.addWidget(self._output_edit)
        out_row.addWidget(out_browse)
        layout.addLayout(out_row)

    # ------------------------------------------------------------------
    def _browse_input(self):
        if self._batch:
            path = QFileDialog.getExistingDirectory(self, "Select input folder")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select audio file", "",
                "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)"
            )
        if path:
            self._input_edit.setText(path)
            self._drop_hint.setText(Path(path).name)

    def _browse_output(self):
        if self._batch:
            path = QFileDialog.getExistingDirectory(self, "Select output folder")
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save protected audio as", "",
                "WAV Files (*.wav);;FLAC Files (*.flac);;OGG Files (*.ogg)"
            )
        if path:
            self._output_edit.setText(path)

    def _drag_enter(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._input_edit.setText(path)
            self._drop_hint.setText(Path(path).name)

    # ------------------------------------------------------------------
    def input_path(self) -> str:
        return self._input_edit.text().strip()

    def output_path(self) -> str:
        return self._output_edit.text().strip()
