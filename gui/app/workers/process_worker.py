"""Background QThread that runs HarmonyDagger processing without freezing the UI."""
import logging
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class _QtLogHandler(logging.Handler):
    """Forwards Python log records to a Qt signal."""

    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))

    def emit(self, record: logging.LogRecord):
        self.signal.emit(self.formatMessage(record))


class ProcessWorker(QThread):
    """
    Runs process_audio_file (or batch) in a background thread.

    Signals
    -------
    log_message : str
        Log lines to display in LogPanel.
    finished : (bool, str)
        True + summary message on success; False + error message on failure.
    """

    log_message: pyqtSignal = pyqtSignal(str)
    finished: pyqtSignal = pyqtSignal(bool, str)

    def __init__(self, params: dict):
        super().__init__()
        self._params = params

    # ------------------------------------------------------------------
    def run(self):
        params = self._params
        input_path = Path(params["input"])
        output_path = Path(params["output"]) if params.get("output") else None
        is_batch = params.get("batch", False)

        # Attach Qt log handler to harmonydagger's logger hierarchy
        handler = _QtLogHandler(self.log_message)
        pkg_logger = logging.getLogger("harmonydagger")
        pkg_logger.addHandler(handler)
        pkg_logger.setLevel(logging.DEBUG)

        try:
            if is_batch:
                self._run_batch(input_path, output_path, params)
            else:
                self._run_single(input_path, output_path, params)
        except Exception as exc:
            self.finished.emit(False, str(exc))
        finally:
            pkg_logger.removeHandler(handler)

    # ------------------------------------------------------------------
    def _run_single(self, input_path: Path, output_path: Path | None, p: dict):
        from harmonydagger.file_operations import process_audio_file

        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_protected{input_path.suffix}"

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
        )

        if not success:
            self.finished.emit(False, f"Processing failed: {out}")
            return

        self.log_message.emit(f"INFO  Saved → {out}  ({elapsed:.2f}s)")
        self._run_analysis(p, input_path, Path(out))
        self.finished.emit(True, f"Saved to {out}")

    def _run_batch(self, input_dir: Path, output_dir: Path | None, p: dict):
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        from harmonydagger.file_operations import process_audio_file

        fmt = p.get("format", "all")
        if fmt == "all":
            exts = [".wav", ".mp3", ".flac", ".ogg"]
        else:
            exts = [f".{fmt}"]

        audio_files = []
        for ext in exts:
            audio_files.extend(input_dir.glob(f"*{ext}"))
            audio_files.extend(input_dir.glob(f"*{ext.upper()}"))

        if not audio_files:
            self.finished.emit(False, f"No audio files found in {input_dir}")
            return

        out_dir = output_dir or (input_dir / "protected")
        out_dir.mkdir(parents=True, exist_ok=True)
        self.log_message.emit(f"INFO  Found {len(audio_files)} file(s) → {out_dir}")

        jobs = min(p.get("jobs", 1), multiprocessing.cpu_count())
        success_count = 0
        start = time.time()

        if jobs > 1:
            with ProcessPoolExecutor(max_workers=jobs) as executor:
                futures = {
                    executor.submit(
                        process_audio_file,
                        str(f),
                        str(out_dir / f"{f.stem}_protected{f.suffix}"),
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
                    ): f
                    for f in audio_files
                }
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
            y_orig, sr = librosa.load(str(input_path), sr=None, mono=p.get("force_mono", False))
            y_prot, _ = librosa.load(str(out_path), sr=sr, mono=p.get("force_mono", False))
            n = min(len(y_orig), len(y_prot))
            y_orig, y_prot = y_orig[:n], y_prot[:n]

            if p.get("benchmark"):
                from harmonydagger.benchmark import generate_benchmark_report
                r = generate_benchmark_report(y_orig, y_prot, sr)
                self.log_message.emit(
                    f"INFO  Benchmark — SNR: {r['snr_db']:.1f} dB  "
                    f"perturbation ratio: {r['perturbation_ratio']:.4f}"
                )

            if p.get("verify"):
                from harmonydagger.verify import verify_protection
                r = verify_protection(y_orig, y_prot, sr)
                self.log_message.emit(
                    f"INFO  Verification — protection score: {r['protection_score']:.3f}  "
                    f"MFCC similarity: {r['mfcc_similarity']:.3f}"
                )

            if p.get("robust"):
                from harmonydagger.robustness import augment_and_check_survival
                perturbation = y_prot - y_orig
                report = augment_and_check_survival(y_orig, perturbation, sr)
                for transform, survival in report.items():
                    self.log_message.emit(
                        f"INFO  Robustness [{transform}]: {survival:.1%} survival"
                    )
        except Exception as exc:
            self.log_message.emit(f"WARNING  Analysis skipped: {exc}")
