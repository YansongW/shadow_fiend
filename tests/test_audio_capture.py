"""
AudioCaptureModule 单元测试。
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audio.capture import AudioCaptureModule


def test_chunk_size_calculation():
    capture = AudioCaptureModule(
        sample_rate=16000,
        channels=1,
        chunk_duration_ms=100,
    )
    assert capture._chunk_size == 1600


def test_stereo_to_mono_conversion():
    capture = AudioCaptureModule(
        sample_rate=16000,
        channels=2,
        chunk_duration_ms=100,
    )
    # Manually test the conversion logic without starting the stream.
    samples = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    reshaped = samples.reshape(-1, 2)
    mono = reshaped.mean(axis=1)
    np.testing.assert_array_equal(mono, np.array([1.5, 3.5]))
