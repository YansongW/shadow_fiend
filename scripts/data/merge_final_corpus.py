#!/usr/bin/env python3
"""
合并多个清洗后的语料源（CCMatrix large + OPUS），去重并划分 train/val/test。

用法：
    python scripts/data/merge_final_corpus.py \
        --inputs data/translation_corpus_v0.0.5_large/*.domain.tsv data/translation_corpus_opus/*.domain.tsv \
        --output data/translation_corpus_final \
        --val-ratio 0.01 \
        --test-ratio 0.01
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


PAIRS = ["ja-zh", "ko-zh", "en-zh"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--output", default="data/translation_corpus_final")
    parser.add_argument("--val-ratio", type=float, default=0.01)
    parser.add_argument("--test-ratio", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_pairs(path: Path):
    """加载 (src, tgt, source_tag, pair) 列表。"""
    pairs = []
    # 从文件名推断 pair 和 source_tag
    name = path.name
    pair = None
    for p in PAIRS:
        if name.startswith(p):
            pair = p
            break
    source_tag = "opus" if "opus" in str(path).lower() else "ccmatrix"

    with open(path, "r", encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            pairs.append((parts[0].strip(), parts[1].strip(), source_tag, pair))
    return pairs


def main():
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)

    all_samples = []
    seen = set()
    stats_by_pair = {p: {"total": 0, "ccmatrix": 0, "opus": 0} for p in PAIRS}

    for input_path in args.inputs:
        input_path = Path(input_path)
        if not input_path.exists():
            print(f"Warning: {input_path} not found, skipping")
            continue
        print(f"Loading {input_path} ...")
        pairs = load_pairs(input_path)
        for src, tgt, source_tag, pair in pairs:
            key = (src, tgt)
            if key in seen:
                continue
            seen.add(key)
            all_samples.append((src, tgt, source_tag, pair))
            if pair:
                stats_by_pair[pair]["total"] += 1
                stats_by_pair[pair][source_tag] += 1

    print(f"\nTotal unique pairs: {len(all_samples)}")
    for pair, st in stats_by_pair.items():
        print(f"  {pair}: {st['total']:,} (ccmatrix={st['ccmatrix']:,}, opus={st['opus']:,})")

    random.shuffle(all_samples)

    n = len(all_samples)
    n_test = int(n * args.test_ratio)
    n_val = int(n * args.val_ratio)
    n_train = n - n_val - n_test

    train = all_samples[:n_train]
    val = all_samples[n_train : n_train + n_val]
    test = all_samples[n_train + n_val :]

    # Write TSVs
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
            for src, tgt, source_tag, pair in data:
                f.write(json.dumps({
                    "source": src,
                    "target": tgt,
                    "source_tag": source_tag,
                    "pair": pair,
                    "split": split_name,
                }, ensure_ascii=False) + "\n")
    print(f"Wrote metadata to {meta_path}")

    # Summary stats
    stats = {
        "total": n,
        "train": n_train,
        "val": n_val,
        "test": n_test,
        "by_pair": stats_by_pair,
    }
    with open(output_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\nFinal stats: {stats}")


if __name__ == "__main__":
    main()
