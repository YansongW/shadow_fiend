"""
翻译模块：基于 Argos Translate 的本地离线翻译。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Argos language codes we care about.
SUPPORTED_LANGS = {"zh", "en", "ja", "ko"}


class TranslationModule:
    """
    使用 Argos Translate 进行本地离线翻译。

    如果直接语言包不存在，会尝试通过英语 pivot（中转）。
    """

    def __init__(self, source_lang: str, target_lang: str, auto_install: bool = True):
        if source_lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported source language: {source_lang}")
        if target_lang not in SUPPORTED_LANGS:
            raise ValueError(f"Unsupported target language: {target_lang}")

        self.source_lang = source_lang
        self.target_lang = target_lang
        self.auto_install = auto_install
        self._translation = None
        self._installed_languages = None

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
        """检查 Argos 索引中是否存在某语言包。"""
        try:
            from argostranslate import package
            package.update_package_index()
            available = package.get_available_packages()
            return any(
                p.from_code == from_code and p.to_code == to_code for p in available
            )
        except Exception:
            return False

    def _load_translation(self):
        """加载翻译对象。"""
        if self._translation is not None:
            return

        self._ensure_packages()

        try:
            from argostranslate import translate
        except ImportError as e:
            raise RuntimeError(
                "Argos Translate is not installed. Please run: ./scripts/setup.sh"
            ) from e

        self._installed_languages = translate.get_installed_languages()
        from_lang = self._get_language(self.source_lang)
        to_lang = self._get_language(self.target_lang)

        if from_lang is None or to_lang is None:
            raise RuntimeError(
                f"Could not find Argos languages for {self.source_lang} -> {self.target_lang}. "
                f"Installed languages: {[l.code for l in self._installed_languages]}"
            )

        self._translation = from_lang.get_translation(to_lang)
        if self._translation is None:
            # Try pivot via English.
            en_lang = self._get_language("en")
            if en_lang is None:
                raise RuntimeError(
                    f"No direct translation {self.source_lang} -> {self.target_lang} "
                    f"and English pivot is unavailable."
                )
            self._from_to_en = from_lang.get_translation(en_lang)
            self._en_to_target = en_lang.get_translation(to_lang)
        else:
            self._from_to_en = None
            self._en_to_target = None

    def _get_language(self, code: str):
        """从已安装语言中查找指定语言。"""
        for lang in self._installed_languages:
            if lang.code == code:
                return lang
        return None

    def translate(self, text: str) -> str:
        """翻译文本。"""
        if not text or not text.strip():
            return ""

        if self.source_lang == self.target_lang:
            return text

        self._load_translation()

        if self._translation is not None:
            return self._translation.translate(text)

        # Pivot via English.
        english = self._from_to_en.translate(text)
        return self._en_to_target.translate(english)
