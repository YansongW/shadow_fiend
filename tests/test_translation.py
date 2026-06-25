"""
翻译模块单元测试。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from translation.argos_engine import TranslationModule


def test_same_language_returns_original():
    translator = TranslationModule("en", "en", auto_install=False)
    assert translator.translate("Hello") == "Hello"


def test_empty_text():
    translator = TranslationModule("en", "zh", auto_install=False)
    assert translator.translate("") == ""
    assert translator.translate("   ") == ""


def test_unsupported_source_language():
    with pytest.raises(ValueError):
        TranslationModule("fr", "zh", auto_install=False)


def test_unsupported_target_language():
    with pytest.raises(ValueError):
        TranslationModule("en", "fr", auto_install=False)
