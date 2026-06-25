#!/usr/bin/env python3
"""
测试字幕浮窗 UI。

用法：
    ./scripts/test_ui.py

会显示一个浮窗，并每隔几秒更新字幕内容。
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PyQt6.QtCore import QTimer
from ui.subtitle_window import SubtitleWindow


def main():
    print("shadow_fiend UI test")
    print("Close the subtitle window to exit.")

    window = SubtitleWindow(source_lang="ja", target_lang="zh")
    window.show()

    demo_subtitles = [
        ("こんにちは", "你好"),
        ("お元気ですか", "你好吗"),
        ("これはテストです", "这是测试"),
    ]

    timer = QTimer()
    index = [0]

    def update():
        source, translated = demo_subtitles[index[0] % len(demo_subtitles)]
        window.show_text(source, translated)
        index[0] += 1

    timer.timeout.connect(update)
    timer.start(2000)
    update()

    window._app.exec()


if __name__ == "__main__":
    main()
