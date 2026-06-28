#!/usr/bin/env python3
"""
合并所有清洗后的语料并生成最终报告。
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


PAIRS = ["ja-zh", "ko-zh", "en-zh"]
SOURCES = ["ccmatrix_small", "ccmatrix_large", "opus"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/translation_corpus_final")
    parser.add_argument("--val-ratio", type=float, default=0.01)
    parser.add_argument("--test-ratio", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def find_domain_files():
    """自动发现所有可用的 .domain.tsv 文件。"""
    files = []
    base_dirs = [
        Path("data/translation_corpus_v0.0.5"),
        Path("data/translation_corpus_v0.0.5_large"),
        Path("data/translation_corpus_opus"),
    ]
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
        for pair in PAIRS:
            path = base_dir / f"{pair}.domain.tsv"
            if path.exists():
                source_tag = "opus" if "opus" in str(base_dir).lower() else (
                    "ccmatrix_large" if "large" in str(base_dir).lower() else "ccmatrix_small"
                )
                files.append((path, pair, source_tag))
    return files


def load_pairs(path: Path):
    pairs = []
    with open(path, "r", encoding="utf-8") as f:
        next(f)
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
    return pairs


def main():
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)

    all_samples = []
    seen = set()
    stats_by_pair_source = {p: {s: 0 for s in SOURCES} for p in PAIRS}

    domain_files = find_domain_files()
    print(f"Found {len(domain_files)} domain files")

    for path, pair, source_tag in domain_files:
        print(f"Loading {path} ...")
        pairs = load_pairs(path)
        for src, tgt in pairs:
            key = (src, tgt)
            if key in seen:
                continue
            seen.add(key)
            all_samples.append((src, tgt, pair, source_tag))
            stats_by_pair_source[pair][source_tag] += 1

    print(f"\nTotal unique pairs: {len(all_samples)}")
    for pair in PAIRS:
        total = sum(stats_by_pair_source[pair].values())
        print(f"  {pair}: {total:,}")
        for source_tag in SOURCES:
            count = stats_by_pair_source[pair][source_tag]
            if count > 0:
                print(f"    {source_tag}: {count:,}")

    random.shuffle(all_samples)

    n = len(all_samples)
    n_test = int(n * args.test_ratio)
    n_val = int(n * args.val_ratio)
    n_train = n - n_val - n_test

    train = all_samples[:n_train]
    val = all_samples[n_train : n_train + n_val]
    test = all_samples[n_train + n_val :]

    splits = {"train": train, "val": val, "test": test}
    for split_name, data in splits.items():
        tsv_path = output_dir / f"{split_name}.tsv"
        with open(tsv_path, "w", encoding="utf-8") as f:
            f.write("source\ttarget\n")
            for src, tgt, _, _ in data:
                f.write(f"{src}\t{tgt}\n")
        print(f"Wrote {len(data)} pairs to {tsv_path}")

    # Write metadata
    meta_path = output_dir / "metadata.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for split_name, data in splits.items():
            for src, tgt, pair, source_tag in data:
                f.write(json.dumps({
                    "source": src,
                    "target": tgt,
                    "pair": pair,
                    "source_tag": source_tag,
                    "split": split_name,
                }, ensure_ascii=False) + "\n")
    print(f"Wrote metadata to {meta_path}")

    # Write stats
    stats = {
        "total": n,
        "train": n_train,
        "val": n_val,
        "test": n_test,
        "by_pair_source": stats_by_pair_source,
    }
    with open(output_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # Sample for manual inspection
    random.seed(args.seed)
    sample = random.sample(all_samples, min(300, len(all_samples)))
    sample_path = output_dir / "sample300.tsv"
    with open(sample_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\tpair\tsource_tag\n")
        for src, tgt, pair, source_tag in sample:
            f.write(f"{src}\t{tgt}\t{pair}\t{source_tag}\n")
    print(f"Wrote 300 samples to {sample_path}")

    print("\nFinal stats:")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
