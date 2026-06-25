# shadow_fiend

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
- **Python 3.10+**（必须，因为 Argos Translate / Stanza 等依赖要求）
- Homebrew
- BlackHole 2ch 虚拟声卡（setup.sh 会自动安装）

## 快速开始

```bash
git clone https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend
./scripts/setup.sh        # 安装依赖、BlackHole、portaudio、ffmpeg
./scripts/run.sh --source ja --target zh
```

### macOS 音频路由设置

首次运行前，需要在 **Audio MIDI Setup** 中创建一个 Multi-Output Device：
1. 打开 `/Applications/Utilities/Audio MIDI Setup.app`
2. 点击左下角 `+` → **Create Multi-Output Device**
3. 同时勾选你的扬声器/耳机和 **BlackHole 2ch**
4. 在系统设置中将该 Multi-Output Device 设为默认输出

这样你既能听到视频声音，shadow_fiend 也能从 BlackHole 捕获到音频。

## 开发状态

shadow_fiend 处于早期 MVE 阶段。核心模块已实现并通过单元测试：
- ✅ 音频捕获
- ✅ VAD 切句
- ✅ SenseVoice ASR
- ✅ Argos 翻译
- ✅ PyQt6 字幕浮窗
- ✅ 端到端 pipeline

端到端实时演示需要在配备 Python 3.10+ 和 Homebrew 的 macOS 环境上验证。

## 运行测试

```bash
./.venv/bin/python -m pytest tests/ -v
```

## 模块测试

```bash
# 测试音频捕获（需配置 BlackHole）
./scripts/test_capture.py

# 测试 ASR（首次运行会下载 SenseVoice 模型）
./scripts/test_asr.py path/to/audio.wav

# 测试翻译
./scripts/test_translation.py --source en --target zh "Hello world"

# 测试 UI
./scripts/test_ui.py
```

## 商标声明

"shadow_fiend" 是 Valve Corporation 旗下 Dota 2 中的角色名。本项目是独立的开源字幕翻译工具，与 Valve Corporation 或 Dota 2 无任何关联、认可或赞助关系。本项目名称仅作为对游戏文化的致敬使用。

## 项目结构

```
shadow_fiend/
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
