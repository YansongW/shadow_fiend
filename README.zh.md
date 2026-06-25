<div align="center">
  <img src="docs/logo.svg" width="160" alt="shadow_fiend logo">
  <h1>shadow_fiend</h1>
  <p><b>本地实时字幕翻译器，专为观影设计</b></p>
  <p>
    <a href="README.md">English</a> •
    <a href="README.ko.md">한국어</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/Platform-macOS%20Apple%20Silicon-black?style=flat-square&logo=apple" alt="macOS">
    <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
    <img src="https://img.shields.io/badge/Status-MVE-orange?style=flat-square" alt="MVE">
  </p>
</div>

---

> **让任何没有字幕的电影变得能看懂。**
> shadow_fiend 捕获系统音频，用 SenseVoice 本地识别语音，用 Argos 本地翻译，并在屏幕上实时显示双语字幕。

## 特性

- 🔒 **完全离线** — 音频不上传云端
- 🚀 **快速本地 ASR** — SenseVoice-Small，针对中日韩优化
- 🌐 **本地翻译** — Argos Translate 引擎，无需 API key
- 🎨 **浮窗字幕** — 透明、置顶、可拖拽
- 🎬 **专为观影设计** — 捕获任意播放器的系统音频

## 快速开始

### 前置要求

- macOS 12+（MVE 阶段仅支持 Apple Silicon）
- Python 3.10+
- Homebrew
- BlackHole 2ch 虚拟声卡

### 安装

```bash
git clone https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend
./scripts/setup.sh
```

### 配置 macOS 音频路由

1. 打开 `Audio MIDI Setup`（`/Applications/Utilities/Audio MIDI Setup.app`）
2. 点击左下角 `+` → **创建多输出设备**
3. 同时勾选你的扬声器/耳机和 **BlackHole 2ch**
4. 在系统设置中将其设为默认输出

### 运行

```bash
./scripts/run.sh --source ja --target zh
```

支持语言：`zh`、`en`、`ja`、`ko`。

## 开发状态

当前处于 MVE 阶段，核心模块已实现并通过单元测试：

- ✅ 音频捕获（BlackHole + PyAudio）
- ✅ VAD 切句
- ✅ SenseVoice ASR
- ✅ Argos 翻译
- ✅ PyQt6 字幕浮窗
- ✅ 端到端 pipeline

端到端实时演示需要在配备 Python 3.10+ 和 Homebrew 的 macOS 环境上验证。

## 一键测试

全自动流程：创建环境 → 单元测试 → 限时 demo → 打包日志 → 清理：

```bash
./scripts/one_click_test.sh
```

选项：
- `--no-cleanup` — 保留测试环境与下载的模型，方便排查
- `--duration <秒>` — 调整 demo 运行时长（默认 60 秒）

运行结束后会在 `test-reports/` 下生成 zip 报告，包含日志、环境信息和 pip 列表。

### 手动测试命令

```bash
python scripts/test_runner.py setup     # 创建 .venv-test 并下载模型
python scripts/test_runner.py test      # 运行 pytest
python scripts/test_runner.py demo --duration 30
python scripts/test_runner.py logs      # 打包报告 zip
python scripts/test_runner.py cleanup   # 删除 .venv-test、日志、模型
```

### Docker（仅无 GUI 单元测试）

```bash
./scripts/test_in_docker.sh
```

> Docker 无法访问 macOS 音频硬件和 GUI，因此只运行非 GUI/非音频单元测试。端到端 demo 仍需 macOS + BlackHole 2ch。

## 运行测试

```bash
./.venv/bin/python -m pytest tests/ -v
```

## 项目结构

```
shadow_fiend/
├── README.md
├── README.zh.md
├── README.ko.md
├── src/
│   ├── audio/       # 音频捕获 + VAD
│   ├── asr/         # SenseVoice 语音识别
│   ├── translation/ # Argos 翻译
│   ├── ui/          # 字幕浮窗
│   └── pipeline.py  # 流程编排
├── tests/
└── scripts/
```

## 商标声明

"Shadow Fiend" 是 Valve Corporation 旗下《Dota 2》中的角色名。本项目是独立的开源字幕翻译工具，与 Valve Corporation 或《Dota 2》无任何关联、认可或赞助关系。

## 许可

MIT License
