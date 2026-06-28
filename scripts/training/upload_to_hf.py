#!/usr/bin/env python3
"""
Upload a trained model to Hugging Face Hub.

Usage:
    export HF_TOKEN=your_write_token
    .venv/bin/python scripts/training/upload_to_hf.py \
        --model_dir models/m2m100-418M-zh-ja-ko-en-v0.0.5 \
        --repo_id YansongW/m2m100-418M-zh-ja-ko-en-v0.0.5
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", required=True, help="Local path to trained model")
    parser.add_argument("--repo_id", required=True, help="Hugging Face repo ID, e.g. username/model-name")
    parser.add_argument("--private", action="store_true", help="Create private repo")
    return parser.parse_args()


def main():
    args = parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise ValueError("Please set HF_TOKEN environment variable with a write token")

    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    print(f"Loading model from {model_dir}")
    model = M2M100ForConditionalGeneration.from_pretrained(str(model_dir))
    tokenizer = M2M100Tokenizer.from_pretrained(str(model_dir))

    print(f"Uploading to https://huggingface.co/{args.repo_id}")
    model.push_to_hub(args.repo_id, token=token, private=args.private)
    tokenizer.push_to_hub(args.repo_id, token=token, private=args.private)
    print("Upload complete")


if __name__ == "__main__":
    main()
