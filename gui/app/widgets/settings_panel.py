"""Protection settings panel — mirrors CLI parameters with README-sourced annotations."""
from PyQt6.QtCore import Qt, QPointF, QRect
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSlider, QCheckBox, QSpinBox, QGroupBox,
    QScrollArea, QFrame, QToolButton,
    QStyle, QStyleOptionButton, QStyleOptionSlider,
)

# ── Badge colour tokens ────────────────────────────────────────────────────────
# Green  — universally recommended in every README example
_BADGE_REC   = ("#1e3a2f", "#a6e3a1")   # bg, fg
# Blue   — part of the "full protection" trio  (phase + temporal + vocal)
_BADGE_FULL  = ("#1a2d4a", "#89b4fa")
# Amber  — default values highlighted on the noise scale
_BADGE_DEF   = ("#3a2e1a", "#f9e2af")

_STYLE = """
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 6px;
    color: #89b4fa;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #45475a;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #89b4fa;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #89b4fa; border-radius: 2px; }
QSlider[annotated="true"] { padding-left: 22px; padding-right: 22px; }
QCheckBox { spacing: 8px; color: #cdd6f4; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #45475a;
    border-radius: 3px;
    background: #313244;
}
QCheckBox::indicator:checked { background: #89b4fa; border-color: #89b4fa; }
QSpinBox {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 3px 22px 3px 6px;
    color: #cdd6f4;
    min-width: 70px;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #45475a;
    border-top-right-radius: 3px;
    background: #45475a;
}
QSpinBox::up-button:hover { background: #585b70; }
QSpinBox::up-button:pressed { background: #89b4fa; }
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid #45475a;
    border-bottom-right-radius: 3px;
    background: #45475a;
}
QSpinBox::down-button:hover { background: #585b70; }
QSpinBox::down-button:pressed { background: #89b4fa; }
QComboBox {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    color: #cdd6f4;
}
QComboBox::drop-down { border: none; }
QLabel { color: #cdd6f4; }
QLabel#valueLabel { color: #89b4fa; font-weight: bold; min-width: 40px; }
QLabel#annotNote { color: #6c7086; font-size: 11px; padding-left: 2px; }
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _badge(text: str, colors: tuple[str, str], tooltip: str = "") -> QLabel:
    """Small pill-shaped annotation label."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{colors[0]}; color:{colors[1]};"
        "border-radius:4px; padding:1px 7px;"
        "font-size:10px; font-weight:bold;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if tooltip:
        lbl.setToolTip(tooltip)
    return lbl


class _CheckBox(QCheckBox):
    """QCheckBox that paints a ✓ mark inside the indicator when checked."""

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isChecked():
            return
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        r = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, opt, self
        )
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#1e1e2e"), 1.8, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        mid = QPointF(x + w * 0.42, y + h * 0.72)
        painter.drawLine(QPointF(x + w * 0.20, y + h * 0.50), mid)
        painter.drawLine(mid, QPointF(x + w * 0.80, y + h * 0.24))
        painter.end()


def _checkbox_row(
    text: str,
    tooltip: str = "",
    badge_text: str = "",
    badge_colors: tuple[str, str] | None = None,
    badge_tooltip: str = "",
) -> tuple[QWidget, QCheckBox]:
    """Checkbox with an optional right-aligned badge."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 2, 0, 2)
    h.setSpacing(6)
    cb = _CheckBox(text)
    if tooltip:
        cb.setToolTip(tooltip)
    h.addWidget(cb)
    h.addStretch()
    if badge_text and badge_colors:
        h.addWidget(_badge(badge_text, badge_colors, badge_tooltip))
    return row, cb


class _AnnotatedSlider(QSlider):
    """Horizontal slider that paints coloured tick marks at specified values.

    ticks: list of (value, label, colour_hex) drawn below the groove.
    """

    # Half the handle width from QSS — used to align ticks with the groove ends.
    _HALF_HANDLE = 7

    def __init__(self, ticks: list[tuple[int, str, str]]):
        super().__init__(Qt.Orientation.Horizontal)
        self._tick_marks = ticks
        if ticks:
            self.setProperty("annotated", True)

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(hint.height() + 20)   # room for tick line + label
        return hint

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setHeight(hint.height() + 20)
        return hint

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._tick_marks:
            return

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self,
        )

        # Groove usable range excludes the half-handle overhang on each side
        g_left  = groove.left()  + self._HALF_HANDLE
        g_right = groove.right() - self._HALF_HANDLE
        g_width = g_right - g_left
        if g_width <= 0:
            return

        tick_top   = groove.bottom() + 4
        tick_bot   = tick_top + 6
        label_top  = tick_bot + 1

        span = self.maximum() - self.minimum()
        if span == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for value, label, colour in self._tick_marks:
            ratio = (value - self.minimum()) / span
            x = g_left + int(ratio * g_width)

            pen = QPen(QColor(colour), 2, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(x, tick_top, x, tick_bot)

            if label:
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)
                painter.setPen(QColor(colour))
                painter.drawText(
                    QRect(x - 22, label_top, 44, 13),
                    Qt.AlignmentFlag.AlignCenter,
                    label,
                )

        painter.end()

    def wheelEvent(self, event):
        event.ignore()  # let the scroll area handle the wheel, not the slider


def _slider_row(
    label: str,
    lo: int,
    hi: int,
    default: int,
    scale: float = 1.0,
    tooltip: str = "",
    ticks: list[tuple[int, str, str]] | None = None,
    editable: bool = False,
) -> tuple[QWidget, QSlider, QLabel | QLineEdit]:
    """Labelled horizontal slider returning (container, slider, value_widget)."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    lbl = QLabel(label)
    lbl.setMinimumWidth(130)
    if tooltip:
        lbl.setToolTip(tooltip)

    slider = _AnnotatedSlider(ticks or [])
    slider.setRange(lo, hi)
    slider.setValue(default)
    if tooltip:
        slider.setToolTip(tooltip)

    if editable:
        lo_f, hi_f = lo * scale, hi * scale
        val_widget = QLineEdit(f"{default * scale:.2f}")
        val_widget.setFixedWidth(55)
        val_widget.setAlignment(Qt.AlignmentFlag.AlignRight)
        val_widget.setStyleSheet(
            "background:#313244; border:1px solid #45475a; border-radius:4px;"
            "padding:2px 5px; color:#89b4fa; font-weight:bold;"
        )
        def _update(v):
            val_widget.setText(f"{v * scale:.2f}")

        def _on_edit_finished():
            text = val_widget.text().strip()
            try:
                val = float(text)
            except ValueError:
                val_widget.setText(f"{slider.value() * scale:.2f}")
                return
            val = max(lo_f, min(hi_f, val))
            slider.setValue(round(val / scale))
            val_widget.setText(f"{slider.value() * scale:.2f}")

        slider.valueChanged.connect(_update)
        val_widget.editingFinished.connect(_on_edit_finished)
    else:
        val_widget = QLabel(f"{default * scale:.2f}" if scale != 1.0 else str(default))
        val_widget.setObjectName("valueLabel")
        val_widget.setFixedWidth(42)
        val_widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def _update(v):
            val_widget.setText(f"{v * scale:.2f}" if scale != 1.0 else str(v))

        slider.valueChanged.connect(_update)

    h.addWidget(lbl)
    h.addWidget(slider)
    h.addWidget(val_widget)
    return row, slider, val_widget


def _note(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("annotNote")
    lbl.setWordWrap(True)
    return lbl


class _CollapsibleSection(QWidget):
    """A titled section whose content can be toggled open/closed with an arrow."""

    def __init__(self, title: str, collapsed: bool = True, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._toggle = QToolButton()
        self._toggle.setCheckable(True)
        self._toggle.setChecked(not collapsed)
        self._toggle.setText(f"  {title}")
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(
            Qt.ArrowType.RightArrow if collapsed else Qt.ArrowType.DownArrow
        )
        self._toggle.setSizePolicy(
            self._toggle.sizePolicy().horizontalPolicy(),
            self._toggle.sizePolicy().verticalPolicy(),
        )
        self._toggle.setStyleSheet("""
            QToolButton {
                border: 1px solid #45475a;
                border-radius: 6px;
                background: #313244;
                color: #89b4fa;
                font-weight: bold;
                font-size: 13px;
                padding: 6px 10px;
                text-align: left;
                width: 100%;
            }
            QToolButton:checked {
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }
            QToolButton:hover { background: #45475a; }
        """)
        self._toggle.clicked.connect(self._on_toggle)
        outer.addWidget(self._toggle)

        self._body = QFrame()
        self._body.setObjectName("collapsibleBody")
        self._body.setStyleSheet(
            "QFrame#collapsibleBody { border: 1px solid #45475a; border-top: none;"
            "border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }"
        )
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(10, 8, 10, 8)
        self._body_layout.setSpacing(6)
        self._body.setVisible(not collapsed)
        outer.addWidget(self._body)

    def _on_toggle(self, checked: bool):
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        self._body.setVisible(checked)

    def addWidget(self, widget):
        self._body_layout.addWidget(widget)

    def addLayout(self, layout):
        self._body_layout.addLayout(layout)


# ── Main widget ───────────────────────────────────────────────────────────────

class SettingsPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(_STYLE)
        self.setMinimumWidth(300)
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        self._scroll_inner = inner          # exposed for window auto-sizing
        inner.setStyleSheet("background: transparent;")
        v = QVBoxLayout(inner)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(10)

        # ── Protection Strength ──────────────────────────────────────────────
        grp1 = QGroupBox("Protection Strength")
        g1 = QVBoxLayout(grp1)

        full_note = _note(
            "Hover over each slider to learn more about each setting."
        )
        full_note.setStyleSheet(
            "color:#89b4fa; font-size:11px; "
            "background:#1a2d4a; border-radius:4px; padding:5px 8px;"
        )
        g1.addWidget(full_note)

        noise_row, self._noise_slider, self._noise_val = _slider_row(
            "Signal-to-Noise Ratio",
            lo=0, hi=20, default=10, scale=0.01,
            tooltip=(
                "Controls perturbation amplitude.\n"
                "0.00 → no protection\n"
                "0.05 → ~32 dB SNR (light)\n"
                "0.10 → ~26 dB SNR (recommended default)\n"
                "0.20 → ~20 dB SNR (strong)"
            ),
            ticks=[
                (5,  "0.05", "#6c7086"),
                (10, "★0.10", "#a6e3a1"),
                (20, "0.20", "#6c7086"),
            ],
            editable=True,
        )
        # Highlight the editable field green when at the recommended default
        _base_edit_style = (
            "background:#313244; border:1px solid #45475a; border-radius:4px;"
            "padding:2px 5px; font-weight:bold;"
        )
        def _update_noise_color(v):
            color = "#a6e3a1" if v == 10 else "#89b4fa"
            self._noise_val.setStyleSheet(f"{_base_edit_style} color:{color};")

        self._noise_slider.valueChanged.connect(_update_noise_color)
        _update_noise_color(10)
        g1.addWidget(noise_row)

        # Benchmark row below noise slider showing SNR ranges
        # snr_row = QHBoxLayout()
        # for scale_txt, snr_txt, is_rec in [
        #     ("0.05", "~32 dB", False),
        #     ("0.10", "~26 dB ★", True),
        #     ("0.20", "~20 dB", False),
        # ]:
        #     col = QVBoxLayout()
        #     sv = QLabel(scale_txt)
        #     sv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #     sv.setStyleSheet(
        #         f"color:{'#a6e3a1' if is_rec else '#6c7086'}; font-size:10px;"
        #         + (" font-weight:bold;" if is_rec else "")
        #     )
        #     snr = QLabel(snr_txt)
        #     snr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #     snr.setStyleSheet(
        #         f"color:{'#a6e3a1' if is_rec else '#6c7086'}; font-size:10px;"
        #         + (" font-weight:bold;" if is_rec else "")
        #     )
        #     col.addWidget(sv)
        #     col.addWidget(snr)
        #     snr_row.addLayout(col)
        # g1.addLayout(snr_row)

        # Dry/Wet
        dw_row, self._drywet_slider, self._drywet_val = _slider_row(
            "Dry / Wet Mix",
            lo=0, hi=100, default=100, scale=0.01,
            tooltip="0.0 = original audio unchanged  |  1.0 = fully protected (default)",
            ticks=[
                (70,  "0.70", "#6c7086"),
                (100, "★1.0", "#a6e3a1"),
            ],
            editable=True,
        )
        def _update_drywet_color(v):
            color = "#a6e3a1" if v == 100 else "#89b4fa"
            self._drywet_val.setStyleSheet(f"{_base_edit_style} color:{color};")

        self._drywet_slider.valueChanged.connect(_update_drywet_color)
        _update_drywet_color(100)
        g1.addWidget(dw_row)

        # Adaptive scaling — recommended
        row, self._adaptive = _checkbox_row(
            "Adaptive Scaling  (auto-adjusts to signal)",
            tooltip="Used in every README example: harmonydagger input.wav -n 0.1 -a",
            badge_text="★ Recommended",
            badge_colors=_BADGE_REC,
            badge_tooltip=(
                "Every CLI example in the README uses -a / --adaptive-scaling.\n"
                "Adjusts noise to the local signal strength automatically."
            ),
        )
        self._adaptive.setChecked(True)
        g1.addWidget(row)

        v.addWidget(grp1)

        # ── Enhancement Modes ────────────────────────────────────────────────
        grp2 = QGroupBox("Enhancement Modes")
        g2 = QVBoxLayout(grp2)

        full_note = _note(
            "Hover over each tickbox to learn more about each mode."
        )
        full_note.setStyleSheet(
            "color:#89b4fa; font-size:11px; "
            "background:#1a2d4a; border-radius:4px; padding:5px 8px;"
        )
        g2.addWidget(full_note)

        row, self._ensemble = _checkbox_row(
            "Ensemble Mode  (targets multiple AI architectures)",
            tooltip=(
                "Applies several perturbation strategies in combination."
            ),
            badge_text="★ Recommended",
            badge_colors=_BADGE_REC,
        )
        g2.addWidget(row)
        g2.addSpacing(12)

        full_note = _note(
            "Combine all three below for full protection — as shown in the README "
            '"Full protection with all techniques" example.'
        )
        full_note.setStyleSheet(
            "color:#a6e3a1; font-size:11px; "
            "background:#1e3a2f; border-radius:4px; padding:5px 8px;"
        )
        g2.addWidget(full_note)

        row, self._vocal = _checkbox_row(
            "Vocal-Specific Mode  (optimizes 300 Hz – 3 kHz)",
            tooltip=(
                "Targets AI voice cloning specifically."
            ),
            badge_text="★ Recommended",
            badge_colors=_BADGE_REC,
            badge_tooltip=(
                "Part of the README full-protection combo:\n"
                "  -n 0.1 -a --phase --temporal-masking --vocal-mode\n"
                "Also enabled in the Python API example."
            ),
        )
        g2.addWidget(row)

        row, self._phase = _checkbox_row(
            "Phase Perturbation  (disrupts AI feature extraction)",
            tooltip=(
                "Subtle phase shifts that disrupt AI feature extraction while remaining imperceptible."
            ),
            badge_text="★ Recommended",
            badge_colors=_BADGE_REC,
            badge_tooltip=(
                "Part of the README full-protection combo:\n"
                "  harmonydagger input.wav -o output.wav -n 0.1 -a --phase --temporal-masking --vocal-mode"
            ),
        )
        g2.addWidget(row)

        row, self._temporal = _checkbox_row(
            "Temporal Masking  (exploits auditory post-masking)",
            tooltip=(
                "Exploits post-masking effects to insert further imperceptible noise after spikes in the input file's amplitude."\
            ),
            badge_text="★ Recommended",
            badge_colors=_BADGE_REC,
            badge_tooltip=(
                "Part of the README full-protection combo:\n"
                "  harmonydagger input.wav -o output.wav -n 0.1 -a --phase --temporal-masking --vocal-mode"
            ),
        )
        g2.addWidget(row)

        v.addWidget(grp2)

        # ── Visualization Options ─────────────────────────────────────────────
        grp_vis = QGroupBox("Visualization Options")
        g_vis = QVBoxLayout(grp_vis)
        g_vis.addWidget(
            _note(
                "Saves spectrogram images alongside the output file.\n"
                "Requires matplotlib — pip install matplotlib"
            )
        )

        row, self._visualize = _checkbox_row(
            "Spectrogram comparison  (--visualize)",
            tooltip="Saves a side-by-side spectrogram of the original and protected audio.",
        )
        g_vis.addWidget(row)

        row, self._visualize_diff = _checkbox_row(
            "Difference visualization  (--visualize_diff)",
            tooltip="Saves a heatmap of the perturbation added to the audio.",
        )
        g_vis.addWidget(row)

        v.addWidget(grp_vis)

        # ── Post-Processing Analysis ──────────────────────────────────────────
        grp3 = QGroupBox("Post-Processing Analysis")
        g3 = QVBoxLayout(grp3)
        g3.addWidget(
            _note('README example: "Process with robustness check and verification"\n'
                  '  harmonydagger input.wav -n 0.1 -a --robust --verify --benchmark -v')
        )

        row, self._benchmark = _checkbox_row(
            "Benchmark  (SNR + perturbation metrics)",
            tooltip="Shows SNR (dB) and perturbation ratio after processing.",
        )
        g3.addWidget(row)

        row, self._verify = _checkbox_row(
            "Verification  (protection score + MFCC similarity)",
            tooltip="Measures how effectively AI features are disrupted.",
        )
        g3.addWidget(row)

        row, self._robust = _checkbox_row(
            "Robustness Test  (MP3, filtering, resampling survival)",
            tooltip=(
                "Tests whether the perturbation survives common transforms.\n"
                "Requires ffmpeg for MP3 robustness testing."
            ),
        )
        g3.addWidget(row)

        v.addWidget(grp3)

        # ── Advanced (collapsible, starts closed) ────────────────────────────
        adv = _CollapsibleSection("Advanced", collapsed=True)

        win_row = QHBoxLayout()
        win_lbl = QLabel("STFT Window Size")
        win_lbl.setFixedWidth(140)
        win_lbl.setToolTip(
            "STFT window size.\n"
            "README default: 2048  (used in all examples and the Python API)"
        )
        win_row.addWidget(win_lbl)
        self._window_spin = QSpinBox()
        self._window_spin.setRange(256, 8192)
        self._window_spin.setSingleStep(256)
        self._window_spin.setValue(2048)
        self._window_spin.setFixedWidth(80)
        self._window_spin.setToolTip("README default: 2048")
        win_row.addWidget(self._window_spin)
        win_row.addWidget(
            _badge("Default: 2048", _BADGE_DEF, "All README examples use window_size=2048")
        )
        win_row.addStretch()
        adv.addLayout(win_row)

        hop_row = QHBoxLayout()
        hop_lbl = QLabel("STFT Hop Size")
        hop_lbl.setFixedWidth(140)
        hop_lbl.setToolTip(
            "STFT hop size.\n"
            "README default: 512  (used in all examples and the Python API)"
        )
        hop_row.addWidget(hop_lbl)
        self._hop_spin = QSpinBox()
        self._hop_spin.setRange(64, 2048)
        self._hop_spin.setSingleStep(64)
        self._hop_spin.setValue(512)
        self._hop_spin.setFixedWidth(80)
        self._hop_spin.setToolTip("README default: 512")
        hop_row.addWidget(self._hop_spin)
        hop_row.addWidget(
            _badge("Default: 512", _BADGE_DEF, "All README examples use hop_size=512")
        )
        hop_row.addStretch()
        adv.addLayout(hop_row)

        row, self._force_mono = _checkbox_row(
            "Force Mono  (convert stereo → mono)",
            tooltip="Use if your files are stereo and you want single-channel output.",
        )
        adv.addWidget(row)

        row, self._gpu = _checkbox_row(
            "GPU Acceleration  (requires PyTorch + CUDA)",
            tooltip="Requires: pip install torch\nSee README for installation.",
        )
        adv.addWidget(row)

        row, self._recursive = _checkbox_row(
            "Recursive folder processing",
            tooltip=(
                "When a folder is given as input, also process audio files in sub-folders.\n"
                "Only WAV, MP3, FLAC, and OGG files are included."
            ),
        )
        adv.addWidget(row)

        jobs_row = QHBoxLayout()
        jobs_lbl = QLabel("Parallel jobs")
        jobs_lbl.setFixedWidth(140)
        jobs_lbl.setToolTip(
            "Number of parallel workers for multi-file and folder processing.\n"
            "README example: -j 4  |  capped at your CPU core count."
        )
        jobs_row.addWidget(jobs_lbl)
        self._jobs_spin = QSpinBox()
        self._jobs_spin.setRange(1, 16)
        self._jobs_spin.setValue(1)
        self._jobs_spin.setFixedWidth(80)
        self._jobs_spin.setToolTip("Applies when processing more than one file.")
        jobs_row.addWidget(self._jobs_spin)
        jobs_row.addStretch()
        adv.addLayout(jobs_row)

        v.addWidget(adv)

        v.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    def contentSizeHint(self):
        """Full preferred size of the scroll content — bypasses QScrollArea's capped hint."""
        return self._scroll_inner.sizeHint()

    def get_params(self) -> dict:
        params = {
            "noise_scale": self._noise_slider.value() * 0.01,
            "dry_wet": self._drywet_slider.value() * 0.01,
            "adaptive_scaling": self._adaptive.isChecked(),
            "vocal_mode": self._vocal.isChecked(),
            "use_phase_perturbation": self._phase.isChecked(),
            "use_temporal_masking": self._temporal.isChecked(),
            "use_ensemble": self._ensemble.isChecked(),
            "window_size": self._window_spin.value(),
            "hop_size": self._hop_spin.value(),
            "force_mono": self._force_mono.isChecked(),
            "use_gpu": self._gpu.isChecked(),
            "benchmark": self._benchmark.isChecked(),
            "verify": self._verify.isChecked(),
            "robust": self._robust.isChecked(),
            "visualize": self._visualize.isChecked(),
            "visualize_diff": self._visualize_diff.isChecked(),
            "recursive": self._recursive.isChecked(),
            "jobs": self._jobs_spin.value(),
        }
        return params
