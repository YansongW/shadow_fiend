#!/usr/bin/env python3
"""
测试 ASR 模块。

用法：
    ./scripts/test_asr.py path/to/audio.wav

该脚本会用 SenseVoice-Small 识别指定音频文件，并打印识别结果。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from asr.sensevoice import ASRModule


def main():
    parser = argparse.ArgumentParser(description="Shadow Fiend ASR test")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("--language", default="auto", help="Source language")
    args = parser.parse_args()

    print("Shadow Fiend ASR test")
    print("=" * 40)

    asr = ASRModule()
    print(f"Loading audio: {args.audio}")
    print("Recognizing... (first run will download the model)")

    result = asr.transcribe(args.audio, language=args.language)
    print(f"Detected language: {result['language']}")
    print(f"Text: {result['text']}")


if __name__ == "__main__":
    main()
