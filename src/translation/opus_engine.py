"""
opus-mt 直接翻译引擎。

使用 Helsinki-NLP/opus-mt 系列模型进行本地离线翻译。
支持直接语言对；中日/中韩等无直接模型时，通过英语 pivot 完成翻译。
"""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _deduplicate_repeated_tokens(text: str, max_repeat: int = 3) -> str:
    """
    检测并截断连续重复 token 导致的退化输出。

    例如 opus-mt-en-zh 对无标点短输入可能生成：
        "你好 你好 你好 你好 ..."
    该函数会将其截断为：
        "你好"

    规则：若某个 token（或带标点的变体）连续重复超过 max_repeat 次，
    则只保留第一次出现。
    """
    if not text:
        return text

    # 按空白切分 token
    tokens = text.split()
    if len(tokens) < max_repeat + 1:
        return text

    # 检测连续重复的最小单元（1 个或 2 个 token）
    for unit_len in (1, 2):
        for start in range(len(tokens) - unit_len * max_repeat + 1):
            unit = tokens[start : start + unit_len]
            repeats = 1
            pos = start + unit_len
            while pos + unit_len <= len(tokens) and tokens[pos : pos + unit_len] == unit:
                repeats += 1
                pos += unit_len
            if repeats > max_repeat:
                # 截断：保留第一次出现，加适当标点后的内容
                prefix = " ".join(tokens[: start + unit_len])
                # 如果原句有结尾标点，尽量保留
                tail = " ".join(tokens[start + unit_len : start + unit_len * 2])
                if tail and tail[-1] in {"，", "。", "！", "？", ",", ".", "!", "?"}:
                    prefix += tail[-1]
                return prefix
    return text


def _dynamic_max_length(input_token_count: int, min_len: int = 24, max_len: int = 128) -> int:
    """
    根据输入 token 数动态决定 decode 的最大长度。

    短句不需要 decode 到 128，避免无标点输入触发重复生成。
    正常句子保留足够空间，防止过早截断有效内容。
    """
    target = input_token_count * 3 + 16
    return max(min_len, min(target, max_len))


class _OpusTranslator:
    """单个 opus-mt 语言对的轻量封装，支持延迟加载、warmup 与复用。"""

    # 高频短句缓存：只缓存长度较短的输入，避免内存无限增长
    _CACHE_MAX_LEN = 32
    _CACHE_SIZE = 512

    def __init__(
        self,
        model_name: str,
        device: str,
        cache_dir: str,
        warmup: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self._warmup = warmup
        self._tokenizer = None
        self._model = None
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        logger.info("Loading opus-mt model '%s' on device '%s'", self.model_name, self.device)
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as e:
            raise RuntimeError(
                "transformers is not installed. Please run: ./scripts/setup.sh"
            ) from e

        # 设置缓存目录一致
        os.environ.setdefault("HF_HOME", self.cache_dir)
        os.environ.setdefault("TRANSFORMERS_CACHE", self.cache_dir)

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            cache_dir=self.cache_dir,
        )
        self._model = AutoModelForSeq2SeqLM.from_pretrained(
            self.model_name,
            cache_dir=self.cache_dir,
        )
        if self.device:
            self._model.to(self.device)
        self._model.eval()
        self._loaded = True

        if self._warmup:
            logger.debug("Warming up opus-mt model '%s'", self.model_name)
            self._translate_impl("hello", use_cache=False)

    @lru_cache(maxsize=_CACHE_SIZE)
    def _cached_translate(self, text: str) -> str:
        """LRU 缓存层：对高频短句复用翻译结果。"""
        return self._translate_impl(text, use_cache=False)

    def _translate_impl(self, text: str, use_cache: bool = True) -> str:
        if not text:
            return ""
        if use_cache and len(text) <= self._CACHE_MAX_LEN:
            return self._cached_translate(text)

        self._load()
        import torch

        inputs = self._tokenizer(text, return_tensors="pt", padding=True)
        input_len = inputs["input_ids"].shape[1]
        max_length = _dynamic_max_length(input_len)

        if self.device:
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                num_beams=1,
                max_length=max_length,
            )
        raw = self._tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].strip()
        return _deduplicate_repeated_tokens(raw)

    def translate(self, text: str) -> str:
        return self._translate_impl(text)


class OpusEngine:
    """
    Helsinki-NLP/opus-mt 翻译引擎。

    支持语言对：
    - 直接：en<->zh, zh<->en, ja->en, ko->en, en->ja, en->ko 等 HF 上存在的 opus-mt 对
    - pivot：ja->zh（ja->en->zh）、ko->zh（ko->en->zh）等通过英语中转的对
    """

    # 实际存在于 Hugging Face 的直接 opus-mt 语言对（本项目关心的范围）
    DIRECT_PAIRS = {
        ("en", "zh"),
        ("zh", "en"),
        ("ja", "en"),
        ("ko", "en"),
        ("en", "ja"),
        ("en", "ko"),
    }

    # 可通过英语 pivot 支持的对
    PIVOT_PAIRS = {
        ("ja", "zh"),
        ("ko", "zh"),
        ("ja", "ko"),
        ("ko", "ja"),
    }

    MODEL_MAP = {
        ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
        ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
        ("ja", "en"): "Helsinki-NLP/opus-mt-ja-en",
        ("ko", "en"): "Helsinki-NLP/opus-mt-ko-en",
        ("en", "ja"): "Helsinki-NLP/opus-mt-en-jap",  # HF 使用 jap 作为目标代码
        ("en", "ko"): "Helsinki-NLP/opus-mt-en-ko",
    }

    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        device: str = "auto",
        cache_dir: Optional[str] = None,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.device = self._resolve_device(device)
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/shadow_fiend/opus-mt")
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

        self._direct: Optional[_OpusTranslator] = None
        self._pivot: Optional[_OpusTranslator] = None
        self._is_pivot = False

        self._load_model()

    @classmethod
    def is_supported(cls, source_lang: str, target_lang: str) -> bool:
        """检查是否支持该语言对（直接或 pivot）。"""
        pair = (source_lang, target_lang)
        return pair in cls.DIRECT_PAIRS or pair in cls.PIVOT_PAIRS

    @staticmethod
    def _resolve_device(device: str) -> Optional[str]:
        """解析 device 参数。

        实测 MarianMT 小模型在 Apple Silicon MPS 上反而慢于 CPU，
        因此 opus-mt 的 auto 默认优先 CPU，避免拖累实时翻译。
        """
        if device == "auto":
            return "cpu"
        if device in {"cpu", "cuda", "mps"}:
            return device
        return None

    def _model_name_for(self, source_lang: str, target_lang: str) -> Optional[str]:
        pair = (source_lang, target_lang)
        return self.MODEL_MAP.get(pair)

    def _load_model(self) -> None:
        pair = (self.source_lang, self.target_lang)

        # 同语言直接返回
        if self.source_lang == self.target_lang:
            return

        # 直接对
        if pair in self.DIRECT_PAIRS:
            model_name = self._model_name_for(self.source_lang, self.target_lang)
            if model_name is None:
                raise RuntimeError(f"opus-mt direct model not configured for {pair}")
            self._direct = _OpusTranslator(model_name, self.device, self.cache_dir)
            return

        # 通过英语 pivot
        if pair in self.PIVOT_PAIRS:
            src_to_en = self._model_name_for(self.source_lang, "en")
            en_to_tgt = self._model_name_for("en", self.target_lang)
            if src_to_en is None or en_to_tgt is None:
                raise RuntimeError(
                    f"opus-mt pivot path not available for {self.source_lang}->{self.target_lang}"
                )
            self._direct = _OpusTranslator(src_to_en, self.device, self.cache_dir)
            self._pivot = _OpusTranslator(en_to_tgt, self.device, self.cache_dir)
            self._is_pivot = True
            return

        raise RuntimeError(
            f"opus-mt does not support {self.source_lang}->{self.target_lang}"
        )

    def translate(self, text: str) -> str:
        """翻译文本。"""
        if not text or self.source_lang == self.target_lang:
            return text

        start = time.perf_counter()
        if not self._is_pivot:
            result = self._direct.translate(text)
        else:
            english = self._direct.translate(text)
            result = self._pivot.translate(english)
        elapsed = time.perf_counter() - start
        logger.debug(
            "opus-mt %s %s->%s: %.0f ms",
            "pivot" if self._is_pivot else "direct",
            self.source_lang,
            self.target_lang,
            elapsed * 1000,
        )
        return result
