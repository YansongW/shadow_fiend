<div align="center">
  <img src="docs/logo.svg" width="180" alt="shadow_fiend logo">
  <h1>shadow_fiend</h1>
  <p>
    <b>🎬 本地实时字幕翻译 · Local Real-time Subtitle Translation · 로컬 실시간 자막 번역</b>
  </p>
  <p>
    中日韩英离线观影字幕助手 | Offline subtitle assistant for C/J/K/E movies | 중일한영 오프라인 영화 자막 도우미
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/Platform-macOS%20(Apple%20Silicon)-black?style=flat-square&logo=apple" alt="macOS">
    <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
    <img src="https://img.shields.io/badge/Status-MVE%20in%20progress-orange?style=flat-square" alt="MVE">
  </p>

  <p>
    <a href="#快速开始">中文</a> •
    <a href="#quick-start">English</a> •
    <a href="#빠른-시작">한국어</a>
  </p>
</div>

---

## 快速开始

### 一句话介绍

**shadow_fiend** 是一个开源、免费、本地优先的实时字幕翻译器。播放没有字幕的日剧/韩剧/美剧时，它能把系统音频实时识别并翻译成中文，显示在屏幕浮窗上。

### ✨ 特性

- 🔒 **完全离线**：音频不上传云端，保护隐私
- 🚀 **本地 ASR**：SenseVoice-Small，中日韩识别快且准
- 🌐 **本地翻译**：Argos Translate 轻量翻译引擎
- 🎨 **透明浮窗**：PyQt6 半透明字幕，置顶可拖拽
- 🎬 **专为观影设计**：捕获系统音频，适配电影/剧集/直播

### 前置要求

- macOS 12+（MVE 阶段仅支持 Apple Silicon）
- **Python 3.10+**
- Homebrew
- BlackHole 2ch 虚拟声卡（setup.sh 会自动安装）

### 安装与运行

```bash
git clone https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend
./scripts/setup.sh
./scripts/run.sh --source ja --target zh
```

### macOS 音频路由

1. 打开 `/Applications/Utilities/Audio MIDI Setup.app`
2. 点击 `+` → **Create Multi-Output Device**
3. 同时勾选你的扬声器/耳机和 **BlackHole 2ch**
4. 在系统设置中将其设为默认输出

---

## Quick Start

### One-liner

**shadow_fiend** is an open-source, free, and local-first real-time subtitle translator. When watching Japanese/Korean/English movies without subtitles, it captures system audio, transcribes speech, and overlays translated Chinese subtitles on your screen.

### ✨ Features

- 🔒 **Fully offline**: audio never leaves your machine
- 🚀 **Local ASR**: SenseVoice-Small, fast and accurate for C/J/K
- 🌐 **Local translation**: Argos Translate lightweight engine
- 🎨 **Transparent overlay**: PyQt6 floating subtitle window
- 🎬 **Built for watching movies**: captures system-wide audio

### Requirements

- macOS 12+ (MVE targets Apple Silicon)
- **Python 3.10+**
- Homebrew
- BlackHole 2ch virtual audio driver (auto-installed by setup.sh)

### Install & Run

```bash
git clone https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend
./scripts/setup.sh
./scripts/run.sh --source ja --target zh
```

### macOS Audio Routing

1. Open `/Applications/Utilities/Audio MIDI Setup.app`
2. Click `+` → **Create Multi-Output Device**
3. Check both your speakers/headphones and **BlackHole 2ch**
4. Set it as the system default output

---

## 빠른 시작

### 한 줄 소개

**shadow_fiend**는 오픈소스이자 무상이며 로컬 우선의 실시간 자막 번역기입니다. 자막이 없는 일본/한국/영어 영화를 볼 때 시스템 오디오를 인식해 중국어로 번역한 자막을 화면에 표시합니다.

### ✨ 특징

- 🔒 **완전 오프라인**: 오디오가 클라우드로 업로드되지 않음
- 🚀 **로컬 ASR**: SenseVoice-Small, 중일한 인식이 빠르고 정확
- 🌐 **로컬 번역**: Argos Translate 가벼운 번역 엔진
- 🎨 **투명 오버레이**: PyQt6 플로팅 자막 창
- 🎬 **영화 시청용 설계**: 시스템 전체 오디오 캡처

### 요구사항

- macOS 12+ (MVE 단계에서는 Apple Silicon 대상)
- **Python 3.10+**
- Homebrew
- BlackHole 2ch 가상 오디오 드라이버 (setup.sh가 자동 설치)

### 설치 및 실행

```bash
git clone https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend
./scripts/setup.sh
./scripts/run.sh --source ko --target zh
```

### macOS 오디오 라우팅

1. `/Applications/Utilities/Audio MIDI Setup.app` 열기
2. `+` 클릭 → **Create Multi-Output Device**
3. 스피커/헤드폰과 **BlackHole 2ch** 모두 선택
4. 시스템 기본 출력으로 설정

---

## 开发状态 | Development Status | 개발 상태

当前处于 MVE 早期阶段，核心模块已实现并通过单元测试：

- ✅ Audio capture (BlackHole + PyAudio)
- ✅ Energy-threshold VAD
- ✅ SenseVoice ASR
- ✅ Argos Translate
- ✅ PyQt6 subtitle overlay
- ✅ End-to-end pipeline

端到端实时演示需要在配备 Python 3.10+ 和 Homebrew 的 macOS 环境上验证。

## 运行测试

```bash
./.venv/bin/python -m pytest tests/ -v
```

## 模块测试

```bash
./scripts/test_capture.py
./scripts/test_asr.py path/to/audio.wav
./scripts/test_translation.py --source en --target zh "Hello world"
./scripts/test_ui.py
```

## 项目结构

```
shadow_fiend/
├── README.md           # 项目说明
├── AGENTS.md           # AI 协作指南
├── ROADMAP.md          # 路线图
├── CHANGELOG.md        # 变更日志
├── docs/
│   └── logo.svg        # 项目 Logo
├── src/
│   ├── audio/          # 音频捕获
│   ├── asr/            # 语音识别
│   ├── translation/    # 翻译
│   ├── ui/             # 字幕浮窗
│   └── pipeline.py     # 主流程编排
├── tests/              # 单元测试
└── scripts/            # 安装/启动脚本
```

## 商标声明 | Trademark Disclaimer | 상표 면책 조항

"Shadow Fiend" is a character name owned by Valve Corporation in Dota 2. This project is an independent open-source subtitle translation tool and is not affiliated with, endorsed by, or sponsored by Valve Corporation or Dota 2. The name is used as a tribute to gaming culture.

"Shadow Fiend"는 Valve Corporation의 Dota 2에 등장하는 캐릭터 이름입니다. 본 프로젝트는 독립적인 오픈소스 자막 번역 도구이며 Valve Corporation 또는 Dota 2와 제휴, 보증, 후원 관계가 없습니다.

## 许可 | License | 라이선스

MIT License
