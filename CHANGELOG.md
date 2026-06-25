# Changelog

## [Unreleased]

### Added
- 项目初始化：创建 YingMo（影魔）项目骨架。
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

### Known Limitations
- 当前开发环境为 Python 3.9.6，无法安装 Argos Translate 完整依赖。
- SenseVoice 模型下载在当前网络环境下超时，端到端 demo 需在更合适环境验证。
