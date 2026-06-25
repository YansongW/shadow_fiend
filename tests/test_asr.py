"""
ASR 模块单元测试。
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from asr.sensevoice import ASRModule


def test_extract_language():
    text = "<|ja|><|NEUTRAL|><|Speech|><|withitn|>こんにちは"
    assert ASRModule._extract_language(text) == "ja"


def test_extract_language_chinese():
    text = "<|zh|><|NEUTRAL|><|Speech|><|withitn|>你好"
    assert ASRModule._extract_language(text) == "zh"


def test_strip_tags():
    text = "<|ja|><|NEUTRAL|><|Speech|><|withitn|>こんにちは"
    assert ASRModule._strip_tags(text) == "こんにちは"


def test_resolve_device_auto():
    asr = ASRModule(device="cpu")
    assert asr.device == "cpu"
