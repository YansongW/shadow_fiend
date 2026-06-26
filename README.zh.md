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
- 🚀 **流式低延迟 ASR** — SenseVoice-Small + Silero VAD + 500 ms 滑动窗口
- 🔇 **实时降噪** — RNNoise 在识别前降低背景噪声
- 🌐 **本地翻译** — 优先使用 Helsinki-NLP/opus-mt，Argos Translate 回退
- 🎨 **浮窗字幕** — 透明、置顶、可拖拽
- 🖥️ **系统托盘 / 菜单栏** — 开始/暂停、降噪开关、样式、位置、点击穿透、SRT 导出
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

v0.0.3 已发布。核心模块已实现并验证：

- ✅ 音频捕获（BlackHole + PyAudio）
- ✅ Silero VAD 切句
- ✅ 流式 SenseVoice ASR（500 ms 窗口 / 200 ms hop）
- ✅ RNNoise 实时降噪（16 kHz I/O，内部 48 kHz）
- ✅ opus-mt 直译引擎，Argos 回退
- ✅ PyQt6 字幕浮窗 + 系统托盘控制器
- ✅ 流式端到端 pipeline

已在 macOS Apple Silicon + BlackHole 2ch 上完成端到端实时演示验证。

> **测试代码**维护在 [`test`](https://github.com/YansongW/shadow_fiend/tree/test) 分支。详见 [`ROADMAP.md`](ROADMAP.md)。

## Docker

镜像已发布到 **GitHub Packages**，用于可复现的开发和无 GUI 测试：

```bash
docker pull ghcr.io/yansongw/shadow_fiend:latest
```

#### 无界面 / CI 用法

```bash
docker run --rm ghcr.io/yansongw/shadow_fiend:latest --help
```

#### GUI 用法（X11 转发）

> Docker 中运行 GUI 为可选项，日常观影仍建议使用本地安装。

```bash
# macOS：允许 XQuartz 连接
xhost +localhost

# 转发 X11 socket 运行
docker run --rm -e DISPLAY=host.docker.internal:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ghcr.io/yansongw/shadow_fiend:latest --source ja --target zh
```

该镜像通过 [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml) 在每次 GitHub Release 时自动构建发布。默认发布平台为 `linux/amd64`；如需 `linux/arm64`，可通过 workflow 的 `platforms` 输入添加。

> Docker 无法直接访问 macOS 音频硬件，端到端 demo 仍需 macOS + BlackHole 2ch。

## 运行测试

测试代码与基准数据位于 [`test`](https://github.com/YansongW/shadow_fiend/tree/test) 分支。切换到该分支后：

```bash
./.venv/bin/python -m pytest tests/ -v
```

## 项目结构

```
shadow_fiend/
├── README.md
├── README.zh.md
├── README.ko.md
├── CHANGELOG.md
├── ROADMAP.md
├── setup.py
├── pyproject.toml
├── Dockerfile
├── src/
│   ├── audio/                # 音频捕获 + Silero VAD
│   ├── asr/                  # SenseVoice ASR + 流式封装
│   ├── translation/          # opus-mt 引擎 + Argos 回退
│   ├── ui/                   # 字幕浮窗 + 托盘控制器
│   ├── pipeline_streaming.py # 流式流程编排
│   └── main.py               # CLI 入口
├── scripts/                  # 安装 / 运行辅助脚本
├── tests/                    # 基准测试（test 分支）
└── assets/                   # Logo 文件
```

## 商标声明

"Shadow Fiend" 是 Valve Corporation 旗下《Dota 2》中的角色名。本项目是独立的开源字幕翻译工具，与 Valve Corporation 或《Dota 2》无任何关联、认可或赞助关系。

## 许可

MIT License
