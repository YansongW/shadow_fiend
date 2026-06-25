"""
音频捕获模块。

负责从 macOS 音频输入设备（通常是 BlackHole 2ch）读取原始 PCM 数据。
"""

import logging
from typing import Optional

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)


class AudioCaptureModule:
    """
    从指定音频输入设备捕获音频。

    默认配置：
        - sample_rate: 16000 Hz
        - channels: 1（单声道）
        - format: 16-bit PCM
        - output: float32 numpy array, normalized to [-1.0, 1.0]
    """

    def __init__(
        self,
        device_name: Optional[str] = "BlackHole 2ch",
        device_index: Optional[int] = None,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration_ms: int = 100,
    ):
        self.device_name = device_name
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration_ms = chunk_duration_ms
        self._chunk_size = int(sample_rate * channels * chunk_duration_ms / 1000)
        self._device_sample_rate: Optional[int] = None
        self._device_chunk_size: Optional[int] = None

        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._is_running = False

    def _find_device_index(self) -> int:
        """根据 device_name 查找设备索引，如果找不到则抛出异常。"""
        if self.device_index is not None:
            return self.device_index

        if self._pyaudio is None:
            raise RuntimeError("PyAudio is not initialized")

        target = (self.device_name or "").lower()
        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            name = info.get("name", "").lower()
            if target in name:
                logger.info(
                    "Found audio device '%s' at index %d (sample rate %.0f)",
                    info.get("name"),
                    i,
                    info.get("defaultSampleRate"),
                )
                return i

        available = [
            self._pyaudio.get_device_info_by_index(i).get("name", "")
            for i in range(self._pyaudio.get_device_count())
        ]
        raise RuntimeError(
            f"Audio device '{self.device_name}' not found. "
            f"Available input devices: {available}"
        )

    def start(self) -> None:
        """启动音频捕获。"""
        if self._is_running:
            return

        try:
            import pyaudio
        except ImportError as e:
            raise RuntimeError(
                "PyAudio is not installed. Please run: ./scripts/setup.sh"
            ) from e

        logger.info("Starting audio capture (sample_rate=%d, channels=%d)",
                    self.sample_rate, self.channels)
        self._pyaudio = pyaudio.PyAudio()
        device_index = self._find_device_index()

        # Open the stream at the device's native sample rate and resample in
        # software. PyAudio's built-in resampling can produce distorted audio
        # when the requested rate differs from the device's default rate
        # (e.g. BlackHole 2ch reports 48000 Hz but we want 16000 Hz).
        device_info = self._pyaudio.get_device_info_by_index(device_index)
        self._device_sample_rate = int(device_info.get("defaultSampleRate", self.sample_rate))
        self._device_chunk_size = int(
            self._chunk_size * self._device_sample_rate / self.sample_rate
        )
        logger.info(
            "Opening audio stream at native sample rate %d Hz (target %d Hz)",
            self._device_sample_rate,
            self.sample_rate,
        )

        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self._device_sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self._device_chunk_size,
        )
        self._is_running = True

    def read_chunk(self) -> np.ndarray:
        """
        读取一个 chunk 的音频数据。

        Returns:
            float32 numpy array with shape (samples,), normalized to [-1.0, 1.0].
        """
        if not self._is_running or self._stream is None:
            raise RuntimeError("Audio capture is not started")

        data = self._stream.read(self._device_chunk_size, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

        # If stereo, convert to mono by averaging channels.
        if self.channels > 1:
            samples = samples.reshape(-1, self.channels).mean(axis=1)

        # Resample from the device's native rate to the target rate.
        if self._device_sample_rate != self.sample_rate:
            num_target = int(len(samples) * self.sample_rate / self._device_sample_rate)
            samples = signal.resample(samples, num_target)

        return samples

    def read_duration(self, duration_ms: int) -> np.ndarray:
        """读取指定时长的音频数据。"""
        num_samples = int(self.sample_rate * duration_ms / 1000)
        chunks = []
        while sum(len(c) for c in chunks) < num_samples:
            chunks.append(self.read_chunk())
        audio = np.concatenate(chunks)
        return audio[:num_samples]

    def stop(self) -> None:
        """停止音频捕获并释放资源。"""
        logger.info("Stopping audio capture")
        self._is_running = False
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._pyaudio is not None:
            self._pyaudio.terminate()
            self._pyaudio = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False
