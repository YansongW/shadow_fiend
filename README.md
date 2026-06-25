<div align="center">
  <img src="docs/logo.svg" width="200" alt="shadow_fiend logo">
  <h1>shadow_fiend</h1>
  <p><b>Local real-time subtitle translation for movies and shows</b></p>
  <p>
    <a href="README.zh.md">中文</a> •
    <a href="README.ko.md">한국어</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/macOS-Apple%20Silicon-000000?style=flat-square&logo=apple" alt="macOS">
    <img src="https://img.shields.io/github/license/YansongW/shadow_fiend?style=flat-square" alt="License">
    <img src="https://img.shields.io/github/stars/YansongW/shadow_fiend?style=flat-square&color=yellow&logo=github" alt="Stars">
    <img src="https://img.shields.io/github/last-commit/YansongW/shadow_fiend?style=flat-square" alt="Last Commit">
  </p>
</div>

---

<p align="center">
  <b>Turn any movie without subtitles into a watchable experience.</b><br>
  shadow_fiend captures your system audio, transcribes speech locally with SenseVoice, translates locally, and overlays bilingual subtitles in real time.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ASR-SenseVoice-ff006e?style=flat-square">
  <img src="https://img.shields.io/badge/VAD-Silero-06d6a0?style=flat-square">
  <img src="https://img.shields.io/badge/Denoise-RNNoise-fb5607?style=flat-square">
  <img src="https://img.shields.io/badge/Translation-opus--mt%20%2F%20Argos-8338ec?style=flat-square">
  <img src="https://img.shields.io/badge/UI-PyQt6%20%2B%20Tray-3a86ff?style=flat-square">
  <img src="https://img.shields.io/badge/Status-v0.0.3-fb5607?style=flat-square">
</p>

## Features

- 🔒 **Fully offline** — audio never leaves your machine
- 🚀 **Streaming low-latency ASR** — SenseVoice-Small + Silero VAD + 500 ms sliding window
- 🔇 **Real-time denoising** — RNNoise reduces background noise before recognition
- 🌐 **Local translation** — Helsinki-NLP/opus-mt preferred, Argos Translate fallback
- 🎨 **Floating subtitle overlay** — transparent, always-on-top, draggable
- 🖥️ **System tray / menu bar** — start/pause, denoise toggle, style, position, click-through, SRT export
- 🎬 **Built for watching** — captures system audio from any player

## Quick Start

### Requirements

- macOS 12+ (Apple Silicon for MVE)
- Python 3.10+
- Homebrew
- BlackHole 2ch virtual audio driver

### Install

```bash
git clone https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend
./scripts/setup.sh
```

### Route macOS Audio

1. Open `Audio MIDI Setup` (`/Applications/Utilities/Audio MIDI Setup.app`)
2. Click `+` → **Create Multi-Output Device**
3. Check both your speakers/headphones and **BlackHole 2ch**
4. Set it as the system default output

### Run

```bash
./scripts/run.sh --source ja --target zh
```

Supported languages: `zh`, `en`, `ja`, `ko`.

## Development Status

v0.0.3 released. Core modules implemented and verified:

- ✅ Audio capture (BlackHole + PyAudio)
- ✅ Silero VAD segmentation
- ✅ Streaming SenseVoice ASR (500 ms window / 200 ms hop)
- ✅ RNNoise real-time denoising (16 kHz I/O, internal 48 kHz)
- ✅ opus-mt direct translation engine with Argos fallback
- ✅ PyQt6 subtitle overlay + system tray controller
- ✅ Streaming end-to-end pipeline

End-to-end live demo verified on macOS Apple Silicon + BlackHole 2ch.

> **Testing code** is maintained on the [`test`](https://github.com/YansongW/shadow_fiend/tree/test) branch. See [`ROADMAP.md`](ROADMAP.md) for planned improvements.

## macOS 双击运行

针对 v0.0.1 发布包，项目根目录提供两个 `.command` 脚本：

1. **安装 shadow_fiend.command** — 首次运行时双击，自动安装 Homebrew 依赖并创建 Python 虚拟环境。
2. **启动 shadow_fiend.command** — 双击启动实时字幕浮窗（默认 `ja -> zh`）。

> 双击前请确保已配置好 BlackHole 2ch 多输出音频设备。

## Project Structure

```
shadow_fiend/
├── README.md
├── README.zh.md
├── README.ko.md
├── CHANGELOG.md
├── ROADMAP.md
├── setup.py
├── pyproject.toml
├── src/
│   ├── audio/                # audio capture + Silero VAD
│   ├── asr/                  # SenseVoice ASR + streaming wrapper
│   ├── translation/          # opus-mt engine + Argos fallback
│   ├── ui/                   # subtitle overlay + tray controller
│   ├── pipeline_streaming.py # streaming orchestration
│   └── main.py               # CLI entry point
├── scripts/                  # setup / run helpers
├── tests/                    # benchmarks (test branch)
└── assets/                   # logo files
```

## Trademark Disclaimer

"Shadow Fiend" is a character name owned by Valve Corporation in *Dota 2*. This project is an independent open-source subtitle translation tool and is not affiliated with, endorsed by, or sponsored by Valve Corporation or *Dota 2*.

## License

MIT License
