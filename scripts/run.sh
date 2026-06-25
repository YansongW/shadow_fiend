#!/usr/bin/env bash
set -e

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run ./scripts/setup.sh first."
    exit 1
fi

./.venv/bin/python -m src.main "$@"
