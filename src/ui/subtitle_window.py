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
        self._export_srt_callback: Optional[callable] = None

        # Default appearance settings.
        self._style = {
            "source_font_size": 18,
            "translated_font_size": 16,
            "source_color": "#ffffff",
            "translated_color": "#f0f0f0",
            "background_alpha": 180,
            "position": "bottom",
        }

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
        self._window.setWindowTitle("shadow_fiend")
        self._window.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self._window.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self._window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        # Enable context menu (right-click) and click-through toggle.
        self._window.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._window.customContextMenuRequested.connect(self._show_context_menu)

        # Main layout.
        self._layout = QtWidgets.QVBoxLayout(self._window)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(8)

        # Source text label.
        self._source_label = QtWidgets.QLabel("等待音频...")
        self._source_label.setWordWrap(True)
        self._source_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._layout.addWidget(self._source_label)

        # Translated text label.
        self._translated_label = QtWidgets.QLabel("")
        self._translated_label.setWordWrap(True)
        self._translated_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._layout.addWidget(self._translated_label)

        # Background container.
        self._container = QtWidgets.QWidget()
        self._container.setLayout(self._layout)

        outer_layout = QtWidgets.QVBoxLayout(self._window)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._container)
        self._window.setLayout(outer_layout)

        # Default size and position.
        self._window.resize(720, 140)
        self._apply_position()
        self._apply_styles()

        # Enable dragging.
        self._window.mousePressEvent = self._on_mouse_press
        self._window.mouseMoveEvent = self._on_mouse_move

    def _apply_styles(self):
        """根据当前样式配置更新控件外观。"""
        alpha = self._style["background_alpha"]
        self._container.setStyleSheet(
            f"background-color: rgba(0, 0, 0, {alpha}); border-radius: 12px;"
        )
        self._source_label.setStyleSheet(
            f"color: {self._style['source_color']}; "
            f"font-size: {self._style['source_font_size']}px; "
            f"font-weight: bold;"
        )
        self._translated_label.setStyleSheet(
            f"color: {self._style['translated_color']}; "
            f"font-size: {self._style['translated_font_size']}px;"
        )

    def _apply_position(self):
        """根据当前位置配置调整窗口位置。"""
        screen = self._app.primaryScreen().geometry()
        x = (screen.width() - self._window.width()) // 2
        position = self._style.get("position", "bottom")
        if position == "top":
            y = int(screen.height() * 0.15)
        elif position == "center":
            y = (screen.height() - self._window.height()) // 2
        else:  # bottom
            y = int(screen.height() * 0.75)
        self._window.move(x, y)

    def _on_mouse_press(self, event):
        if event.button() == self._QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()

    def _on_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() == self._QtCore.Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def set_export_srt_callback(self, callback: callable) -> None:
        """设置导出 SRT 文件时的回调函数。"""
        self._export_srt_callback = callback

    def _show_context_menu(self, pos):
        """显示右键菜单。"""
        menu = self._QtWidgets.QMenu(self._window)
        style_action = menu.addAction("样式设置...")
        export_srt_action = menu.addAction("导出 SRT...")
        toggle_clickthrough = menu.addAction("切换点击穿透")
        action = menu.exec(self._window.mapToGlobal(pos))
        if action == style_action:
            self._open_style_dialog()
        elif action == export_srt_action:
            self._export_srt()
        elif action == toggle_clickthrough:
            self._toggle_click_through()

    def _export_srt(self):
        """弹出文件对话框并导出 SRT 字幕文件。"""
        if self._export_srt_callback is None:
            return
        path, _ = self._QtWidgets.QFileDialog.getSaveFileName(
            self._window,
            "导出 SRT 字幕",
            "shadow_fiend_subtitles.srt",
            "SRT files (*.srt)",
        )
        if path:
            try:
                self._export_srt_callback(path)
            except Exception as e:
                logger.error("Failed to export SRT: %s", e)

    def _toggle_click_through(self):
        """切换窗口是否接收鼠标事件（点击穿透）。"""
        flags = self._window.windowFlags()
        if flags & self._QtCore.Qt.WindowType.WindowTransparentForInput:
            flags &= ~self._QtCore.Qt.WindowType.WindowTransparentForInput
            logger.info("Click-through disabled")
        else:
            flags |= self._QtCore.Qt.WindowType.WindowTransparentForInput
            logger.info("Click-through enabled")
        self._window.setWindowFlags(flags)
        self._window.show()

    def _open_style_dialog(self):
        """打开样式设置对话框。"""
        dialog = self._QtWidgets.QDialog(self._window)
        dialog.setWindowTitle("字幕样式设置")
        layout = self._QtWidgets.QFormLayout(dialog)

        # Source font size.
        source_size_spin = self._QtWidgets.QSpinBox()
        source_size_spin.setRange(10, 64)
        source_size_spin.setValue(self._style["source_font_size"])
        layout.addRow("原文字号:", source_size_spin)

        # Translated font size.
        translated_size_spin = self._QtWidgets.QSpinBox()
        translated_size_spin.setRange(10, 64)
        translated_size_spin.setValue(self._style["translated_font_size"])
        layout.addRow("译文字号:", translated_size_spin)

        # Source color.
        source_color_btn = self._QtWidgets.QPushButton(self._style["source_color"])
        source_color_btn.setStyleSheet(
            f"background-color: {self._style['source_color']}; color: #000000;"
        )
        source_color_btn.clicked.connect(
            lambda: self._pick_color(source_color_btn, "source_color")
        )
        layout.addRow("原文颜色:", source_color_btn)

        # Translated color.
        translated_color_btn = self._QtWidgets.QPushButton(self._style["translated_color"])
        translated_color_btn.setStyleSheet(
            f"background-color: {self._style['translated_color']}; color: #000000;"
        )
        translated_color_btn.clicked.connect(
            lambda: self._pick_color(translated_color_btn, "translated_color")
        )
        layout.addRow("译文颜色:", translated_color_btn)

        # Background alpha.
        alpha_slider = self._QtWidgets.QSlider(self._QtCore.Qt.Orientation.Horizontal)
        alpha_slider.setRange(0, 255)
        alpha_slider.setValue(self._style["background_alpha"])
        layout.addRow("背景透明度:", alpha_slider)

        # Position.
        position_combo = self._QtWidgets.QComboBox()
        position_combo.addItems(["top", "center", "bottom"])
        position_combo.setCurrentText(self._style["position"])
        layout.addRow("窗口位置:", position_combo)

        # Buttons.
        buttons = self._QtWidgets.QDialogButtonBox(
            self._QtWidgets.QDialogButtonBox.StandardButton.Ok
            | self._QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == self._QtWidgets.QDialog.DialogCode.Accepted:
            self._style["source_font_size"] = source_size_spin.value()
            self._style["translated_font_size"] = translated_size_spin.value()
            self._style["background_alpha"] = alpha_slider.value()
            self._style["position"] = position_combo.currentText()
            self._apply_styles()
            self._apply_position()
            logger.info("Subtitle style updated: %s", self._style)

    def _pick_color(self, button, style_key):
        """弹出颜色选择器并更新临时样式键。"""
        color = self._QtWidgets.QColorDialog.getColor(
            self._QtGui.QColor(self._style[style_key]),
            self._window,
            "选择颜色",
        )
        if color.isValid():
            hex_color = color.name()
            self._style[style_key] = hex_color
            button.setText(hex_color)
            button.setStyleSheet(f"background-color: {hex_color}; color: #000000;")

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
