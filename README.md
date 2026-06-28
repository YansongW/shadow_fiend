> **Note: This is the `v0.0.5-finetune` branch.**  
> It contains the data pipeline and training scripts for fine-tuning `facebook/m2m100_418M` on ja↔zh / ko↔zh / en↔zh parallel corpora.  
> For the main application, see the [`main`](https://github.com/YansongW/shadow_fiend/tree/main) branch.

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

## v0.0.5 Model Training

This branch fine-tunes `facebook/m2m100_418M` on 586k cleaned parallel sentence pairs for **ja→zh, ko→zh, en→zh**.

### Dataset

Final corpus: `data/translation_corpus_final/`

| Split | Pairs |
|---|---|
| train.tsv | 574,465 |
| val.tsv | 5,861 |
| test.tsv | 5,861 |

Sources: CCMatrix small (168k), CCMatrix large (356k), OPUS (61k).

### Setup on a fresh Mac mini

```bash
# 1. Clone this branch
git clone --branch v0.0.5-finetune https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend

# 2. Create a virtual environment
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# 3. Prepare the final corpus (choose one method)
#    A) Copy from another machine:
#       scp -r user@other-host:/path/to/shadow_fiend/data/translation_corpus_final data/
#    B) Or regenerate from scratch on main branch (slow, CPU-only):
#       git checkout main
#       bash scripts/data/pipeline_v0.0.5_large_from_langid.sh
#       bash scripts/data/pipeline_opus.sh
#       .venv/bin/python scripts/data/generate_final_report.py
#       git checkout v0.0.5-finetune

# 4. Check environment
.venv/bin/python scripts/training/check_env.py
```

### Run Training

```bash
# Optional: set Hugging Face write token if you want to upload the model
export HF_TOKEN=hf_xxxxxxxxxxxxxxxx

# Start training + auto push code + optional HF upload
bash scripts/training/train_and_publish.sh
```

Training hyperparameters ( tuned for 64 GB Apple Silicon ):
- Epochs: 3
- Batch size: 4 per device
- Gradient accumulation: 8 (effective batch 32)
- Max length: 128
- Learning rate: 5e-5
- Device: auto (`mps` on Apple Silicon, `cpu` fallback)

The wrapper will:
1. Train the model to `models/m2m100-418M-zh-ja-ko-en-v0.0.5/`.
2. Upload it to Hugging Face (if `HF_TOKEN` is set).
3. Commit and push any code changes back to the `v0.0.5-finetune` branch.

### Manual Steps

If you prefer to run training without the wrapper:

```bash
.venv/bin/python scripts/training/finetune_m2m100_v0.0.5.py \
  --data_dir data/translation_corpus_final \
  --output_dir models/m2m100-418M-zh-ja-ko-en-v0.0.5 \
  --num_train_epochs 3 \
  --per_device_train_batch_size 4 \
  --gradient_accumulation_steps 8
```

Upload to Hugging Face manually:

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxx
.venv/bin/python scripts/training/upload_to_hf.py \
  --model_dir models/m2m100-418M-zh-ja-ko-en-v0.0.5 \
  --repo_id YansongW/m2m100-418M-zh-ja-ko-en-v0.0.5
```

## Docker

A Docker image is published to **GitHub Packages** for reproducible development and headless testing:

```bash
docker pull ghcr.io/yansongw/shadow_fiend:latest
```

### Headless / CI usage

```bash
docker run --rm ghcr.io/yansongw/shadow_fiend:latest --help
```

### GUI usage (X11 forwarding on macOS/Linux)

> GUI mode in Docker is optional. Native installation is recommended for daily watching.

```bash
# macOS: allow XQuartz connections
xhost +localhost

# Run with X11 socket forwarded
docker run --rm -e DISPLAY=host.docker.internal:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ghcr.io/yansongw/shadow_fiend:latest --source ja --target zh
```

The image is built automatically on every GitHub Release via [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml). The default published platform is `linux/amd64`; `linux/arm64` can be added via the `platforms` workflow input when needed.

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
├── Dockerfile
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
