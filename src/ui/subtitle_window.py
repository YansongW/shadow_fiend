"""
字幕浮窗 UI 模块。

使用 PyQt6 实现一个半透明、置顶、可拖拽的窗口，用于显示原文和译文。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SubtitleWindow:
    """
    半透明双语字幕浮窗。
    """

    def __init__(
        self,
        source_lang: str = "ja",
        target_lang: str = "zh",
        compact: bool = False,
    ):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.compact = compact
        self._app = None
        self._window = None
        self._source_label = None
        self._translated_label = None
        self._drag_pos = None

    def _ensure_qt(self):
        """延迟初始化 Qt 对象。"""
        if self._app is not None:
            return

        try:
            from PyQt6 import QtCore, QtGui, QtWidgets
        except ImportError as e:
            raise RuntimeError(
                "PyQt6 is not installed. Please run: ./scripts/setup.sh"
            ) from e

        self._QtCore = QtCore
        self._QtGui = QtGui
        self._QtWidgets = QtWidgets

        self._app = QtWidgets.QApplication.instance()
        if self._app is None:
            self._app = QtWidgets.QApplication([])

        self._window = QtWidgets.QWidget()
        self._window.setWindowTitle("Shadow Fiend")
        self._window.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self._window.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self._window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        # Main layout.
        self._layout = QtWidgets.QVBoxLayout(self._window)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(8)

        # Source text label.
        self._source_label = QtWidgets.QLabel("等待音频...")
        self._source_label.setWordWrap(True)
        self._source_label.setStyleSheet(
            "color: white; font-size: 18px; font-weight: bold;"
        )
        self._source_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._layout.addWidget(self._source_label)

        # Translated text label.
        self._translated_label = QtWidgets.QLabel("")
        self._translated_label.setWordWrap(True)
        self._translated_label.setStyleSheet(
            "color: #f0f0f0; font-size: 16px;"
        )
        self._translated_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._layout.addWidget(self._translated_label)

        # Background container.
        self._container = QtWidgets.QWidget()
        self._container.setStyleSheet("background-color: rgba(0, 0, 0, 180); border-radius: 12px;")
        self._container.setLayout(self._layout)

        outer_layout = QtWidgets.QVBoxLayout(self._window)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._container)
        self._window.setLayout(outer_layout)

        # Default size and position.
        self._window.resize(720, 140)
        screen = self._app.primaryScreen().geometry()
        self._window.move(
            (screen.width() - self._window.width()) // 2,
            int(screen.height() * 0.75),
        )

        # Enable dragging.
        self._window.mousePressEvent = self._on_mouse_press
        self._window.mouseMoveEvent = self._on_mouse_move

    def _on_mouse_press(self, event):
        if event.button() == self._QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()

    def _on_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() == self._QtCore.Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def show_text(self, source: str, translated: str) -> None:
        """更新字幕内容。"""
        self._ensure_qt()
        self._source_label.setText(source)
        if self.compact:
            self._translated_label.setVisible(False)
        else:
            self._translated_label.setVisible(True)
            self._translated_label.setText(translated)

    def show(self) -> None:
        """显示浮窗。"""
        self._ensure_qt()
        self._window.show()

    def close(self) -> None:
        """关闭浮窗。"""
        if self._window is not None:
            self._window.close()

    def run(self) -> None:
        """启动 Qt 事件循环。"""
        self.show()
        self._app.exec()
