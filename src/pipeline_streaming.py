"""
shadow_fiend 流式主流程编排模块。

把音频捕获、Silero VAD、SenseVoice 短窗口流式 ASR、翻译、UI 串成实时 pipeline。
"""

from __future__ import annotations

import logging
import threading
import time
from queue import Queue
from typing import Optional

import numpy as np

from audio.capture import AudioCaptureModule
from audio.denoiser import RNNoiseDenoiser
from audio.silero_vad import SileroVADModule
from asr.streaming_sensevoice import StreamingSenseVoiceASR
from translation.argos_engine import TranslationModule
from ui.subtitle_window import SubtitleWindow

logger = logging.getLogger(__name__)


class StreamingTranslationPipeline:
    """
    实时字幕翻译 pipeline（流式版本）。

    数据流：
        音频捕获 -> Silero VAD -> 流式 ASR -> 翻译 -> UI 浮窗

    线程模型：
        - 主线程：Qt UI 事件循环
        - 音频线程：从 BlackHole 读取 chunk
        - 处理线程：VAD -> 流式 ASR -> 翻译 -> 更新 UI
    """

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "zh",
        device_name: str = "BlackHole 2ch",
        sample_rate: int = 16000,
        compact: bool = False,
        asr_device: str = "auto",
        chunk_duration_ms: int = 40,
        vad_threshold: float = 0.5,
        vad_min_silence_ms: int = 300,
        vad_min_speech_ms: int = 200,
        vad_max_utterance_ms: int = 5000,
        asr_window_ms: int = 500,
        asr_hop_ms: int = 200,
        denoise_enabled: bool = True,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.compact = compact
        self.asr_device = asr_device
        self.chunk_duration_ms = chunk_duration_ms

        self.vad_threshold = vad_threshold
        self.vad_min_silence_ms = vad_min_silence_ms
        self.vad_min_speech_ms = vad_min_speech_ms
        self.vad_max_utterance_ms = vad_max_utterance_ms
        self.asr_window_ms = asr_window_ms
        self.asr_hop_ms = asr_hop_ms
        self.denoise_enabled = denoise_enabled

        self._running = False
        self._audio_thread: Optional[threading.Thread] = None
        self._process_thread: Optional[threading.Thread] = None

        self._audio_queue: Queue[np.ndarray] = Queue(maxsize=300)
        self._subtitle_queue: Queue[tuple[str, str]] = Queue()
        self._subtitle_history: list[dict] = []

        self._capture: Optional[AudioCaptureModule] = None
        self._denoiser: Optional[RNNoiseDenoiser] = None
        self._vad: Optional[SileroVADModule] = None
        self._asr: Optional[StreamingSenseVoiceASR] = None
        self._translator: Optional[TranslationModule] = None
        self._ui: Optional[SubtitleWindow] = None

    def start(self) -> None:
        """启动 pipeline。"""
        if self._running:
            return

        logger.info("Starting shadow_fiend streaming translation pipeline")
        self._running = True

        self._capture = AudioCaptureModule(
            device_name=self.device_name,
            sample_rate=self.sample_rate,
            chunk_duration_ms=self.chunk_duration_ms,
        )
        self._denoiser = RNNoiseDenoiser(
            sample_rate=self.sample_rate,
            enabled=self.denoise_enabled,
        )
        self._vad = SileroVADModule(
            sample_rate=self.sample_rate,
            threshold=self.vad_threshold,
            min_silence_ms=self.vad_min_silence_ms,
            min_speech_ms=self.vad_min_speech_ms,
            max_utterance_ms=self.vad_max_utterance_ms,
            device=self.asr_device,
        )
        self._asr = StreamingSenseVoiceASR(
            device=self.asr_device,
            window_ms=self.asr_window_ms,
            hop_ms=self.asr_hop_ms,
        )
        self._translator = TranslationModule(
            source_lang=self.source_lang if self.source_lang != "auto" else "en",
            target_lang=self.target_lang,
        )
        self._ui = SubtitleWindow(
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            compact=self.compact,
        )
        self._ui.set_export_srt_callback(self.export_srt)
        self._ui.on_toggle_denoise = self._toggle_denoise

        self._capture.start()

        # Warm up ASR on the target device to avoid first-inference stalls.
        logger.info("Warming up ASR...")
        self._asr.warmup(language=self.source_lang)

        self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._audio_thread.start()
        self._process_thread.start()

        self._ui._ensure_qt()
        self._timer = self._ui._QtCore.QTimer()
        self._timer.timeout.connect(self._update_ui)
        self._timer.start(50)

        self._ui.show()

    def _audio_loop(self) -> None:
        """持续读取音频并推入队列。"""
        logger.info("Audio loop started")
        while self._running:
            try:
                chunk = self._capture.read_chunk()
                if not self._audio_queue.full():
                    self._audio_queue.put(chunk, block=False)
                else:
                    logger.warning("Audio queue full, dropping chunk")
            except Exception as e:
                logger.error("Audio capture error: %s", e)
                time.sleep(0.1)

    def _process_loop(self) -> None:
        """处理音频队列：VAD -> 流式 ASR -> 翻译。"""
        logger.info("Process loop started")
        while self._running:
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except Exception:
                continue

            try:
                # Denoise before VAD/ASR when enabled.
                if self._denoiser is not None:
                    chunk = self._denoiser.process_chunk(chunk)

                was_speaking = self._vad._is_speaking
                utterances = self._vad.add_audio(chunk)
                is_speaking = self._vad._is_speaking
                speech_ended = was_speaking and not is_speaking

                # Speech started: reset ASR for a fresh utterance.
                if not was_speaking and is_speaking:
                    self._asr.reset()

                # Feed audio only during speech to save compute.
                if is_speaking:
                    asr_result = self._asr.feed_audio(chunk, language=self.source_lang)
                    if asr_result and asr_result.text:
                        # Show partial source text immediately without translating.
                        self._subtitle_queue.put(("partial_source", asr_result.text))

                # Speech ended: finalize and translate the full utterance.
                if speech_ended or utterances:
                    final_result = self._asr.finalize(language=self.source_lang)
                    if final_result and final_result.text:
                        self._process_asr_result(final_result)
                    self._asr.reset()
            except Exception as e:
                logger.error("Processing error: %s", e)

    def _process_asr_result(self, result) -> None:
        """处理 ASR 结果并翻译。"""
        source_text = result.text.strip()
        if not source_text:
            return

        # Auto language detection update.
        if result.language and result.language != "auto" and result.language in {"zh", "en", "ja", "ko"}:
            if self.source_lang == "auto" and self._translator.source_lang != result.language:
                logger.info("Auto-detected source language: %s", result.language)
                self._translator = TranslationModule(
                    source_lang=result.language,
                    target_lang=self.target_lang,
                )

        try:
            translated_text = self._translator.translate(source_text)
        except Exception as e:
            logger.error("Translation error: %s", e)
            translated_text = "[翻译失败]"

        end_time = time.time()
        self._subtitle_history.append({
            "start": end_time,
            "end": end_time,
            "source": source_text,
            "translated": translated_text,
        })
        self._subtitle_queue.put((source_text, translated_text))

    def _toggle_denoise(self) -> None:
        """切换降噪开关。"""
        self.denoise_enabled = not self.denoise_enabled
        if self._denoiser is not None:
            self._denoiser.enabled = self.denoise_enabled
        if self._ui is not None:
            self._ui.set_denoise(self.denoise_enabled)
        logger.info("Denoise %s", "enabled" if self.denoise_enabled else "disabled")

    def _update_ui(self) -> None:
        """从字幕队列取出结果并更新 UI。"""
        while not self._subtitle_queue.empty():
            try:
                key, value = self._subtitle_queue.get(block=False)
                if key == "partial_source":
                    self._ui.show_partial_source(value)
                else:
                    self._ui.show_text(key, value)
            except Exception as e:
                logger.error("UI update error: %s", e)

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """将秒数格式化为 SRT 时间戳 HH:MM:SS,mmm。"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def export_srt(self, path: str) -> None:
        """将当前字幕历史导出为 SRT 文件。"""
        logger.info("Exporting %d subtitles to %s", len(self._subtitle_history), path)
        with open(path, "w", encoding="utf-8") as f:
            for i, item in enumerate(self._subtitle_history, start=1):
                start = self._format_srt_time(item["start"])
                end = self._format_srt_time(item["end"])
                text = item["translated"] if item["translated"] else item["source"]
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

    def stop(self) -> None:
        """停止 pipeline。"""
        logger.info("Stopping shadow_fiend streaming translation pipeline")
        self._running = False

        if self._timer is not None:
            if self._ui._QtCore.QThread.currentThread() == self._timer.thread():
                self._timer.stop()
            else:
                self._ui._QtCore.QMetaObject.invokeMethod(
                    self._timer, "stop", self._ui._QtCore.Qt.ConnectionType.QueuedConnection
                )

        if self._audio_thread is not None:
            self._audio_thread.join(timeout=2)
        if self._process_thread is not None:
            self._process_thread.join(timeout=2)

        # Flush denoiser and finalize any trailing speech before tearing down.
        if self._denoiser is not None:
            try:
                tail = self._denoiser.flush()
                if len(tail) > 0 and self._vad is not None:
                    self._vad.add_audio(tail)
            except Exception as e:
                logger.error("Denoiser flush error: %s", e)

        if self._asr is not None and self._vad is not None and self._vad._is_speaking:
            try:
                final_result = self._asr.finalize(language=self.source_lang)
                if final_result and final_result.text:
                    self._process_asr_result(final_result)
            except Exception as e:
                logger.error("Finalize on stop error: %s", e)

        if self._capture is not None:
            self._capture.stop()
        if self._ui is not None:
            self._ui.close()

    def run(self) -> None:
        """启动并阻塞直到 UI 关闭。"""
        self.start()
        try:
            self._ui.run()
        finally:
            self.stop()
