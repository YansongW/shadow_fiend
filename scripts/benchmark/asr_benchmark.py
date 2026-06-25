"""ASR benchmark for shadow_fiend.

Compares ASR engines on synthetic and real-world audio clips.
Metrics: WER, CER, latency (wall-clock inference time).

Usage:
    .venv-test/bin/python scripts/benchmark/asr_benchmark.py \
        --engine sensevoice --dataset synthetic --lang ja
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import wave
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_audio(path: Path, target_sr: int = 16000) -> np.ndarray:
    """Load WAV audio and resample to target sample rate."""
    import aifc
    import audioop

    data = bytearray()
    sample_rate = 16000
    channels = 1
    width = 2

    suffix = path.suffix.lower()
    if suffix == ".aiff":
        with aifc.open(str(path), "rb") as f:
            sample_rate = f.getframerate()
            channels = f.getnchannels()
            width = f.getsampwidth()
            data = bytearray(f.readframes(f.getnframes()))
    else:
        with wave.open(str(path), "rb") as f:
            sample_rate = f.getframerate()
            channels = f.getnchannels()
            width = f.getsampwidth()
            data = bytearray(f.readframes(f.getnframes()))

    if channels > 1:
        # Convert stereo to mono.
        data = audioop.tomono(bytes(data), width, 0.5, 0.5)

    if width == 1:
        samples = np.frombuffer(data, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    elif width == 2:
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        raise ValueError(f"Unsupported sample width: {width}")

    if sample_rate != target_sr:
        from scipy import signal
        num_target = int(len(samples) * target_sr / sample_rate)
        samples = signal.resample(samples, num_target)

    return samples


def edit_distance(s1: list[str], s2: list[str]) -> int:
    """Compute Levenshtein distance between two lists of tokens/characters."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if not s2:
        return len(s1)

    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, 1):
        curr = [i]
        for j, c2 in enumerate(s2, 1):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate for CJK languages."""
    ref_chars = list(reference.replace(" ", ""))
    hyp_chars = list(hypothesis.replace(" ", ""))
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    return edit_distance(ref_chars, hyp_chars) / len(ref_chars)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return edit_distance(ref_words, hyp_words) / len(ref_words)


def normalize_text(text: str) -> str:
    """Normalize text for fair comparison."""
    import unicodedata
    import re
    text = unicodedata.normalize("NFKC", text)
    # Remove common punctuation and filler symbols.
    for ch in "、。！？.,!?~〜…":
        text = text.replace(ch, "")
    # Remove emoji and other non-text symbols.
    text = re.sub(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+", "", text)
    return text.strip().lower()


class SenseVoiceBenchmarkEngine:
    """Benchmark wrapper for SenseVoice ASR."""

    def __init__(self, device: str = "auto", chunk_duration_ms: int | None = None):
        self.device = device
        self.chunk_duration_ms = chunk_duration_ms
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
        from asr.sensevoice import ASRModule
        self._model = ASRModule(device=self.device, use_vad=False)
        self._model._load_model()

    def transcribe(self, audio: np.ndarray, language: str) -> tuple[str, float]:
        self._load()
        start = time.perf_counter()
        result = self._model.transcribe(audio, language=language)
        latency = time.perf_counter() - start
        return result.get("text", ""), latency

    def name(self) -> str:
        base = "sensevoice"
        if self.chunk_duration_ms:
            return f"{base}_chunk{self.chunk_duration_ms}ms"
        return base


def load_synthetic_dataset(lang: str) -> list[dict[str, Any]]:
    """Load synthetic dataset: transcripts + audio files."""
    root = Path(__file__).parent.parent.parent
    transcripts_file = root / "tests" / "asr_benchmark" / "synthetic" / lang / "transcripts.txt"
    audio_dir = root / "tests" / "asr_benchmark" / "synthetic" / lang / "audio"

    transcripts = [line.strip() for line in transcripts_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    clips = []
    for i, text in enumerate(transcripts, start=1):
        candidates = list(audio_dir.glob(f"{i:03d}_*.wav"))
        if not candidates:
            logger.warning("No audio found for %s line %d: %s", lang, i, text)
            continue
        clips.append({"id": f"{lang}_syn_{i:03d}", "file": candidates[0], "transcript": text})
    return clips


def load_real_world_dataset(lang: str) -> list[dict[str, Any]]:
    """Load real-world dataset from metadata.json."""
    root = Path(__file__).parent.parent.parent
    metadata_file = root / "tests" / "asr_benchmark" / "real_world" / lang / "metadata.json"
    if not metadata_file.exists():
        return []

    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    clips = []
    for clip in metadata.get("clips", []):
        clip_path = metadata_file.parent / clip["file"]
        clips.append({
            "id": clip.get("id", clip_path.stem),
            "file": clip_path,
            "transcript": clip["transcript"],
            "source": clip.get("source", ""),
        })
    return clips


def run_benchmark(engine, clips: list[dict[str, Any]], language: str) -> dict[str, Any]:
    """Run benchmark on a list of clips."""
    results = []
    total_cer = 0.0
    total_wer = 0.0
    total_latency = 0.0

    for clip in clips:
        audio = load_audio(clip["file"])
        hypothesis, latency = engine.transcribe(audio, language)
        ref_norm = normalize_text(clip["transcript"])
        hyp_norm = normalize_text(hypothesis)
        cer = compute_cer(ref_norm, hyp_norm)
        wer = compute_wer(ref_norm, hyp_norm)

        total_cer += cer
        total_wer += wer
        total_latency += latency

        results.append({
            "id": clip["id"],
            "reference": clip["transcript"],
            "hypothesis": hypothesis,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
            "latency_ms": round(latency * 1000, 2),
        })
        logger.info("%s CER=%.2f%% WER=%.2f%% lat=%.1fms | %s",
                    clip["id"], cer * 100, wer * 100, latency * 1000, hypothesis[:40])

    n = len(results)
    return {
        "engine": engine.name(),
        "language": language,
        "num_clips": n,
        "avg_cer": round(total_cer / n, 4) if n else 0.0,
        "avg_wer": round(total_wer / n, 4) if n else 0.0,
        "avg_latency_ms": round(total_latency / n * 1000, 2) if n else 0.0,
        "clips": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ASR benchmark for shadow_fiend")
    parser.add_argument("--engine", choices=["sensevoice"], default="sensevoice", help="ASR engine")
    parser.add_argument("--dataset", choices=["synthetic", "real_world", "all"], default="synthetic")
    parser.add_argument("--lang", choices=["ja", "ko", "all"], default="all")
    parser.add_argument("--device", default="auto", help="Device for SenseVoice (auto/cpu/cuda/mps)")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON report path")
    args = parser.parse_args()

    langs = ["ja", "ko"] if args.lang == "all" else [args.lang]
    datasets = ["synthetic", "real_world"] if args.dataset == "all" else [args.dataset]

    engine = SenseVoiceBenchmarkEngine(device=args.device)

    all_reports = []
    for lang in langs:
        for dataset_name in datasets:
            if dataset_name == "synthetic":
                clips = load_synthetic_dataset(lang)
            else:
                clips = load_real_world_dataset(lang)

            if not clips:
                logger.warning("No clips found for %s %s, skipping", dataset_name, lang)
                continue

            logger.info("Running %s on %s %s (%d clips)", engine.name(), dataset_name, lang, len(clips))
            report = run_benchmark(engine, clips, lang)
            report["dataset"] = dataset_name
            all_reports.append(report)

            logger.info("Summary: Avg CER=%.2f%% Avg WER=%.2f%% Avg Latency=%.1fms",
                        report["avg_cer"] * 100, report["avg_wer"] * 100, report["avg_latency_ms"])

    output = args.output or Path(__file__).parent.parent.parent / "tests" / "asr_benchmark" / "results" / f"{engine.name()}_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(all_reports, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Report saved to %s", output)


if __name__ == "__main__":
    main()
