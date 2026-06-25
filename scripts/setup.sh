#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "==> shadow_fiend setup script for macOS"

# Discover a Python 3.10+ interpreter.
PYTHON_CMD=""
for cmd in python3 python3.12 python3.11 python3.10 "$HOME/miniconda3/bin/python" "$HOME/miniconda3/bin/python3" "$HOME/miniconda3/bin/python3.11"; do
    if command -v "$cmd" &> /dev/null; then
        version=$("$cmd" --version 2>&1 | awk '{print $2}')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: shadow_fiend requires Python 3.10 or newer."
    echo "Please install Python 3.10+ via https://www.python.org or Homebrew:"
    echo "    brew install python@3.11"
    exit 1
fi

python_version=$("$PYTHON_CMD" --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version ($PYTHON_CMD)"

# Check Homebrew
if ! command -v brew &> /dev/null; then
    echo "ERROR: Homebrew is required. Please install it first: https://brew.sh"
    exit 1
fi

# Install system dependencies
echo "==> Installing system dependencies via Homebrew..."
brew install portaudio blackhole-2ch ffmpeg

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "==> Creating virtual environment..."
    "$PYTHON_CMD" -m venv .venv
fi

# Install Python dependencies
echo "==> Installing Python dependencies..."
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

# Check BlackHole
echo "==> Checking BlackHole audio driver..."
if [ ! -d "/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver" ]; then
    echo "ERROR: BlackHole 2ch installation seems to have failed."
    exit 1
fi

echo ""
echo "==> Setup complete."
echo "IMPORTANT: Please configure a Multi-Output Device in Audio MIDI Setup"
echo "           so that both your speakers and BlackHole 2ch receive audio."
echo ""
echo "To start shadow_fiend, run: ./scripts/run.sh"
