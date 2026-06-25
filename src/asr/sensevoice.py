"""
ASR 模块：基于 SenseVoice-Small 的本地语音识别。
"""

import logging
import re
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Mapping from SenseVoice language tags to ISO codes.
LANG_TAG_MAP = {
    "zh": "zh",
    "en": "en",
    "ja": "ja",
    "ko": "ko",
    "yue": "yue",
}

LANG_TAG_PATTERN = re.compile(r"<\|([a-z]+)\|>")
ALL_TAGS_PATTERN = re.compile(r"<\|[^|]+\|>")


class ASRModule:
    """
    使用 FunASR + SenseVoice-Small 进行本地语音识别。
    """

    def __init__(
        self,
        model_name: str = "iic/SenseVoiceSmall",
        device: str = "auto",
        use_vad: bool = True,
    ):
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self.use_vad = use_vad
        self._model = None
        self._vad_model = "fsmn-vad" if use_vad else None

    def _resolve_device(self, device: str) -> str:
        """解析 device 参数，auto 时优先使用 mps/cuda。"""
        if device != "auto":
            return device

        try:
            import torch
            if torch.backends.mps.is_available():
                return "mps"
            if torch.cuda.is_available():
                return "cuda:0"
        except ImportError:
            pass

        return "cpu"

    def _load_model(self):
        """延迟加载模型。"""
        if self._model is not None:
            return

        logger.info("Loading SenseVoice model '%s' on device '%s'", self.model_name, self.device)

        try:
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
        except ImportError as e:
            raise RuntimeError(
                "FunASR is not installed. Please run: ./scripts/setup.sh"
            ) from e

        kwargs = {"model": self.model_name, "device": self.device}
        if self._vad_model:
            kwargs["vad_model"] = self._vad_model
            kwargs["vad_kwargs"] = {"max_single_segment_time": 30000}

        self._model = AutoModel(**kwargs)
        self._postprocess = rich_transcription_postprocess

    def transcribe(self, audio: np.ndarray, language: str = "auto") -> dict:
        """
        对音频进行语音识别。

        Args:
            audio: float32 numpy array in range [-1.0, 1.0].
            language: "auto" or one of "zh", "en", "ja", "ko".

        Returns:
            {"text": str, "language": str}
        """
        self._load_model()

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        res = self._model.generate(
            input=audio,
            cache={},
            language=language,
            use_itn=True,
        )
        raw_text = self._postprocess(res[0]["text"])
        detected_lang = self._extract_language(raw_text) or language
        clean_text = self._strip_tags(raw_text)

        return {
            "text": clean_text,
            "language": detected_lang,
        }

    @staticmethod
    def _extract_language(text: str) -> Optional[str]:
        """从 SenseVoice 输出中提取语言标签。"""
        for match in LANG_TAG_PATTERN.finditer(text):
            tag = match.group(1)
            if tag in LANG_TAG_MAP:
                return LANG_TAG_MAP[tag]
        return None

    @staticmethod
    def _strip_tags(text: str) -> str:
        """去掉 SenseVoice 的所有特殊标签。"""
        return ALL_TAGS_PATTERN.sub("", text).strip()
