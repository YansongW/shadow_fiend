#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "==> YingMo setup script for macOS"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
major=$(echo "$python_version" | cut -d. -f1)
minor=$(echo "$python_version" | cut -d. -f2)

echo "Python version: $python_version"
if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
    echo "ERROR: YingMo requires Python 3.10 or newer."
    echo "Current version ($python_version) is not supported."
    echo "Please install Python 3.10+ via https://www.python.org or Homebrew:"
    echo "    brew install python@3.11"
    exit 1
fi

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
    python3 -m venv .venv
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
echo "To start YingMo, run: ./scripts/run.sh"
