#!/usr/bin/env python3
"""
Check local environment readiness for v0.0.5 M2M100 fine-tuning.

Usage:
    .venv/bin/python scripts/training/check_env.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def check_python_packages():
    required = [
        "torch",
        "transformers",
        "datasets",
        "accelerate",
        "sentencepiece",
        "tensorboard",
    ]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def check_data():
    data_dir = Path("data/translation_corpus_final")
    files = ["train.tsv", "val.tsv", "test.tsv"]
    missing = [f for f in files if not (data_dir / f).exists()]
    counts = {}
    for f in files:
        path = data_dir / f
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                counts[f] = sum(1 for _ in fh) - 1  # minus header
    return missing, counts


def check_hf_token():
    token = os.environ.get("HF_TOKEN")
    return token is not None and token.startswith("hf_")


def main():
    print("=" * 50)
    print("v0.0.5 Fine-tuning Environment Check")
    print("=" * 50)

    missing_pkgs = check_python_packages()
    if missing_pkgs:
        print(f"\n❌ Missing packages: {', '.join(missing_pkgs)}")
        print("   Install: .venv/bin/python -m pip install -r requirements.txt")
        sys.exit(1)
    print("\n✅ All required Python packages are installed.")

    missing_data, counts = check_data()
    if missing_data:
        print(f"\n❌ Missing data files: {', '.join(missing_data)}")
        print("   Prepare data by copying from another machine or running the data pipeline.")
        sys.exit(1)
    print("\n✅ Final corpus found:")
    for f, c in counts.items():
        print(f"   {f}: {c:,} pairs")

    if torch := sys.modules.get("torch"):
        print(f"\n✅ PyTorch {torch.__version__}")
        print(f"   MPS available: {torch.backends.mps.is_available()}")
        print(f"   CUDA available: {torch.cuda.is_available()}")

    if check_hf_token():
        print("\n✅ HF_TOKEN is set.")
    else:
        print("\n⚠️  HF_TOKEN not set. Training will work, but model won't upload to Hugging Face.")
        print("   Set with: export HF_TOKEN=hf_xxxxxxxxxxxxxxxx")

    print("\n" + "=" * 50)
    print("Environment ready. Run: bash scripts/training/train_and_publish.sh")
    print("=" * 50)


if __name__ == "__main__":
    main()
