<div align="center">
  <img src="docs/logo.svg" width="160" alt="shadow_fiend logo">
  <h1>shadow_fiend</h1>
  <p><b>영화 시청용 로컬 실시간 자막 번역기</b></p>
  <p>
    <a href="README.md">English</a> •
    <a href="README.zh.md">中文</a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/Platform-macOS%20Apple%20Silicon-black?style=flat-square&logo=apple" alt="macOS">
    <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License">
    <img src="https://img.shields.io/badge/Status-MVE-orange?style=flat-square" alt="MVE">
  </p>
</div>

---

> **자막이 없는 영화도 볼 수 있게 만드세요.**
> shadow_fiend는 시스템 오디오를 캡처하고 SenseVoice로 로컬 음성 인식을 수행한 뒤 Argos로 번역하여 화면에 실시간 이중 자막을 표시합니다.

## 특징

- 🔒 **완전 오프라인** — 오디오가 외부로 전송되지 않음
- 🚀 **스트리밍 저지연 ASR** — SenseVoice-Small + Silero VAD + 500 ms 슬라이딩 윈도우
- 🔇 **실시간 노이즈 제거** — 인식 전 RNNoise로 배경 소음 감소
- 🌐 **로컬 번역** — Helsinki-NLP/opus-mt 우선, Argos Translate 폴팅
- 🎨 **플로팅 자막 오버레이** — 투명하고 항상 위에 표시되며 드래그 가능
- 🖥️ **시스템 트레이 / 메뉴 바** — 시작/일시정지, 노이즈 제거 토글, 스타일, 위치, 클릭 통과, SRT 낭출
- 🎬 **영화 시청용 설계** — 모든 플레이어의 시스템 오디오 캡처

## 빠른 시작

### 요구사항

- macOS 12+ (MVE 단계에서는 Apple Silicon)
- Python 3.10+
- Homebrew
- BlackHole 2ch 가상 오디오 드라이버

### 설치

```bash
git clone https://github.com/YansongW/shadow_fiend.git
cd shadow_fiend
./scripts/setup.sh
```

### macOS 오디오 라우팅

1. `Audio MIDI Setup`(`/Applications/Utilities/Audio MIDI Setup.app`) 열기
2. 좌측 하단 `+` 클릭 → **다중 출력 장치 생성**
3. 스피커/헤드폰과 **BlackHole 2ch** 모두 선택
4. 시스템 설정에서 기본 출력으로 설정

### 실행

```bash
./scripts/run.sh --source ko --target zh
```

지원 언어: `zh`, `en`, `ja`, `ko`.

## 개발 상태

v0.0.3이 릴리스되었습니다. 핵심 모듈이 구현되고 검증되었습니다:

- ✅ 오디오 캡처 (BlackHole + PyAudio)
- ✅ Silero VAD 분할
- ✅ 스트리밍 SenseVoice ASR (500 ms 윈도우 / 200 ms hop)
- ✅ RNNoise 실시간 노이즈 제거 (16 kHz I/O, 낮부 48 kHz)
- ✅ opus-mt 직접 번역 엔진, Argos 폴팅
- ✅ PyQt6 자막 오버레이 + 시스템 트레이 컨트롤러
- ✅ 스트리밍 엔드투엔드 pipeline

macOS Apple Silicon + BlackHole 2ch에서 엔드투엔드 실시간 데모가 검증되었습니다.

> **테스트 코드**는 [`test`](https://github.com/YansongW/shadow_fiend/tree/test) 브랜치에서 관리됩니다. 자세한 내용은 [`ROADMAP.md`](ROADMAP.md)를 참조하세요.

## Docker

**GitHub Packages**에 재현 가능한 개발 및 헤드리스 테스트용 이미지가 게시되어 있습니다:

```bash
docker pull ghcr.io/yansongw/shadow_fiend:latest
```

#### 헤드리스 / CI 사용법

```bash
docker run --rm ghcr.io/yansongw/shadow_fiend:latest --help
```

#### GUI 사용법 (X11 포워딩)

> Docker에서 GUI를 실행하는 것은 선택 사항이며, 일상적인 영화 시청은 로컬 설치를 권장합니다.

```bash
# macOS: XQuartz 연결 허용
xhost +localhost

# X11 소켓을 전달하여 실행
docker run --rm -e DISPLAY=host.docker.internal:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  ghcr.io/yansongw/shadow_fiend:latest --source ko --target zh
```

이 이미지는 [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml)을 통해 GitHub Release가 생성될 때마다 자동으로 빌드 및 게시됩니다. 기본 게시 플랫폼은 `linux/amd64`이며, 필요한 경우 workflow의 `platforms` 입력을 통해 `linux/arm64`를 추가할 수 있습니다.

> Docker는 macOS 오디오 하드웨어에 직접 접근할 수 없으므로 엔드투엔드 demo는 macOS + BlackHole 2ch가 필요합니다.

## 테스트

테스트 코드와 벤치마크 데이터는 [`test`](https://github.com/YansongW/shadow_fiend/tree/test) 브랜치에 있습니다. 해당 브랜치로 전환 후:

```bash
./.venv/bin/python -m pytest tests/ -v
```

## 프로젝트 구조

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
│   ├── audio/                # 오디오 캡처 + Silero VAD
│   ├── asr/                  # SenseVoice ASR + 스트리밍 래퍼
│   ├── translation/          # opus-mt 엔진 + Argos 폴팅
│   ├── ui/                   # 자막 오버레이 + 트레이 컨트롤러
│   ├── pipeline_streaming.py # 스트리밍 흐름 조정
│   └── main.py               # CLI 진입점
├── scripts/                  # 설치 / 실행 보조 스크립트
├── tests/                    # 벤치마크(test 브랜치)
└── assets/                   # 로고 파일
```

## 상표 면책 조항

"Shadow Fiend"는 Valve Corporation의 Dota 2에 등장하는 캐릭터 이름입니다. 본 프로젝트는 독립적인 오픈소스 자막 번역 도구이며 Valve Corporation 또는 Dota 2와 제휴, 보증, 후원 관계가 없습니다.

## 라이선스

MIT License
