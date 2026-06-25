"""Generate synthetic ASR benchmark audio using macOS system TTS.

Supported voices:
- Japanese: Kyoko (ja_JP)
- Korean: Yuna (ko_KR)

Usage:
    .venv-test/bin/python scripts/benchmark/generate_synthetic_audio.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def normalize_filename(text: str, index: int) -> str:
    """Create a safe filename from transcript text."""
    safe = re.sub(r"[^\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF\uAC00-\uD7AF]", "_", text)
    safe = safe.strip("_")[:20]
    return f"{index:03d}_{safe}.wav"


def generate_audio(text: str, output_path: Path, voice: str, rate: int = 180) -> None:
    """Generate WAV audio using macOS `say` command."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "say",
        "-v", voice,
        "-r", str(rate),
        "-o", str(output_path),
        "--data-format", "LEI16@16000",
        text,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic ASR benchmark audio")
    parser.add_argument("--lang", choices=["ja", "ko", "all"], default="all")
    parser.add_argument("--rate", type=int, default=180, help="Speech rate (words per minute)")
    args = parser.parse_args()

    config = {
        "ja": {"voice": "Kyoko", "transcripts": "tests/asr_benchmark/synthetic/ja/transcripts.txt"},
        "ko": {"voice": "Yuna", "transcripts": "tests/asr_benchmark/synthetic/ko/transcripts.txt"},
    }

    root = Path(__file__).parent.parent.parent
    langs = ["ja", "ko"] if args.lang == "all" else [args.lang]

    for lang in langs:
        cfg = config[lang]
        transcripts_file = root / cfg["transcripts"]
        audio_dir = root / "tests" / "asr_benchmark" / "synthetic" / lang / "audio"

        lines = [line.strip() for line in transcripts_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(f"Generating {len(lines)} {lang.upper()} audio files to {audio_dir}")

        for i, text in enumerate(lines, start=1):
            filename = normalize_filename(text, i)
            output_path = audio_dir / filename
            if output_path.exists():
                print(f"  Skip existing: {filename}")
                continue
            try:
                generate_audio(text, output_path, cfg["voice"], args.rate)
                print(f"  Generated: {filename}")
            except subprocess.CalledProcessError as e:
                print(f"  Failed: {filename} - {e.stderr}")


if __name__ == "__main__":
    main()
