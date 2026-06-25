"""
UI 模块单元测试。

由于 PyQt6 需要 GUI 环境，这里只测试不依赖 Qt 的逻辑。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ui.subtitle_window import SubtitleWindow


def test_window_initial_state():
    window = SubtitleWindow(source_lang="ja", target_lang="zh")
    assert window.source_lang == "ja"
    assert window.target_lang == "zh"
    assert window.compact is False
    assert window._app is None


def test_compact_mode():
    window = SubtitleWindow(source_lang="en", target_lang="zh", compact=True)
    assert window.compact is True
