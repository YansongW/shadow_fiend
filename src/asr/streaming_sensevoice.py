"""
SenseVoice 短窗口流式 ASR 模块。

将音频切成滑动窗口，连续调用 SenseVoice 模型，模拟流式识别效果。
适合 v0.0.2 阶段在不更换 ASR 模型的情况下降低延迟。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from asr.sensevoice import ASRModule

logger = logging.getLogger(__name__)


@dataclass
class StreamingASRResult:
    """流式 ASR 结果。"""

    text: str
    is_final: bool
    language: str


class StreamingSenseVoiceASR:
    """
    基于 SenseVoice 的短窗口流式 ASR。

    通过滑动窗口连续调用 SenseVoice，输出当前窗口识别结果（partial）
    以及 utterance 结束时的完整识别结果（final）。
    """

    def __init__(
        self,
        model_name: str = "iic/SenseVoiceSmall",
        device: str = "auto",
        window_ms: int = 1500,
        hop_ms: int = 500,
        max_context_ms: int = 3000,
    ):
        self.window_ms = window_ms
        self.hop_ms = hop_ms
        self.max_context_ms = max_context_ms

        self._asr = ASRModule(model_name=model_name, device=device, use_vad=False)
        self._asr._load_model()

        self._audio_buffer = np.array([], dtype=np.float32)
        self._last_text = ""
        self._sample_rate = 16000
        self._samples_since_last_asr = 0

    def _ms_to_samples(self, ms: int) -> int:
        return int(self._sample_rate * ms / 1000)

    def reset(self) -> None:
        """重置状态。"""
        self._audio_buffer = np.array([], dtype=np.float32)
        self._last_text = ""
        self._samples_since_last_asr = 0

    def warmup(self, language: str = "auto", duration_ms: int = 300) -> None:
        """用一段虚拟音频预热模型，避免首次推理延迟。"""
        samples = self._ms_to_samples(duration_ms)
        dummy = np.zeros(samples, dtype=np.float32)
        logger.info("Warming up StreamingSenseVoiceASR with %d ms dummy audio", duration_ms)
        self._asr.transcribe(dummy, language=language)

    def feed_audio(self, audio: np.ndarray, language: str = "auto") -> Optional[StreamingASRResult]:
        """
        输入一段音频 chunk，按 hop_ms 间隔触发 ASR。

        返回当前窗口的完整识别文本（partial）。
        """
        audio = audio.astype(np.float32)
        self._audio_buffer = np.concatenate([self._audio_buffer, audio])
        self._samples_since_last_asr += len(audio)

        hop_samples = self._ms_to_samples(self.hop_ms)
        window_samples = self._ms_to_samples(self.window_ms)

        if self._samples_since_last_asr < hop_samples:
            return None
        self._samples_since_last_asr = 0

        # Keep buffer bounded to max_context_ms.
        max_context_samples = self._ms_to_samples(self.max_context_ms)
        if len(self._audio_buffer) > max_context_samples:
            self._audio_buffer = self._audio_buffer[-max_context_samples:]

        # Wait until we have at least one full window to avoid short-window
        # misrecognition; this also keeps first-partial latency predictable.
        if len(self._audio_buffer) < window_samples:
            return None

        # Run ASR on the latest window.
        input_audio = self._audio_buffer[-window_samples:]
        start = time.perf_counter()
        result = self._asr.transcribe(input_audio, language=language)
        latency = time.perf_counter() - start

        text = result.get("text", "").strip()
        detected_lang = result.get("language", language)

        if not text or text == self._last_text:
            return None

        self._last_text = text
        logger.debug("Streaming ASR partial: %s (lat=%.1fms)", text, latency * 1000)
        return StreamingASRResult(text=text, is_final=False, language=detected_lang)

    def finalize(self, language: str = "auto") -> Optional[StreamingASRResult]:
        """
        强制识别当前缓冲区中的所有音频，作为 final 结果。
        """
        if len(self._audio_buffer) == 0:
            return None

        result = self._asr.transcribe(self._audio_buffer, language=language)
        text = result.get("text", "").strip()
        detected_lang = result.get("language", language)

        if not text:
            return None

        return StreamingASRResult(text=text, is_final=True, language=detected_lang)
