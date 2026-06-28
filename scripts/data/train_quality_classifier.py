#!/usr/bin/env python3
"""
基于已过滤的 domain.tsv（正例）和 labse.tsv 差集（负例）训练 fasttext 质量分类器。
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import fasttext


def load_pairs(path: Path) -> set[tuple[str, str]]:
    pairs = set()
    with open(path, "r", encoding="utf-8") as f:
        next(f)
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                pairs.add((parts[0].strip(), parts[1].strip()))
    return pairs


def build_train_file(base_dir: Path, output: Path, max_samples: int = 50000):
    pairs = ["ja-zh", "ko-zh", "en-zh"]
    good_samples = []
    bad_samples = []

    for pair in pairs:
        domain_path = base_dir / f"{pair}.domain.tsv"
        labse_path = base_dir / f"{pair}.labse.tsv"
        if not domain_path.exists() or not labse_path.exists():
            print(f"Skipping {pair}: missing files")
            continue

        good = load_pairs(domain_path)
        all_labse = load_pairs(labse_path)
        bad = all_labse - good

        print(f"{pair}: good={len(good)}, bad={len(bad)}")

        for src, tgt in good:
            good_samples.append(f"__label__good {src} {tgt}")
        for src, tgt in bad:
            bad_samples.append(f"__label__bad {src} {tgt}")

    # balance and shuffle
    random.seed(42)
    random.shuffle(good_samples)
    random.shuffle(bad_samples)

    n = min(len(good_samples), len(bad_samples), max_samples // 2)
    good_samples = good_samples[:n]
    bad_samples = bad_samples[:n]

    all_samples = good_samples + bad_samples
    random.shuffle(all_samples)

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for line in all_samples:
            f.write(line.replace("\n", " ") + "\n")

    print(f"Wrote {len(all_samples)} training samples to {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="data/translation_corpus_v0.0.5")
    parser.add_argument("--output", default="data/pretrained/quality_classifier")
    parser.add_argument("--max-samples", type=int, default=50000)
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    output = Path(args.output)

    train_file = output.with_suffix(".train.txt")
    build_train_file(base_dir, train_file, args.max_samples)

    print("Training fasttext classifier...")
    model = fasttext.train_supervised(
        input=str(train_file),
        dim=100,
        epoch=5,
        lr=0.5,
        wordNgrams=2,
        minCount=2,
    )

    model_path = str(output)
    model.save_model(model_path + ".bin")
    print(f"Model saved to {model_path}.bin")

    # quick test
    print("\nQuick test:")
    try:
        texts = [
            "国連は安全な音量レベルに関する新たな安全基準を提案している。 它就音量安全水平提出了新的安全标准。",
            "天も地も泣かず 天地没有哭他们",
        ]
        labels, probs = model.predict(texts)
        for t, l, p in zip(texts, labels, probs):
            print(f"{l[0]} {p[0]:.3f} | {t[:50]}")
    except Exception as e:
        print(f"Predict test skipped: {e}")


if __name__ == "__main__":
    main()
