#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

# Prefer the test-ready .venv-test environment when available; fall back to .venv.
VENV=".venv-test"
if [ ! -d "$VENV" ]; then
    VENV=".venv"
fi

if [ ! -d "$VENV" ]; then
    echo "Virtual environment not found. Please run ./scripts/setup.sh first."
    exit 1
fi

PYTHON="$VENV/bin/python"
py_version=$($PYTHON --version 2>&1 | awk '{print $2}')
major=$(echo "$py_version" | cut -d. -f1)
minor=$(echo "$py_version" | cut -d. -f2)
if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
    echo "ERROR: shadow_fiend requires Python 3.10+. Found $py_version in $VENV."
    exit 1
fi

# Pin model caches to the same location used by scripts/_download_sensevoice.py
# so models are downloaded only once.
SHADOW_FIEND_CACHE_ROOT="${SHADOW_FIEND_CACHE_ROOT:-$HOME/.cache/shadow_fiend-test}"
export HF_HOME="${HF_HOME:-$SHADOW_FIEND_CACHE_ROOT/huggingface}"
export MODELSCOPE_CACHE="${MODELSCOPE_CACHE:-$SHADOW_FIEND_CACHE_ROOT/modelscope}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$SHADOW_FIEND_CACHE_ROOT/transformers}"
export TORCH_HOME="${TORCH_HOME:-$SHADOW_FIEND_CACHE_ROOT/torch}"

export PYTHONPATH="${PWD}:${PWD}/src:${PYTHONPATH:-}"
$PYTHON -m src.main "$@"
