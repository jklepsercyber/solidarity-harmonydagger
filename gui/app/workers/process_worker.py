"""Background QThread that runs HarmonyDagger processing without freezing the UI."""
import logging
import time
from pathlib import Path

import numpy as np

from PyQt6.QtCore import QThread, pyqtSignal

from ..widgets.file_panel import SUPPORTED_EXTS


class _QtLogHandler(logging.Handler):
    """Forwards Python log records to a Qt signal."""

    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))

    def emit(self, record: logging.LogRecord):
        self.signal.emit(self.format(record))


class ProcessWorker(QThread):
    """
    Runs process_audio_file (single or batch) in a background thread.

    Signals
    -------
    log_message : str
        Log lines to display in LogPanel.
    finished : (bool, str)
        True + summary on success; False + error on failure.
    """

    log_message: pyqtSignal = pyqtSignal(str)
    finished: pyqtSignal = pyqtSignal(bool, str)

    def __init__(self, params: dict):
        super().__init__()
        self._params = params

    # ------------------------------------------------------------------
    def run(self):
        p = self._params
        raw_inputs: list[str] = p["inputs"]
        output_path = Path(p["output"]) if p.get("output") else None
        recursive: bool = p.get("recursive", False)

        handler = _QtLogHandler(self.log_message)
        pkg_logger = logging.getLogger("harmonydagger")
        pkg_logger.addHandler(handler)
        pkg_logger.setLevel(logging.DEBUG)
        logging.captureWarnings(True)
        warnings_logger = logging.getLogger("py.warnings")
        warnings_logger.addHandler(handler)

        try:
            # Expand inputs → flat list of audio files
            audio_files: list[Path] = []
            for raw in raw_inputs:
                path = Path(raw)
                if path.is_dir():
                    audio_files.extend(self._collect_dir(path, recursive))
                elif path.is_file():
                    audio_files.append(path)
                else:
                    self.log_message.emit(f"WARNING  Path not found, skipping: {raw}")

            if not audio_files:
                self.finished.emit(False, "No supported audio files found in the given input(s)")
                return

            cmd = self._build_cli_command(p, raw_inputs, output_path, recursive)
            self.log_message.emit(f"CMD   {cmd}")

            if len(audio_files) == 1:
                self._run_single(audio_files[0], output_path, p)
            else:
                self._run_batch(audio_files, output_path, p)

        except Exception as exc:
            self.finished.emit(False, str(exc))
        finally:
            pkg_logger.removeHandler(handler)
            warnings_logger.removeHandler(handler)
            logging.captureWarnings(False)

    # ------------------------------------------------------------------
    @staticmethod
    def _collect_dir(directory: Path, recursive: bool) -> list[Path]:
        results: list[Path] = []
        glob = directory.rglob if recursive else directory.glob
        for ext in SUPPORTED_EXTS:
            results.extend(glob(f"*{ext}"))
            results.extend(glob(f"*{ext.upper()}"))
        return results

    # ------------------------------------------------------------------
    @staticmethod
    def _build_cli_command(
        p: dict,
        raw_inputs: list[str],
        output_path: Path | None,
        recursive: bool,
    ) -> str:
        flags: list[str] = []
        if output_path:
            flags += ["-o", f'"{output_path}"']
        flags += ["-n", f"{p['noise_scale']:.2f}"]
        if p.get("dry_wet", 1.0) != 1.0:
            flags += ["-d", f"{p['dry_wet']:.2f}"]
        if p.get("adaptive_scaling"):
            flags.append("-a")
        if p.get("vocal_mode"):
            flags.append("--vocal-mode")
        if p.get("use_phase_perturbation"):
            flags.append("--phase")
        if p.get("use_temporal_masking"):
            flags.append("--temporal-masking")
        if p.get("use_ensemble"):
            flags.append("--ensemble")
        if p.get("use_gpu"):
            flags.append("--gpu")
        if p.get("window_size", 2048) != 2048:
            flags += ["-w", str(p["window_size"])]
        if p.get("hop_size", 512) != 512:
            flags += ["-s", str(p["hop_size"])]
        if p.get("force_mono"):
            flags.append("--force-mono")
        if p.get("clobber"):
            flags.append("-c")
        if recursive:
            flags.append("--recursive")
        if p.get("jobs", 1) > 1:
            flags += ["-j", str(p["jobs"])]
        if p.get("visualize"):
            flags.append("--visualize")
        if p.get("visualize_diff"):
            flags.append("--visualize_diff")
        if p.get("benchmark"):
            flags.append("--benchmark")
        if p.get("verify"):
            flags.append("--verify")
        if p.get("robust"):
            flags.append("--robust")

        flags_str = " ".join(flags)
        if len(raw_inputs) == 1:
            return f'harmonydagger "{raw_inputs[0]}" {flags_str}'.strip()
        extra = len(raw_inputs) - 1
        return f'harmonydagger "{raw_inputs[0]}" {flags_str}  # (+{extra} more input{"s" if extra != 1 else ""})'.strip()

    # ------------------------------------------------------------------
    def _run_single(self, input_path: Path, output_path: Path | None, p: dict):
        from harmonydagger.file_operations import process_audio_file

        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_protected{input_path.suffix}"

        if output_path.exists() and not p.get("clobber", False):
            self.finished.emit(False, f"Output file already exists: {output_path} — enable Clobber to overwrite")
            return

        success, out, elapsed = process_audio_file(
            str(input_path),
            str(output_path),
            window_size=p["window_size"],
            hop_size=p["hop_size"],
            noise_scale=p["noise_scale"],
            adaptive_scaling=p["adaptive_scaling"],
            force_mono=p["force_mono"],
            dry_wet=p["dry_wet"],
            vocal_mode=p["vocal_mode"],
            use_phase_perturbation=p["use_phase_perturbation"],
            use_temporal_masking=p["use_temporal_masking"],
            use_ensemble=p["use_ensemble"],
            use_gpu=p["use_gpu"],
            visualize=p.get("visualize", False),
            visualize_diff=p.get("visualize_diff", False),
            visualization_path=str(output_path.parent),
        )

        if not success:
            self.finished.emit(False, f"Processing failed: {out}")
            return

        self.log_message.emit(f"INFO  Saved → {out}  ({elapsed:.2f}s)")
        self._run_analysis(p, input_path, Path(out))
        self.finished.emit(True, f"Saved to {out}")

    # ------------------------------------------------------------------
    def _run_batch(self, audio_files: list[Path], output_dir: Path | None, p: dict):
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        from harmonydagger.file_operations import process_audio_file

        # Resolve output directory
        if output_dir is None:
            parents = {f.parent for f in audio_files}
            base = parents.pop() if len(parents) == 1 else audio_files[0].parent
            out_dir = base / "protected"
        else:
            out_dir = output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self.log_message.emit(f"INFO  {len(audio_files)} file(s) → {out_dir}")

        jobs = min(p.get("jobs", 1), multiprocessing.cpu_count())
        success_count = 0
        start = time.time()

        if jobs > 1:
            with ProcessPoolExecutor(max_workers=jobs) as executor:
                futures: dict = {}
                for f in audio_files:
                    out_file = out_dir / f"{f.stem}_protected{f.suffix}"
                    if out_file.exists() and not p.get("clobber", False):
                        self.log_message.emit(f"ERROR ✗ {f.name}: output already exists — skipped (enable Clobber to overwrite)")
                        continue
                    futures[executor.submit(
                        process_audio_file,
                        str(f), str(out_file),
                        window_size=p["window_size"],
                        hop_size=p["hop_size"],
                        noise_scale=p["noise_scale"],
                        adaptive_scaling=p["adaptive_scaling"],
                        force_mono=p["force_mono"],
                        dry_wet=p["dry_wet"],
                        vocal_mode=p["vocal_mode"],
                        use_phase_perturbation=p["use_phase_perturbation"],
                        use_temporal_masking=p["use_temporal_masking"],
                        use_ensemble=p["use_ensemble"],
                        use_gpu=p["use_gpu"],
                        visualize=p.get("visualize", False),
                        visualize_diff=p.get("visualize_diff", False),
                        visualization_path=str(out_dir),
                    )] = f
                for fut, f in futures.items():
                    ok, out, elapsed = fut.result()
                    if ok:
                        success_count += 1
                        self.log_message.emit(f"INFO  ✓ {f.name}  ({elapsed:.2f}s)")
                    else:
                        self.log_message.emit(f"ERROR ✗ {f.name}: {out}")
        else:
            for f in audio_files:
                if self.isInterruptionRequested():
                    break
                out_file = out_dir / f"{f.stem}_protected{f.suffix}"
                if out_file.exists() and not p.get("clobber", False):
                    self.log_message.emit(f"ERROR ✗ {f.name}: output already exists — skipped (enable Clobber to overwrite)")
                    continue
                ok, out, elapsed = process_audio_file(
                    str(f), str(out_file),
                    window_size=p["window_size"],
                    hop_size=p["hop_size"],
                    noise_scale=p["noise_scale"],
                    adaptive_scaling=p["adaptive_scaling"],
                    force_mono=p["force_mono"],
                    dry_wet=p["dry_wet"],
                    vocal_mode=p["vocal_mode"],
                    use_phase_perturbation=p["use_phase_perturbation"],
                    use_temporal_masking=p["use_temporal_masking"],
                    use_ensemble=p["use_ensemble"],
                    use_gpu=p["use_gpu"],
                    visualize=p.get("visualize", False),
                    visualize_diff=p.get("visualize_diff", False),
                    visualization_path=str(out_dir),
                )
                if ok:
                    success_count += 1
                    self.log_message.emit(f"INFO  ✓ {f.name}  ({elapsed:.2f}s)")
                else:
                    self.log_message.emit(f"ERROR ✗ {f.name}: {out}")

        total = time.time() - start
        msg = f"Processed {success_count}/{len(audio_files)} files in {total:.1f}s"
        self.finished.emit(success_count == len(audio_files), msg)

    # ------------------------------------------------------------------
    def _run_analysis(self, p: dict, input_path: Path, out_path: Path):
        if not (p.get("benchmark") or p.get("verify") or p.get("robust")):
            return
        try:
            import librosa

            # Load preserving channels; analysis runs per-channel and averages.
            y_orig, sr = librosa.load(str(input_path), sr=None, mono=False)
            y_prot, _ = librosa.load(str(out_path), sr=sr, mono=False)

            # Normalise to (channels, samples) — mono comes back as 1D.
            if y_orig.ndim == 1:
                y_orig = y_orig[np.newaxis]
            if y_prot.ndim == 1:
                y_prot = y_prot[np.newaxis]

            # Trim to common length along the sample axis.
            n = min(y_orig.shape[1], y_prot.shape[1])
            y_orig = y_orig[:, :n]
            y_prot = y_prot[:, :n]

            n_ch = y_orig.shape[0]
            ch_label = f" (avg {n_ch}ch)" if n_ch > 1 else ""

            if p.get("benchmark"):
                from harmonydagger.benchmark import generate_benchmark_report
                snr_sum = pr_sum = 0.0
                for ch in range(n_ch):
                    r = generate_benchmark_report(y_orig[ch], y_prot[ch], sr)
                    snr_sum += r["snr_db"]
                    pr_sum += r["perturbation_ratio"]
                self.log_message.emit(
                    f"INFO  Benchmark{ch_label} — SNR: {snr_sum/n_ch:.1f} dB  "
                    f"perturbation ratio: {pr_sum/n_ch:.4f}"
                )

            if p.get("verify"):
                from harmonydagger.verify import verify_protection
                ps_sum = ms_sum = 0.0
                for ch in range(n_ch):
                    r = verify_protection(y_orig[ch], y_prot[ch], sr)
                    ps_sum += r["protection_score"]
                    ms_sum += r["mfcc_similarity"]
                self.log_message.emit(
                    f"INFO  Verification{ch_label} — protection score: {ps_sum/n_ch:.3f}  "
                    f"MFCC similarity: {ms_sum/n_ch:.3f}"
                )

            if p.get("robust"):
                from harmonydagger.robustness import augment_and_check_survival
                accum: dict[str, float] = {}
                for ch in range(n_ch):
                    perturbation = y_prot[ch] - y_orig[ch]
                    report = augment_and_check_survival(y_orig[ch], perturbation, sr)
                    for transform, survival in report.items():
                        accum[transform] = accum.get(transform, 0.0) + survival
                for transform, total in accum.items():
                    self.log_message.emit(
                        f"INFO  Robustness{ch_label} [{transform}]: {total/n_ch:.1%} survival"
                    )
        except Exception as exc:
            self.log_message.emit(f"WARNING  Analysis skipped: {exc}")
