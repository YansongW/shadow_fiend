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
- 🚀 **빠른 로컬 ASR** — 중일한에 최적화된 SenseVoice-Small
- 🌐 **로컬 번역** — Argos Translate 엔진, API 키 불필요
- 🎨 **플로팅 자막 오버레이** — 투명하고 항상 위에 표시되며 드래그 가능
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

MVE 단계입니다. 핵심 모듈이 구현되었고 단위 테스트를 통과했습니다:

- ✅ 오디오 캡처 (BlackHole + PyAudio)
- ✅ VAD 분할
- ✅ SenseVoice ASR
- ✅ Argos 번역
- ✅ PyQt6 자막 오버레이
- ✅ 엔드투엔드 pipeline

엔드투엔드 실시간 데모는 Python 3.10+ 및 Homebrew가 설치된 macOS 환경에서 검증해야 합니다.

## 원클릭 테스트

자동화된 전체 테스트 흐름(환경 감지 → 의존성 설치 → 단위 테스트 → 30초 demo + 화면 녹화 → 로그 보고서 → 정리):

```bash
./scripts/one_click_test.sh
```

옵션:
- `--no-cleanup` — 디버깅을 위해 테스트 환경과 다운로드한 모델 유지
- `--duration <초>` — demo 실행 시간 변경(기본 30초)
- `--yes` — 오디오 라우팅 확인 프롬프트 건

실행 후 `test-reports/` 아래에 로그, 녹화 영상, 환경 정보, pip 목록이 포함된 zip 보고서가 저장됩니다.

> 첫 녹화 실행 시 시스템 권한 대화 상자가 나타납니다. demo 녹화를 위해 허용을 클릭하세요.

### 수동 테스트 명령

```bash
python scripts/test_runner.py setup     # 환경 감지, 의존성 설치, .venv-test 생성
python scripts/test_runner.py test      # pytest 실행
python scripts/test_runner.py demo --duration 30   # demo + 자동 화면 녹화
python scripts/test_runner.py logs      # zip 보고서 패키징
python scripts/test_runner.py cleanup   # .venv-test, 로그, 모델 삭제
```

### Docker

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

```bash
./.venv/bin/python -m pytest tests/ -v
```

## 프로젝트 구조

```
shadow_fiend/
├── README.md
├── README.zh.md
├── README.ko.md
├── src/
│   ├── audio/       # 오디오 캡처 + VAD
│   ├── asr/         # SenseVoice 음성 인식
│   ├── translation/ # Argos 번역
│   ├── ui/          # 자막 오버레이
│   └── pipeline.py  # 흐름 조정
├── tests/
└── scripts/
```

## 상표 면책 조항

"Shadow Fiend"는 Valve Corporation의 Dota 2에 등장하는 캐릭터 이름입니다. 본 프로젝트는 독립적인 오픈소스 자막 번역 도구이며 Valve Corporation 또는 Dota 2와 제휴, 보증, 후원 관계가 없습니다.

## 라이선스

MIT License
