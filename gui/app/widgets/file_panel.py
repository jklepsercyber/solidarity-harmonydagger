"""File input/output selection panel with drag-and-drop support."""
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QFrame,
)
from .settings_panel import _CheckBox as _StyledCheckBox

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
QCheckBox { spacing: 8px; color: #6c7086; font-size: 12px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #45475a;
    border-radius: 3px;
    background: #313244;
}
QCheckBox::indicator:checked { background: #89b4fa; border-color: #89b4fa; }
"""

SUPPORTED_EXTS = {".wav", ".mp3", ".flac", ".ogg"}


class FilePanel(QWidget):
    """Input/output path pickers supporting single files, multi-file selection, and folders."""

    def __init__(self):
        super().__init__()
        self._paths: list[str] = []
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
        self._drop_hint = QLabel("Drop audio files or folders here")
        self._drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_hint.setStyleSheet("color: #6c7086; font-size: 13px;")
        dz_layout.addWidget(self._drop_hint)
        layout.addWidget(drop_zone)

        # Input row
        in_row = QHBoxLayout()
        in_label = QLabel("Input:")
        in_label.setFixedWidth(90)
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("Path to file(s) or folder  (WAV, MP3, FLAC, OGG)")
        self._input_edit.editingFinished.connect(self._on_input_edited)
        in_browse_files = QPushButton("Browse Files")
        in_browse_files.setObjectName("browseBtn")
        in_browse_files.clicked.connect(self._browse_files)
        in_browse_folder = QPushButton("Browse Folder")
        in_browse_folder.setObjectName("browseBtn")
        in_browse_folder.clicked.connect(self._browse_folder)
        in_row.addWidget(in_label)
        in_row.addWidget(self._input_edit)
        in_row.addWidget(in_browse_files)
        in_row.addWidget(in_browse_folder)
        layout.addLayout(in_row)

        # Output row
        out_row = QHBoxLayout()
        out_label = QLabel("Output:")
        out_label.setFixedWidth(90)
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText(
            "Optional — file: <input>_protected.ext  |  multi/folder: <input>/protected/"
        )
        out_browse = QPushButton("Browse")
        out_browse.setObjectName("browseBtn")
        out_browse.setFixedWidth(80)
        out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(out_label)
        out_row.addWidget(self._output_edit)
        out_row.addWidget(out_browse)
        layout.addLayout(out_row)

        # Clobber
        self._clobber_cb = _StyledCheckBox("Allow overwriting existing output files  (-c / --clobber)")
        self._clobber_cb.setToolTip(
            "When unchecked (default): collisions error out (single file) or skip the file (batch).\n"
            "When checked: existing output files are silently overwritten."
        )
        layout.addWidget(self._clobber_cb)

    # ------------------------------------------------------------------
    def _set_paths(self, paths: list[str]):
        self._paths = [p for p in paths if p]
        if not self._paths:
            self._input_edit.setText("")
            self._drop_hint.setText("Drop audio files or folders here")
            return

        if len(self._paths) == 1:
            p = Path(self._paths[0])
            self._input_edit.setText(self._paths[0])
            self._drop_hint.setText(f"Folder: {p.name}" if p.is_dir() else p.name)
        else:
            n_folders = sum(1 for p in self._paths if Path(p).is_dir())
            n_files = len(self._paths) - n_folders
            parts = []
            if n_files:
                parts.append(f"{n_files} file{'s' if n_files != 1 else ''}")
            if n_folders:
                parts.append(f"{n_folders} folder{'s' if n_folders != 1 else ''}")
            summary = ", ".join(parts) + " selected"
            self._input_edit.setText(f"<{summary}>")
            self._drop_hint.setText(summary)

    def _on_input_edited(self):
        text = self._input_edit.text().strip()
        if not text or text.startswith("<"):
            return
        self._set_paths([text])

    def _browse_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select audio files", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)",
        )
        if paths:
            self._set_paths(paths)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select folder")
        if path:
            self._set_paths([path])

    def _browse_output(self):
        is_multi = len(self._paths) > 1 or (
            len(self._paths) == 1 and Path(self._paths[0]).is_dir()
        )
        if is_multi:
            path = QFileDialog.getExistingDirectory(self, "Select output folder")
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save protected audio as", "",
                "WAV Files (*.wav);;FLAC Files (*.flac);;OGG Files (*.ogg)",
            )
        if path:
            self._output_edit.setText(path)

    def _drag_enter(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            self._set_paths([u.toLocalFile() for u in urls])

    # ------------------------------------------------------------------
    def input_paths(self) -> list[str]:
        return list(self._paths)

    def output_path(self) -> str:
        return self._output_edit.text().strip()

    def clobber(self) -> bool:
        return self._clobber_cb.isChecked()
