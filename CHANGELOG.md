# Changelog

## [0.0.1] - 2026-06-25

shadow_fiend 首个 MVE 版本。

### Added
- 项目初始化：创建 shadow_fiend项目骨架。
- 添加 README.md、AGENTS.md、ROADMAP.md、CHANGELOG.md。
- 初始化 Git 仓库和 Python 项目结构。
- 添加 setup.sh / run.sh 脚本。
- 设计 MVE 技术方案（docs/mve_design.md）。
- 音频捕获模块（PyAudio + BlackHole）。
- 简单能量阈值 VAD 模块。
- ASR 模块（FunASR + SenseVoice-Small）。
- 翻译模块（Argos Translate，支持 direct 和 English pivot）。
- 字幕浮窗 UI（PyQt6 透明窗口）。
- 端到端 pipeline 和 CLI 入口（src/main.py）。
- 单元测试覆盖所有模块（15 tests passing）。

### Changed
- setup.sh / README 明确要求 Python 3.10+。
- setup.sh 自动发现系统中可用的 Python 3.10+ 解释器（含 miniconda3）。
- run.sh 优先使用 .venv-test 环境，自动设置模型缓存路径，并修复模块导入路径。

### Fixed
- pipeline 中 ASR 模型延迟加载导致首次 utterance 处理时音频队列溢出的问题；启动时预加载 ASR 模型。
- Qt timer 跨线程停止警告（`QObject::killTimer: Timers cannot be stopped from another thread`）。
- 音频捕获以设备原生采样率（如 BlackHole 2ch 的 48000 Hz）打开 PyAudio 流，再用 scipy 重采样到 16000 Hz，避免 PyAudio 内置重采样导致的音质劣化。

### Added
- CLI 新增 `--asr-device` 参数，可显式指定 ASR 推理设备（auto/cpu/cuda/mps）。
- macOS 双击启动脚本：`安装 shadow_fiend.command`、`启动 shadow_fiend.command`。

### Repository
- 创建 `test` 分支保留所有测试代码与测试工具。
- `main` 分支仅保留应用核心代码、脚本与文档，测试相关文件迁移至 `test` 分支。

### Verified
- 单元测试 15/15 通过（见 `test` 分支）。
- 端到端 demo 跑通：通过 BlackHole 2ch 捕获日语/韩语测试音频，经 SenseVoice 识别、Argos 翻译后输出中文字幕。

## [Unreleased]

### Added
- CLI 新增 VAD 参数：`--max-utterance-ms`、`--min-silence-ms`、`--min-speech-ms`。
- 字幕样式设置面板：右键浮窗可调整原/译文字号、颜色、背景透明度与窗口位置。
- 右键菜单支持导出 SRT 字幕文件。
- 窗口位置记忆：拖拽浮窗后自动记住自定义位置。
- 右键菜单支持切换点击穿透模式。

### Changed
- 默认 VAD 参数调整为更低延迟：`max_utterance_ms=5000`、`min_silence_ms=350`、`min_speech_ms=200`。

### Fixed
- 字幕浮窗右键菜单与点击穿透的稳定性。
