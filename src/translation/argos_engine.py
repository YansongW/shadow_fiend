"""
翻译模块：根据语言对自动选择最佳本地离线翻译引擎。

优先级：
1. Helsinki-NLP/opus-mt 直接语言对（v0.0.2 新增）
2. Argos Translate（保留兼容性）
"""

import logging
from typing import Optional

from translation.opus_engine import OpusEngine

logger = logging.getLogger(__name__)

# Argos language codes we care about.
SUPPORTED_LANGS = {"zh", "en", "ja", "ko"}


class TranslationModule:
    """
    本地离线翻译模块，自动选择 opus-mt 或 Argos Translate。
    """

    def __init__(
        self,
        source_lang: str,
        target_lang: str,
        auto_install: bool = True,
        device: str = "auto",
    ):
        if source_lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported source language: {source_lang}")
        if target_lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported target language: {target_lang}")

        self.source_lang = source_lang
        self.target_lang = target_lang
        self.auto_install = auto_install
        self.device = device

        self._engine = None
        self._engine_name: str = "unknown"
        self._load_engine()

    def _load_engine(self) -> None:
        """加载最佳可用翻译引擎。"""
        # Prefer opus-mt for direct language pairs.
        if OpusEngine.is_supported(self.source_lang, self.target_lang):
            try:
                self._engine = OpusEngine(
                    self.source_lang,
                    self.target_lang,
                    device=self.device,
                )
                self._engine_name = "opus-mt"
                logger.info(
                    "Using opus-mt engine for %s -> %s",
                    self.source_lang,
                    self.target_lang,
                )
                return
            except Exception as e:
                logger.warning(
                    "Failed to load opus-mt for %s -> %s: %s. Falling back to Argos.",
                    self.source_lang,
                    self.target_lang,
                    e,
                )

        # Fallback to Argos Translate.
        self._engine = _ArgosEngine(self.source_lang, self.target_lang, self.auto_install)
        self._engine_name = "argos"
        logger.info(
            "Using Argos engine for %s -> %s",
            self.source_lang,
            self.target_lang,
        )

    def translate(self, text: str) -> str:
        """翻译文本。"""
        if self._engine is None:
            raise RuntimeError("Translation engine not loaded")
        return self._engine.translate(text)


class _ArgosEngine:
    """
    内部 Argos Translate 引擎封装。
    """

    def __init__(self, source_lang: str, target_lang: str, auto_install: bool = True):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.auto_install = auto_install
        self._translation = None
        self._installed_languages = None
        self._from_to_en = None
        self._en_to_target = None

        self._ensure_packages()
        self._build_translations()

    def _ensure_packages(self) -> None:
        """确保所需语言包已安装。"""
        try:
            from argostranslate import package
        except ImportError as e:
            raise RuntimeError(
                "Argos Translate is not installed. Please run: ./scripts/setup.sh"
            ) from e

        installed = package.get_installed_packages()
        installed_pairs = {(p.from_code, p.to_code) for p in installed}

        needed = self._get_needed_pairs()
        for from_code, to_code in needed:
            if (from_code, to_code) not in installed_pairs:
                if not self.auto_install:
                    raise RuntimeError(
                        f"Missing Argos package {from_code} -> {to_code}. "
                        f"Run setup.sh or install manually."
                    )
                logger.info("Installing Argos package %s -> %s", from_code, to_code)
                package.update_package_index()
                available = package.get_available_packages()
                pkg = next(
                    (p for p in available if p.from_code == from_code and p.to_code == to_code),
                    None,
                )
                if pkg is None:
                    raise RuntimeError(
                        f"Argos package {from_code} -> {to_code} not available"
                    )
                package.install_from_path(pkg.download())

    def _get_needed_pairs(self):
        """返回需要的语言包对。直接包不存在时通过英语 pivot。"""
        if self.source_lang == self.target_lang:
            return []

        direct = (self.source_lang, self.target_lang)
        if self._package_exists_in_index(*direct):
            return [direct]

        # Fallback: translate via English.
        pairs = []
        if self.source_lang != "en":
            pairs.append((self.source_lang, "en"))
        if self.target_lang != "en":
            pairs.append(("en", self.target_lang))
        return pairs

    def _package_exists_in_index(self, from_code: str, to_code: str) -> bool:
        """检查索引中是否存在直接语言包。"""
        try:
            from argostranslate import package
            available = package.get_available_packages()
            return any(p.from_code == from_code and p.to_code == to_code for p in available)
        except Exception:
            return False

    def _build_translations(self) -> None:
        """构建翻译函数。"""
        try:
            from argostranslate import translate
        except ImportError as e:
            raise RuntimeError(
                "Argos Translate is not installed. Please run: ./scripts/setup.sh"
            ) from e

        self._installed_languages = translate.get_installed_languages()
        from_lang = next(
            (lang for lang in self._installed_languages if lang.code == self.source_lang),
            None,
        )
        to_lang = next(
            (lang for lang in self._installed_languages if lang.code == self.target_lang),
            None,
        )
        en_lang = next(
            (lang for lang in self._installed_languages if lang.code == "en"),
            None,
        )

        if from_lang is None:
            raise RuntimeError(f"Source language '{self.source_lang}' not installed in Argos")
        if to_lang is None:
            raise RuntimeError(f"Target language '{self.target_lang}' not installed in Argos")

        self._translation = from_lang.get_translation(to_lang)

        # Pre-build English pivot translations if needed.
        if self._translation is None:
            if en_lang is None:
                raise RuntimeError("English language package not installed in Argos")
            self._from_to_en = from_lang.get_translation(en_lang)
            self._en_to_target = en_lang.get_translation(to_lang)
            if self._from_to_en is None or self._en_to_target is None:
                raise RuntimeError(
                    f"Cannot translate {self.source_lang} -> {self.target_lang} via English: "
                    f"missing pivot packages"
                )

    def translate(self, text: str) -> str:
        """翻译文本。"""
        if not text:
            return ""
        if self._translation is not None:
            return self._translation.translate(text)
        english = self._from_to_en.translate(text)
        return self._en_to_target.translate(english)
