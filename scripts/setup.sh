#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

echo "==> YiMu setup script for macOS"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

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
    echo "BlackHole 2ch not found. Installing via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "ERROR: Homebrew not found. Please install Homebrew first: https://brew.sh"
        exit 1
    fi
    brew install blackhole-2ch
    echo "Please restart your Mac or run: sudo killall coreaudiod"
else
    echo "BlackHole 2ch is already installed."
fi

echo "==> Setup complete."
echo "To start YiMu, run: ./scripts/run.sh"
