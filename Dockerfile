# shadow_fiend Docker image
# Primarily intended for development environment consistency and headless testing.
# GUI mode requires X11 forwarding (see README).

FROM python:3.11-slim

LABEL org.opencontainers.image.title="shadow-fiend"
LABEL org.opencontainers.image.description="Local real-time subtitle translation"
LABEL org.opencontainers.image.source="https://github.com/YansongW/shadow_fiend"

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies:
# - libportaudio2: PyAudio runtime
# - libportaudio-dev + build-essential: compile PyAudio wheel from source
# - python3-dev: Python headers for building native extensions
# - libsndfile1: audio file I/O
# - libgl1 / libglib2.0-0 / libxkbcommon-x11-0: Qt6 runtime
# - libgomp1: OpenMP for some ML libs
# - git: torch.hub may need it
# - xvfb: headless display for GUI/CI tests
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    libportaudio-dev \
    build-essential \
    python3-dev \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    libxkbcommon-x11-0 \
    libgomp1 \
    git \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY requirements.txt pyproject.toml setup.py ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY assets/ ./assets/
COPY scripts/ ./scripts/
COPY README.md CHANGELOG.md ROADMAP.md ./

# Install the package itself
RUN pip install --no-cache-dir -e .

# Default to CLI help; override at runtime for actual usage
ENTRYPOINT ["shadow-fiend"]
CMD ["--help"]
