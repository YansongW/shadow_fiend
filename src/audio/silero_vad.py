"""
Silero VAD 模块：基于 Silero VAD 模型的流式语音活动检测。

相比能量阈值 VAD，Silero VAD 对噪声更鲁棒，适合低延迟切句。
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class SileroVADModule:
    """
    基于 Silero VAD 的流式语音活动检测。

    持续输入音频 chunk，当检测到完整 utterance 时返回。
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        threshold: float = 0.5,
        min_speech_ms: int = 250,
        min_silence_ms: int = 350,
        max_utterance_ms: int = 5000,
        device: str = "auto",
    ):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.max_utterance_ms = max_utterance_ms

        self._model = None
        self._utils = None
        self._device: Optional[str] = None

        # Audio buffer for accumulating speech.
        self._buffer = np.array([], dtype=np.float32)
        self._is_speaking = False
        self._speech_start_idx = 0
        self._speech_end_idx = 0
        self._total_samples_processed = 0
        # For smoothing speech probability.
        self._speech_probs: list[float] = []
        self._smooth_window = 5

        self._resolve_device(device)
        self._load_model()

    def _resolve_device(self, device: str) -> None:
        """解析 device 参数。"""
        if device != "auto":
            self._device = device
            return
        try:
            import torch
            if torch.backends.mps.is_available():
                self._device = "mps"
                return
            if torch.cuda.is_available():
                self._device = "cuda"
                return
        except Exception:
            pass
        self._device = "cpu"

    def _load_model(self) -> None:
        """加载 Silero VAD 模型。"""
        try:
            import torch
        except ImportError as e:
            raise RuntimeError("PyTorch is required for Silero VAD") from e

        logger.info("Loading Silero VAD model on device '%s'", self._device)
        try:
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
                trust_repo=True,
            )
        except Exception as e:
            logger.error("Failed to load Silero VAD from torch.hub: %s", e)
            raise

        self._model = model.to(self._device)
        self._model.eval()

    def _speech_probability(self, window: np.ndarray) -> float:
        """Run Silero VAD model on a window and return speech probability."""
        import torch
        with torch.no_grad():
            tensor = torch.from_numpy(window).to(self._device)
            # Silero VAD expects batch-first tensor of shape (batch, samples).
            if tensor.dim() == 1:
                tensor = tensor.unsqueeze(0)
            speech_prob = self._model(tensor, self.sample_rate).item()
        return speech_prob

    def _ms_to_samples(self, ms: int) -> int:
        return int(self.sample_rate * ms / 1000)

    def add_audio(self, chunk: np.ndarray) -> List[np.ndarray]:
        """
        输入音频 chunk，返回检测到的完整 utterance 列表。
        """
        chunk = chunk.astype(np.float32)
        results: List[np.ndarray] = []

        min_speech_samples = self._ms_to_samples(self.min_speech_ms)
        min_silence_samples = self._ms_to_samples(self.min_silence_ms)
        max_utterance_samples = self._ms_to_samples(self.max_utterance_ms)

        # Append chunk to buffer first.
        buffer_start_idx = self._total_samples_processed
        self._buffer = np.concatenate([self._buffer, chunk])
        self._total_samples_processed += len(chunk)

        # Process each 32ms window within the chunk.
        window_size = self._ms_to_samples(32)
        for i in range(0, len(chunk), window_size):
            window = chunk[i:i + window_size]
            if len(window) < window_size:
                # Pad last incomplete window.
                window = np.pad(window, (0, window_size - len(window)), mode="constant")

            try:
                speech_prob = self._speech_probability(window)
                self._speech_probs.append(speech_prob)
                if len(self._speech_probs) > self._smooth_window:
                    self._speech_probs.pop(0)
                # Smooth over recent windows to reduce flicker.
                smoothed_prob = sum(self._speech_probs) / len(self._speech_probs)
                is_speech = smoothed_prob >= self.threshold
            except Exception as e:
                logger.error("Silero VAD inference error: %s", e)
                continue

            window_start = buffer_start_idx + i
            window_end = window_start + window_size

            if not self._is_speaking:
                if is_speech:
                    self._is_speaking = True
                    self._speech_start_idx = window_start
                    self._speech_end_idx = window_end
            else:
                if is_speech:
                    self._speech_end_idx = window_end

                speech_samples = self._speech_end_idx - self._speech_start_idx
                silence_samples = window_end - self._speech_end_idx

                should_end = (
                    silence_samples >= min_silence_samples
                    and speech_samples >= min_speech_samples
                ) or speech_samples >= max_utterance_samples

                if should_end and speech_samples >= min_speech_samples:
                    utterance = self._buffer[self._speech_start_idx:self._speech_end_idx].copy()
                    if len(utterance) >= min_speech_samples:
                        results.append(utterance)
                    # Reset state.
                    self._buffer = self._buffer[self._speech_end_idx:]
                    self._total_samples_processed -= self._speech_end_idx
                    self._speech_start_idx = 0
                    self._speech_end_idx = 0
                    self._is_speaking = False
                    self._speech_probs = []

        # Keep buffer bounded.
        max_buffer_samples = max_utterance_samples + min_silence_samples
        if len(self._buffer) > max_buffer_samples:
            drop = len(self._buffer) - max_buffer_samples
            self._buffer = self._buffer[-max_buffer_samples:]
            self._total_samples_processed -= drop
            if self._is_speaking:
                self._speech_start_idx = max(0, self._speech_start_idx - drop)
                self._speech_end_idx = max(0, self._speech_end_idx - drop)

        return results

    def reset(self) -> None:
        """重置状态。"""
        self._buffer = np.array([], dtype=np.float32)
        self._is_speaking = False
        self._speech_start_idx = 0
        self._speech_end_idx = 0
        self._total_samples_processed = 0
        self._speech_probs = []
