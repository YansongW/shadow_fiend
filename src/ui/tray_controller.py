"""
系统托盘 / 菜单栏控制器。

提供菜单栏图标、托盘菜单和设置入口。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TrayController:
    """
    包装 PyQt6 QSystemTrayIcon，提供菜单栏图标和菜单。
    """

    def __init__(
        self,
        parent,
        on_toggle_listening: Optional[Callable[[], None]] = None,
        on_style_settings: Optional[Callable[[], None]] = None,
        on_export_srt: Optional[Callable[[], None]] = None,
        on_position_top: Optional[Callable[[], None]] = None,
        on_position_center: Optional[Callable[[], None]] = None,
        on_position_bottom: Optional[Callable[[], None]] = None,
        on_toggle_click_through: Optional[Callable[[], None]] = None,
        on_about: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self._parent = parent
        self._on_toggle_listening = on_toggle_listening
        self._on_style_settings = on_style_settings
        self._on_export_srt = on_export_srt
        self._on_position_top = on_position_top
        self._on_position_center = on_position_center
        self._on_position_bottom = on_position_bottom
        self._on_toggle_click_through = on_toggle_click_through
        self._on_about = on_about
        self._on_quit = on_quit

        self._QtWidgets = None
        self._QtGui = None
        self._QtCore = None
        self._tray_icon = None
        self._menu = None
        self._listening = True

    def _ensure_qt(self) -> None:
        """Lazy import PyQt6 modules."""
        if self._QtWidgets is not None:
            return
        from PyQt6 import QtCore, QtGui, QtWidgets
        self._QtWidgets = QtWidgets
        self._QtGui = QtGui
        self._QtCore = QtCore

    def setup(self) -> bool:
        """创建托盘图标和菜单。返回是否成功。"""
        self._ensure_qt()
        if not self._QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this platform")
            return False

        self._tray_icon = self._QtWidgets.QSystemTrayIcon(self._parent)
        icon = self._load_icon()
        if icon is not None:
            self._tray_icon.setIcon(icon)
        self._tray_icon.setToolTip("shadow_fiend 影魔")

        self._menu = self._QtWidgets.QMenu(self._parent)
        self._build_menu()

        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.activated.connect(self._on_activated)
        self._tray_icon.show()
        return True

    def _load_icon(self) -> Optional["QtGui.QIcon"]:
        """加载项目 Logo 作为托盘图标。"""
        candidates = [
            # Installed wheel / source tree: src/ui/assets
            Path(__file__).parent / "assets",
            # Source tree run from repo root
            Path(__file__).parent.parent.parent / "assets",
            # Working directory
            Path.cwd() / "assets",
        ]
        for root in candidates:
            for size in [64, 128, 32, 256]:
                path = root / f"logo_{size}.png"
                if path.exists():
                    return self._QtGui.QIcon(str(path))
        logger.warning("No logo found for tray icon")
        return None

    def _build_menu(self) -> None:
        """构建托盘菜单。"""
        self._toggle_action = self._menu.addAction("暂停监听")
        self._toggle_action.triggered.connect(self._handle_toggle_listening)
        self._menu.addSeparator()

        self._style_action = self._menu.addAction("字幕样式...")
        self._style_action.triggered.connect(self._handle_style_settings)

        position_menu = self._menu.addMenu("位置")
        self._pos_top_action = position_menu.addAction("顶部")
        self._pos_top_action.triggered.connect(self._handle_position_top)
        self._pos_center_action = position_menu.addAction("居中")
        self._pos_center_action.triggered.connect(self._handle_position_center)
        self._pos_bottom_action = position_menu.addAction("底部")
        self._pos_bottom_action.triggered.connect(self._handle_position_bottom)

        self._click_through_action = self._menu.addAction("点击穿透")
        self._click_through_action.setCheckable(True)
        self._click_through_action.triggered.connect(self._handle_toggle_click_through)

        self._menu.addSeparator()

        self._export_action = self._menu.addAction("导出 SRT...")
        self._export_action.triggered.connect(self._handle_export_srt)

        self._menu.addSeparator()

        self._about_action = self._menu.addAction("关于")
        self._about_action.triggered.connect(self._handle_about)

        self._quit_action = self._menu.addAction("退出")
        self._quit_action.triggered.connect(self._handle_quit)

    def _on_activated(self, reason) -> None:
        """处理托盘图标激活事件。"""
        if reason == self._QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            # Left click: toggle listening.
            self._handle_toggle_listening()

    def _handle_toggle_listening(self) -> None:
        if self._on_toggle_listening:
            self._on_toggle_listening()

    def _handle_style_settings(self) -> None:
        if self._on_style_settings:
            self._on_style_settings()

    def _handle_export_srt(self) -> None:
        if self._on_export_srt:
            self._on_export_srt()

    def _handle_position_top(self) -> None:
        if self._on_position_top:
            self._on_position_top()

    def _handle_position_center(self) -> None:
        if self._on_position_center:
            self._on_position_center()

    def _handle_position_bottom(self) -> None:
        if self._on_position_bottom:
            self._on_position_bottom()

    def _handle_toggle_click_through(self) -> None:
        if self._on_toggle_click_through:
            self._on_toggle_click_through()

    def _handle_about(self) -> None:
        if self._on_about:
            self._on_about()
        else:
            self._QtWidgets.QMessageBox.about(
                self._parent,
                "关于 shadow_fiend",
                "shadow_fiend 影魔\n\n本地实时字幕翻译工具",
            )

    def _handle_quit(self) -> None:
        if self._on_quit:
            self._on_quit()
        else:
            self._QtWidgets.QApplication.instance().quit()

    def set_listening(self, listening: bool) -> None:
        """更新托盘菜单中的监听状态。"""
        self._listening = listening
        if self._toggle_action is not None:
            self._toggle_action.setText("暂停监听" if listening else "开始监听")

    def set_click_through(self, enabled: bool) -> None:
        """更新托盘菜单中的点击穿透状态。"""
        if self._click_through_action is not None:
            self._click_through_action.setChecked(enabled)

    def show_message(self, title: str, message: str, duration_ms: int = 3000) -> None:
        """显示托盘气泡消息。"""
        if self._tray_icon is not None:
            self._tray_icon.showMessage(
                title,
                message,
                self._QtWidgets.QSystemTrayIcon.MessageIcon.Information,
                duration_ms,
            )
