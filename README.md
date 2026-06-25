# YiMu（译幕）

> 一个开源、免费、本地优先的实时字幕翻译器。
> 专注于中日韩影视剧，无需官方字幕也能看懂。

## 项目愿景

让每个人都能在自己设备上免费获得高质量、低延迟、隐私安全的实时翻译字幕。

- **开源免费**：核心代码 MIT 协议，任何人可自由使用、修改、分发。
- **本地优先**：默认离线运行，音频和翻译不上传云端。
- **专注观影**：系统音频捕获 + 半透明浮窗，专为看电影、追剧、直播设计。
- **中日韩优化**：优先支持中文、日语、韩语与英语之间的互译。

## 当前阶段

本项目处于早期开发阶段，正在实现 **MVE（Minimum Viable Experience）**：
在 macOS 上，把播放器的声音实时转成中日韩/英文字幕并显示在屏幕上。

## 技术栈

- **平台**：macOS（MVE），后续支持 Windows / Linux
- **语言**：Python 3.10+
- **UI**：PyQt6 / PyObjC 浮窗
- **ASR（语音识别）**：SenseVoice-Small（本地，支持中日韩）
- **翻译**：Argos Translate / LibreTranslate（本地轻量），可选本地 LLM
- **音频捕获**：BlackHole 虚拟声卡 / ScreenCaptureKit

## 前置要求

- macOS 12+（MVE 阶段仅支持 Apple Silicon）
- Python 3.10+
- Homebrew
- BlackHole 2ch 虚拟声卡（setup.sh 会自动安装）

## 快速开始

```bash
git clone https://github.com/YOUR_USERNAME/yimu.git
cd yimu
./scripts/setup.sh        # 安装依赖、BlackHole、portaudio
./scripts/run.sh --source ja --target zh
```

> 注意：首次运行前需要在 **Audio MIDI Setup** 中创建一个 Multi-Output Device，
> 同时勾选你的扬声器/耳机和 **BlackHole 2ch**，并将其设为系统输出。

> 详细文档待 MVE 完成后补充。

## 项目结构

```
yimu/
├── README.md           # 项目说明
├── AGENTS.md           # AI 协作指南
├── ROADMAP.md          # 路线图
├── CHANGELOG.md        # 变更日志
├── .gitignore
├── src/
│   ├── audio/          # 音频捕获
│   ├── asr/            # 语音识别
│   ├── translation/    # 翻译
│   ├── ui/             # 字幕浮窗
│   └── pipeline.py     # 主流程编排
├── tests/              # 单元测试
├── scripts/            # 安装/启动脚本
└── docs/               # 文档
```

## 贡献

欢迎 Issue 和 PR。请先阅读 `AGENTS.md` 了解项目约定。

## 许可

MIT License
