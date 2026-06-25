"""
YiMu 主流程编排模块。

负责把音频捕获、VAD、ASR、翻译、UI 串成一个实时 pipeline。
MVE 阶段保持简单，后续再引入更复杂的调度和错误恢复。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TranslationPipeline:
    """
    实时字幕翻译 pipeline。

    数据流：
        音频捕获 -> VAD 切句 -> ASR -> 翻译 -> UI 浮窗
    """

    def __init__(
        self,
        audio_source,
        vad,
        asr,
        translator,
        ui,
    ):
        self.audio_source = audio_source
        self.vad = vad
        self.asr = asr
        self.translator = translator
        self.ui = ui
        self._running = False

    def start(self) -> None:
        """启动 pipeline。"""
        logger.info("Starting YiMu translation pipeline")
        self._running = True
        # TODO: implement audio loop, VAD, ASR, translation, UI update
        raise NotImplementedError("MVE 1 will implement this")

    def stop(self) -> None:
        """停止 pipeline。"""
        logger.info("Stopping YiMu translation pipeline")
        self._running = False

    def is_running(self) -> bool:
        return self._running
