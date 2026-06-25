"""
实时语音降噪模块。

基于 RNNoise 的因果帧级降噪，支持 16 kHz 输入/输出。
RNNoise 内部工作在 48 kHz / 10 ms 帧，因此模块内部完成
16 kHz ↔ 48 kHz 重采样。
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)


class RNNoiseDenoiser:
    """
    RNNoise 实时降噪器。

    RNNoise 原生要求 48 kHz、480 样本（10 ms）帧。
    本类对外暴露 16 kHz 接口，内部维护重采样缓冲。

    为了避免重采样边界失真并保证输入/输出严格对齐，
    模块按 1440 样本 @ 16 kHz（90 ms）的批次上采样到 480 样本 @ 48 kHz 处理，
    再下采样回 480 样本 @ 16 kHz 输出。
    """

    # RNNoise 原生参数
    RN_NATIVE_SR = 48000
    RN_FRAME_MS = 10
    RN_FRAME_SIZE_NATIVE = 480  # 48 kHz * 10 ms

    # 16 kHz 端每批样本数：必须 = RN_FRAME_SIZE_NATIVE * (16/48) 的整数倍
    BATCH_SIZE_16K = RN_FRAME_SIZE_NATIVE // 3  # 160 samples = 10 ms @ 16 kHz

    def __init__(self, sample_rate: int = 16000, enabled: bool = True):
        if sample_rate != 16000:
            raise ValueError(f"RNNoiseDenoiser currently only supports 16 kHz, got {sample_rate}")
        self.sample_rate = sample_rate
        self.enabled = enabled

        self._rn_module = self._load_rnnoise_module()
        self._rn_state = self._rn_module.create()
        self._rn_frame_size = self._rn_module.FRAME_SIZE
        self._rn_sample_rate = self._rn_module.SAMPLE_RATE

        # 16 kHz 输入/输出缓冲区
        self._in_buffer16 = np.array([], dtype=np.float32)
        self._out_buffer16 = np.array([], dtype=np.float32)

        logger.info(
            "RNNoise denoiser initialized (sr=%d, enabled=%s, rn_frame_size=%d)",
            sample_rate,
            enabled,
            self._rn_frame_size,
        )

    @staticmethod
    def _load_rnnoise_module():
        """动态加载 pyrnnoise 的低级 rnnoise 模块，绕过 audiolab 依赖问题。"""
        try:
            import pyrnnoise.rnnoise as rnnoise  # type: ignore
            return rnnoise
        except Exception:
            pass

        # Fallback: locate pyrnnoise/rnnoise.py in site-packages.
        for site_path in sys.path:
            candidate = Path(site_path) / "pyrnnoise" / "rnnoise.py"
            if candidate.exists():
                spec = importlib.util.spec_from_file_location(
                    "rnnoise_lowlevel", str(candidate)
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module

        raise RuntimeError(
            "RNNoise backend not found. Please install: pip install pyrnnoise"
        )

    def reset(self) -> None:
        """重置 RNNoise 状态和内部缓冲区。"""
        if self._rn_state is not None:
            self._rn_module.destroy(self._rn_state)
        self._rn_state = self._rn_module.create()
        self._in_buffer16 = np.array([], dtype=np.float32)
        self._out_buffer16 = np.array([], dtype=np.float32)

    @staticmethod
    def _to_int16(audio: np.ndarray) -> np.ndarray:
        return np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)

    @staticmethod
    def _from_int16(audio: np.ndarray) -> np.ndarray:
        return audio.astype(np.float32) / 32767.0

    def _denoise_16k_batch(self, audio16: np.ndarray) -> np.ndarray:
        """处理一段 16 kHz 音频，长度必须是 BATCH_SIZE_16K 的整数倍。"""
        # 上采样到 48 kHz
        audio48 = signal.resample_poly(audio16, up=3, down=1)

        # 按 RNNoise 帧处理
        processed48 = np.zeros_like(audio48)
        for i in range(0, len(audio48), self._rn_frame_size):
            frame = audio48[i : i + self._rn_frame_size]
            if len(frame) < self._rn_frame_size:
                # Should not happen if input length is aligned.
                frame = np.pad(frame, (0, self._rn_frame_size - len(frame)))
            frame_int16 = self._to_int16(frame)
            out_int16, _ = self._rn_module.process_mono_frame(
                self._rn_state, frame_int16
            )
            processed48[i : i + self._rn_frame_size] = self._from_int16(out_int16)

        # 下采样回 16 kHz
        return signal.resample_poly(processed48, up=1, down=3)

    def process_chunk(self, audio: np.ndarray) -> np.ndarray:
        """
        处理一段 16 kHz 音频，返回同长度降噪后的 16 kHz 音频。

        如果当前禁用降噪，直接返回输入音频。
        """
        audio = audio.astype(np.float32)
        if not self.enabled:
            return audio

        # 累积输入缓冲
        self._in_buffer16 = np.concatenate([self._in_buffer16, audio])

        # 处理完整批次
        batch_size = self.BATCH_SIZE_16K
        num_batches = len(self._in_buffer16) // batch_size
        if num_batches > 0:
            process_len = num_batches * batch_size
            to_process = self._in_buffer16[:process_len]
            self._in_buffer16 = self._in_buffer16[process_len:]
            denoised = self._denoise_16k_batch(to_process)
            self._out_buffer16 = np.concatenate([self._out_buffer16, denoised])

        # 返回与输入等长的输出
        if len(self._out_buffer16) >= len(audio):
            result = self._out_buffer16[: len(audio)]
            self._out_buffer16 = self._out_buffer16[len(audio) :]
            return result
        else:
            # Not enough output yet (first few small chunks).
            pad = len(audio) - len(self._out_buffer16)
            result = np.concatenate(
                [self._out_buffer16, np.zeros(pad, dtype=np.float32)]
            )
            self._out_buffer16 = np.array([], dtype=np.float32)
            return result

    def flush(self) -> np.ndarray:
        """刷新剩余缓冲，返回所有未输出音频。"""
        if not self.enabled:
            remaining = self._out_buffer16.copy()
            self._out_buffer16 = np.array([], dtype=np.float32)
            return remaining

        # Pad input buffer to batch size and process.
        if len(self._in_buffer16) > 0:
            pad = self.BATCH_SIZE_16K - (len(self._in_buffer16) % self.BATCH_SIZE_16K)
            if pad == self.BATCH_SIZE_16K:
                pad = 0
            padded = np.pad(self._in_buffer16, (0, pad))
            self._in_buffer16 = np.array([], dtype=np.float32)
            denoised = self._denoise_16k_batch(padded)
            self._out_buffer16 = np.concatenate([self._out_buffer16, denoised])

        result = self._out_buffer16.copy()
        self._out_buffer16 = np.array([], dtype=np.float32)
        return result

    def __del__(self):
        if self._rn_state is not None:
            try:
                self._rn_module.destroy(self._rn_state)
            except Exception:
                pass
            self._rn_state = None
