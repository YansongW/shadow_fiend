"""
VAD 模块：基于能量的简单语音活动检测。

MVE 阶段使用能量阈值 + 静音时长切句。
后续可替换为 Silero VAD。
"""

import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class VADModule:
    """
    简单能量阈值 VAD。

    持续输入音频，当检测到完整 utterance 时返回。
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.005,
        min_speech_ms: int = 250,
        min_silence_ms: int = 400,
        max_utterance_ms: int = 10000,
    ):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.max_utterance_ms = max_utterance_ms

        self._buffer = np.array([], dtype=np.float32)
        self._speech_start: int = -1
        self._silence_samples: int = 0
        self._is_speaking: bool = False

    def _ms_to_samples(self, ms: int) -> int:
        return int(self.sample_rate * ms / 1000)

    def add_audio(self, chunk: np.ndarray) -> List[np.ndarray]:
        """
        输入音频 chunk，返回检测到的完整 utterance 列表。
        """
        chunk = chunk.astype(np.float32)
        self._buffer = np.concatenate([self._buffer, chunk])

        results = []
        max_samples = self._ms_to_samples(self.max_utterance_ms)
        min_speech_samples = self._ms_to_samples(self.min_speech_ms)
        min_silence_samples = self._ms_to_samples(self.min_silence_ms)

        i = 0
        while i < len(self._buffer):
            # Compute RMS energy for current chunk.
            window_size = self._ms_to_samples(30)
            window = self._buffer[i:i + window_size]
            if len(window) < window_size:
                break

            rms = np.sqrt(np.mean(window ** 2))
            is_speech = rms > self.threshold

            if not self._is_speaking:
                if is_speech:
                    self._is_speaking = True
                    self._speech_start = i
                    self._silence_samples = 0
                else:
                    # Trim leading silence to keep buffer bounded.
                    pass
            else:
                if is_speech:
                    self._silence_samples = 0
                else:
                    self._silence_samples += window_size

                speech_samples = i - self._speech_start

                # End utterance if silence is long enough or max length reached.
                should_end = (
                    self._silence_samples >= min_silence_samples
                    and speech_samples >= min_speech_samples
                ) or speech_samples >= max_samples

                if should_end and speech_samples >= min_speech_samples:
                    utterance = self._buffer[self._speech_start:i].copy()
                    results.append(utterance)
                    self._buffer = self._buffer[i:]
                    self._is_speaking = False
                    self._speech_start = -1
                    self._silence_samples = 0
                    i = 0
                    continue

            i += window_size

        # Keep buffer bounded: drop processed leading silence if not speaking.
        if not self._is_speaking and len(self._buffer) > max_samples:
            self._buffer = self._buffer[-max_samples:]

        return results

    def reset(self) -> None:
        """重置状态。"""
        self._buffer = np.array([], dtype=np.float32)
        self._speech_start = -1
        self._silence_samples = 0
        self._is_speaking = False
