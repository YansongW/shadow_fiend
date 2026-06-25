#!/usr/bin/env python3
"""
测试音频捕获模块。

用法：
    ./scripts/test_capture.py

该脚本会从默认音频设备（通常是 BlackHole 2ch）读取 5 秒音频，
并打印音频统计信息。播放视频时运行此脚本，如果看到音量变化，
说明系统音频捕获配置正确。
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from audio.capture import AudioCaptureModule


def main():
    print("shadow_fiend audio capture test")
    print("=" * 40)

    try:
        with AudioCaptureModule() as capture:
            print("Capturing 5 seconds of audio...")
            print("Play a video or make some sound now.\n")

            audio = capture.read_duration(5000)
            print(f"Captured {len(audio)} samples")
            print(f"Min amplitude: {audio.min():.4f}")
            print(f"Max amplitude: {audio.max():.4f}")
            print(f"RMS amplitude: {np.sqrt(np.mean(audio ** 2)):.4f}")

            if np.abs(audio).max() < 0.001:
                print("\nWARNING: Audio level is very low.")
                print("Make sure BlackHole is set up as a Multi-Output Device.")
            else:
                print("\nAudio capture looks good!")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
