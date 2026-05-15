"""Protection settings panel — mirrors CLI parameters with README-sourced annotations."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QCheckBox, QSpinBox, QGroupBox,
    QScrollArea, QComboBox, QFrame,
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
    padding: 3px 6px;
    color: #cdd6f4;
    min-width: 70px;
}
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
    cb = QCheckBox(text)
    if tooltip:
        cb.setToolTip(tooltip)
    h.addWidget(cb)
    h.addStretch()
    if badge_text and badge_colors:
        h.addWidget(_badge(badge_text, badge_colors, badge_tooltip))
    return row, cb


def _slider_row(
    label: str,
    lo: int,
    hi: int,
    default: int,
    scale: float = 1.0,
    tooltip: str = "",
) -> tuple[QWidget, QSlider, QLabel]:
    """Labelled horizontal slider returning (container, slider, value_label)."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    lbl = QLabel(label)
    lbl.setMinimumWidth(130)
    if tooltip:
        lbl.setToolTip(tooltip)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(lo, hi)
    slider.setValue(default)
    if tooltip:
        slider.setToolTip(tooltip)
    val_lbl = QLabel(f"{default * scale:.2f}" if scale != 1.0 else str(default))
    val_lbl.setObjectName("valueLabel")
    val_lbl.setFixedWidth(42)
    val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _update(v):
        val_lbl.setText(f"{v * scale:.2f}" if scale != 1.0 else str(v))

    slider.valueChanged.connect(_update)
    h.addWidget(lbl)
    h.addWidget(slider)
    h.addWidget(val_lbl)
    return row, slider, val_lbl


def _note(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("annotNote")
    lbl.setWordWrap(True)
    return lbl


# ── Main widget ───────────────────────────────────────────────────────────────

class SettingsPanel(QWidget):
    def __init__(self, show_batch_options: bool = False):
        super().__init__()
        self._show_batch = show_batch_options
        self.setStyleSheet(_STYLE)
        self.setMinimumWidth(300)
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        v = QVBoxLayout(inner)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(10)

        # ── Protection Strength ──────────────────────────────────────────────
        grp1 = QGroupBox("Protection Strength")
        g1 = QVBoxLayout(grp1)

        # Noise scale — with "Recommended default" annotation at 0.10
        noise_hdr = QHBoxLayout()
        noise_hdr.addWidget(QLabel("Noise Scale"))
        noise_hdr.addStretch()
        noise_hdr.addWidget(
            _badge(
                "0.10 = Recommended default",
                _BADGE_DEF,
                "From README benchmarks: noise_scale=0.10 → ~26 dB SNR\n"
                "Light (0.05) to Strong (0.20) also available.",
            )
        )
        g1.addLayout(noise_hdr)

        noise_row, self._noise_slider, self._noise_val = _slider_row(
            "",
            lo=1, hi=50, default=10, scale=0.01,
            tooltip=(
                "Controls perturbation amplitude.\n"
                "0.01 → ~45 dB SNR (minimal)\n"
                "0.05 → ~32 dB SNR (light)\n"
                "0.10 → ~26 dB SNR (recommended default)\n"
                "0.20 → ~20 dB SNR (strong)"
            ),
        )
        # Highlight value label green when at the recommended default (10 ticks = 0.10)
        def _update_noise_color(v):
            color = "#a6e3a1" if v == 10 else "#89b4fa"
            self._noise_val.setStyleSheet(f"color:{color}; font-weight:bold;")

        self._noise_slider.valueChanged.connect(_update_noise_color)
        _update_noise_color(10)
        g1.addWidget(noise_row)

        # Benchmark row below noise slider showing SNR ranges
        snr_row = QHBoxLayout()
        for scale_txt, snr_txt, is_rec in [
            ("0.05", "~32 dB", False),
            ("0.10", "~26 dB ★", True),
            ("0.20", "~20 dB", False),
        ]:
            col = QVBoxLayout()
            sv = QLabel(scale_txt)
            sv.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sv.setStyleSheet(
                f"color:{'#a6e3a1' if is_rec else '#6c7086'}; font-size:10px;"
                + (" font-weight:bold;" if is_rec else "")
            )
            snr = QLabel(snr_txt)
            snr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            snr.setStyleSheet(
                f"color:{'#a6e3a1' if is_rec else '#6c7086'}; font-size:10px;"
                + (" font-weight:bold;" if is_rec else "")
            )
            col.addWidget(sv)
            col.addWidget(snr)
            snr_row.addLayout(col)
        g1.addLayout(snr_row)

        # Dry/Wet
        dw_row, self._drywet_slider, _ = _slider_row(
            "Dry / Wet Mix",
            lo=0, hi=100, default=100, scale=0.01,
            tooltip="0.0 = original audio unchanged  |  1.0 = fully protected (default)",
        )
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
            "Combine all three below for full protection — as shown in the README "
            '"Full protection with all techniques" example.'
        )
        full_note.setStyleSheet(
            "color:#89b4fa; font-size:11px; "
            "background:#1a2d4a; border-radius:4px; padding:5px 8px;"
        )
        g2.addWidget(full_note)

        row, self._vocal = _checkbox_row(
            "Vocal Mode  (optimizes 300 Hz – 3 kHz)",
            tooltip=(
                "Targets AI voice cloning specifically.\n"
                "README: 'Vocal-Specific Mode: Optimized protection for the human vocal range'"
            ),
            badge_text="Full Protection",
            badge_colors=_BADGE_FULL,
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
                "Subtle phase shifts that confuse AI models.\n"
                "README: 'Phase Perturbation: Subtle phase shifts that disrupt AI feature extraction'"
            ),
            badge_text="Full Protection",
            badge_colors=_BADGE_FULL,
            badge_tooltip=(
                "Part of the README full-protection combo:\n"
                "  harmonydagger input.wav -o output.wav -n 0.1 -a --phase --temporal-masking --vocal-mode"
            ),
        )
        g2.addWidget(row)

        row, self._temporal = _checkbox_row(
            "Temporal Masking  (exploits auditory post-masking)",
            tooltip=(
                "Hides extra perturbations in the temporal shadow of loud events.\n"
                "README: 'Temporal Forward Masking: Exploits post-masking effects'"
            ),
            badge_text="Full Protection",
            badge_colors=_BADGE_FULL,
            badge_tooltip=(
                "Part of the README full-protection combo:\n"
                "  harmonydagger input.wav -o output.wav -n 0.1 -a --phase --temporal-masking --vocal-mode"
            ),
        )
        g2.addWidget(row)

        row, self._ensemble = _checkbox_row(
            "Ensemble Mode  (targets multiple AI architectures)",
            tooltip="Applies several perturbation strategies in combination.",
        )
        g2.addWidget(row)

        v.addWidget(grp2)

        # ── Advanced ─────────────────────────────────────────────────────────
        grp3 = QGroupBox("Advanced")
        g3 = QVBoxLayout(grp3)

        win_row = QHBoxLayout()
        win_lbl = QLabel("Window Size")
        win_lbl.setToolTip(
            "STFT window size.\n"
            "README default: 2048  (used in all examples and the Python API)"
        )
        win_row.addWidget(win_lbl)
        self._window_spin = QSpinBox()
        self._window_spin.setRange(256, 8192)
        self._window_spin.setSingleStep(256)
        self._window_spin.setValue(2048)
        self._window_spin.setToolTip("README default: 2048")
        win_row.addWidget(self._window_spin)
        win_row.addWidget(
            _badge("Default: 2048", _BADGE_DEF, "All README examples use window_size=2048")
        )
        g3.addLayout(win_row)

        hop_row = QHBoxLayout()
        hop_lbl = QLabel("Hop Size")
        hop_lbl.setToolTip(
            "STFT hop size.\n"
            "README default: 512  (used in all examples and the Python API)"
        )
        hop_row.addWidget(hop_lbl)
        self._hop_spin = QSpinBox()
        self._hop_spin.setRange(64, 2048)
        self._hop_spin.setSingleStep(64)
        self._hop_spin.setValue(512)
        self._hop_spin.setToolTip("README default: 512")
        hop_row.addWidget(self._hop_spin)
        hop_row.addWidget(
            _badge("Default: 512", _BADGE_DEF, "All README examples use hop_size=512")
        )
        g3.addLayout(hop_row)

        row, self._force_mono = _checkbox_row(
            "Force Mono  (convert stereo → mono)",
            tooltip="Use if your files are stereo and you want single-channel output.",
        )
        g3.addWidget(row)

        row, self._gpu = _checkbox_row(
            "GPU Acceleration  (requires PyTorch + CUDA)",
            tooltip="Requires: pip install torch\nSee README for installation.",
        )
        g3.addWidget(row)

        v.addWidget(grp3)

        # ── Post-Processing Analysis ──────────────────────────────────────────
        grp4 = QGroupBox("Post-Processing Analysis")
        g4 = QVBoxLayout(grp4)
        g4.addWidget(
            _note('README example: "Process with robustness check and verification"\n'
                  '  harmonydagger input.wav -n 0.1 -a --robust --verify --benchmark -v')
        )

        row, self._benchmark = _checkbox_row(
            "Benchmark  (SNR + perturbation metrics)",
            tooltip="Shows SNR (dB) and perturbation ratio after processing.",
        )
        g4.addWidget(row)

        row, self._verify = _checkbox_row(
            "Verification  (protection score + MFCC similarity)",
            tooltip="Measures how effectively AI features are disrupted.",
        )
        g4.addWidget(row)

        row, self._robust = _checkbox_row(
            "Robustness Test  (MP3, filtering, resampling survival)",
            tooltip=(
                "Tests whether the perturbation survives common transforms.\n"
                "Requires ffmpeg for MP3 robustness testing."
            ),
        )
        g4.addWidget(row)

        v.addWidget(grp4)

        # ── Batch Options ─────────────────────────────────────────────────────
        if self._show_batch:
            grp5 = QGroupBox("Batch Options")
            g5 = QVBoxLayout(grp5)

            fmt_row = QHBoxLayout()
            fmt_row.addWidget(QLabel("Format filter"))
            self._fmt_combo = QComboBox()
            self._fmt_combo.addItems(["all", "wav", "mp3", "flac", "ogg"])
            self._fmt_combo.setToolTip(
                "README: 'Process only MP3 files'  →  -f mp3\n"
                "'all' processes WAV, MP3, FLAC and OGG."
            )
            fmt_row.addWidget(self._fmt_combo)
            g5.addLayout(fmt_row)

            jobs_row = QHBoxLayout()
            jobs_row.addWidget(QLabel("Parallel jobs"))
            self._jobs_spin = QSpinBox()
            self._jobs_spin.setRange(1, 16)
            self._jobs_spin.setValue(1)
            self._jobs_spin.setToolTip(
                "README example: -j 4 for 4 parallel workers.\n"
                "Capped at your CPU core count automatically."
            )
            jobs_row.addWidget(self._jobs_spin)
            jobs_row.addWidget(
                _badge(
                    "README: -j 4",
                    _BADGE_REC,
                    "README batch example uses -j 4 parallel jobs",
                )
            )
            g5.addLayout(jobs_row)

            v.addWidget(grp5)

        v.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
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
        }
        if self._show_batch:
            params["format"] = self._fmt_combo.currentText()
            params["jobs"] = self._jobs_spin.value()
        return params
