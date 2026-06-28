#!/usr/bin/env python3
"""
使用 fasttext 质量分类器对平行语料进行二次过滤。

用法：
    python scripts/data/apply_quality_classifier.py \
        --input data/translation_corpus_v0.0.5/ja-zh.domain.tsv \
        --output data/translation_corpus_v0.0.5/ja-zh.classifier.tsv \
        --model data/pretrained/quality_classifier.bin \
        --threshold 0.8
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fasttext
from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="data/pretrained/quality_classifier.bin")
    parser.add_argument("--threshold", type=float, default=0.8,
                        help="Minimum probability for __label__good")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    print(f"Loading classifier from {args.model} ...")
    model = fasttext.load_model(args.model)

    pairs = []
    with open(input_path, "r", encoding="utf-8") as f:
        next(f)
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                pairs.append((parts[0], parts[1]))

    print(f"Loaded {len(pairs)} pairs")

    kept = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\n")
        for src, tgt in tqdm(pairs, desc="Classifier filtering"):
            text = f"{src} {tgt}"
            labels, probs = model.predict([text])
            label = labels[0][0]
            prob = probs[0][0]
            if label == "__label__good" and prob >= args.threshold:
                f.write(f"{src}\t{tgt}\n")
                kept += 1

    stats = {
        "input": str(input_path),
        "output": str(output_path),
        "total": len(pairs),
        "kept": kept,
        "removed": len(pairs) - kept,
        "retention_rate": round(kept / len(pairs), 4),
        "threshold": args.threshold,
    }
    stats_path = output_path.with_suffix(output_path.suffix + ".stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\nKept {kept}/{len(pairs)} pairs ({stats['retention_rate']*100:.1f}%)")
    print(f"Stats saved to {stats_path}")


if __name__ == "__main__":
    main()
