"""
VAD 模块单元测试。
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audio.vad import VADModule


def test_silence_returns_empty():
    vad = VADModule()
    silence = np.zeros(16000, dtype=np.float32)
    assert vad.add_audio(silence) == []


def test_speech_then_silence_returns_utterance():
    vad = VADModule(sample_rate=16000, threshold=0.1, min_speech_ms=100, min_silence_ms=100)

    # 0.3s of speech
    speech = np.ones(int(16000 * 0.3), dtype=np.float32) * 0.5
    # 0.5s of silence (above min_silence_ms)
    silence = np.zeros(int(16000 * 0.5), dtype=np.float32)

    audio = np.concatenate([speech, silence])
    results = vad.add_audio(audio)

    assert len(results) == 1
    assert len(results[0]) >= int(16000 * 0.3)


def test_max_length_forces_split():
    vad = VADModule(sample_rate=16000, threshold=0.1, max_utterance_ms=500)

    # 1.2s of continuous speech, should be split into at least 2 utterances.
    speech = np.ones(int(16000 * 1.2), dtype=np.float32) * 0.5
    results = vad.add_audio(speech)

    assert len(results) >= 2
