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
  shadow_fiend captures your system audio, transcribes speech locally with SenseVoice, translates with Argos, and overlays bilingual subtitles in real time.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/ASR-SenseVoice-ff006e?style=flat-square">
  <img src="https://img.shields.io/badge/Translation-Argos-8338ec?style=flat-square">
  <img src="https://img.shields.io/badge/UI-PyQt6-3a86ff?style=flat-square">
  <img src="https://img.shields.io/badge/Status-MVE-fb5607?style=flat-square">
</p>

## Features

- 🔒 **Fully offline** — audio never leaves your machine
- 🚀 **Fast local ASR** — SenseVoice-Small optimized for Chinese, Japanese, Korean
- 🌐 **Local translation** — Argos Translate engine, no API keys
- 🎨 **Floating subtitle overlay** — transparent, always-on-top, draggable
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

MVE stage. Core modules implemented and unit-tested:

- ✅ Audio capture (BlackHole + PyAudio)
- ✅ VAD segmentation
- ✅ SenseVoice ASR
- ✅ Argos Translate
- ✅ PyQt6 subtitle overlay
- ✅ End-to-end pipeline

End-to-end live demo needs verification on a machine with Python 3.10+ and Homebrew.

## Testing

```bash
./.venv/bin/python -m pytest tests/ -v
```

## Project Structure

```
shadow_fiend/
├── README.md
├── README.zh.md
├── README.ko.md
├── src/
│   ├── audio/       # audio capture + VAD
│   ├── asr/         # SenseVoice ASR
│   ├── translation/ # Argos translation
│   ├── ui/          # subtitle overlay
│   └── pipeline.py  # orchestration
├── tests/
└── scripts/
```

## Trademark Disclaimer

"Shadow Fiend" is a character name owned by Valve Corporation in *Dota 2*. This project is an independent open-source subtitle translation tool and is not affiliated with, endorsed by, or sponsored by Valve Corporation or *Dota 2*.

## License

MIT License
