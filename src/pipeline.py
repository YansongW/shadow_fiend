"""
YingMo 主流程编排模块。

把音频捕获、VAD、ASR、翻译、UI 串成一个实时 pipeline。
"""

import logging
import threading
import time
from queue import Queue
from typing import Optional

import numpy as np

from audio.capture import AudioCaptureModule
from audio.vad import VADModule
from asr.sensevoice import ASRModule
from translation.argos_engine import TranslationModule
from ui.subtitle_window import SubtitleWindow

logger = logging.getLogger(__name__)


class TranslationPipeline:
    """
    实时字幕翻译 pipeline。

    数据流：
        音频捕获 -> VAD 切句 -> ASR -> 翻译 -> UI 浮窗

    线程模型：
        - 主线程：Qt UI 事件循环
        - 音频线程：从 BlackHole 读取 chunk
        - 处理线程：VAD -> ASR -> 翻译 -> 更新 UI
    """

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "zh",
        device_name: str = "BlackHole 2ch",
        sample_rate: int = 16000,
        compact: bool = False,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.device_name = device_name
        self.sample_rate = sample_rate
        self.compact = compact

        self._running = False
        self._audio_thread: Optional[threading.Thread] = None
        self._process_thread: Optional[threading.Thread] = None

        self._audio_queue: Queue[np.ndarray] = Queue(maxsize=120)
        self._subtitle_queue: Queue[tuple[str, str]] = Queue()

        self._capture: Optional[AudioCaptureModule] = None
        self._vad: Optional[VADModule] = None
        self._asr: Optional[ASRModule] = None
        self._translator: Optional[TranslationModule] = None
        self._ui: Optional[SubtitleWindow] = None

    def start(self) -> None:
        """启动 pipeline。"""
        if self._running:
            return

        logger.info("Starting YingMo translation pipeline")
        self._running = True

        # Initialize modules.
        self._capture = AudioCaptureModule(
            device_name=self.device_name,
            sample_rate=self.sample_rate,
            chunk_duration_ms=100,
        )
        self._vad = VADModule(sample_rate=self.sample_rate)
        self._asr = ASRModule(device="auto")
        self._translator = TranslationModule(
            source_lang=self.source_lang if self.source_lang != "auto" else "en",
            target_lang=self.target_lang,
        )
        self._ui = SubtitleWindow(
            source_lang=self.source_lang,
            target_lang=self.target_lang,
            compact=self.compact,
        )

        # Start audio capture.
        self._capture.start()

        # Start worker threads.
        self._audio_thread = threading.Thread(target=self._audio_loop, daemon=True)
        self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._audio_thread.start()
        self._process_thread.start()

        # UI timer to poll subtitle queue.
        self._ui._ensure_qt()
        self._timer = self._ui._QtCore.QTimer()
        self._timer.timeout.connect(self._update_ui)
        self._timer.start(100)

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
        """处理音频队列：VAD -> ASR -> 翻译。"""
        logger.info("Process loop started")
        while self._running:
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except Exception:
                continue

            try:
                utterances = self._vad.add_audio(chunk)
                for utterance in utterances:
                    self._process_utterance(utterance)
            except Exception as e:
                logger.error("Processing error: %s", e)

    def _process_utterance(self, audio: np.ndarray) -> None:
        """处理一个完整 utterance。"""
        logger.debug("Processing utterance of %d samples", len(audio))

        # ASR
        try:
            asr_result = self._asr.transcribe(audio, language=self.source_lang)
        except Exception as e:
            logger.error("ASR error: %s", e)
            return

        source_text = asr_result.get("text", "").strip()
        if not source_text:
            return

        detected_lang = asr_result.get("language", self.source_lang)
        if detected_lang and detected_lang != "auto":
            # Update translator source language if auto-detection changed it.
            if self.source_lang == "auto" and detected_lang in {"zh", "en", "ja", "ko"}:
                if self._translator.source_lang != detected_lang:
                    logger.info("Auto-detected source language: %s", detected_lang)
                    self._translator = TranslationModule(
                        source_lang=detected_lang,
                        target_lang=self.target_lang,
                    )

        # Translation
        try:
            translated_text = self._translator.translate(source_text)
        except Exception as e:
            logger.error("Translation error: %s", e)
            translated_text = "[翻译失败]"

        self._subtitle_queue.put((source_text, translated_text))

    def _update_ui(self) -> None:
        """从字幕队列取出结果并更新 UI。"""
        while not self._subtitle_queue.empty():
            try:
                source, translated = self._subtitle_queue.get(block=False)
                self._ui.show_text(source, translated)
            except Exception as e:
                logger.error("UI update error: %s", e)

    def stop(self) -> None:
        """停止 pipeline。"""
        logger.info("Stopping YingMo translation pipeline")
        self._running = False

        if self._timer is not None:
            self._timer.stop()

        if self._audio_thread is not None:
            self._audio_thread.join(timeout=2)
        if self._process_thread is not None:
            self._process_thread.join(timeout=2)

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
