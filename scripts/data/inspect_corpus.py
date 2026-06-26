#!/usr/bin/env python3
"""
Inspect cleaned parallel corpus and print statistics + samples.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_tsv(path: Path):
    pairs = []
    with open(path, "r", encoding="utf-8") as f:
        next(f)
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            pairs.append((parts[0], parts[1]))
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="data/translation_corpus_v0.0.5")
    parser.add_argument("--pairs", nargs="+", default=["ja-zh", "ko-zh", "en-zh"])
    parser.add_argument("--samples", type=int, default=10)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    stats = {}
    for pair in args.pairs:
        path = data_dir / f"{pair}.tsv"
        if not path.exists():
            print(f"{path} not found, skipping")
            continue
        pairs = load_tsv(path)
        src_lens = [len(s) for s, _ in pairs]
        tgt_lens = [len(t) for _, t in pairs]
        avg_src = sum(src_lens) / len(src_lens) if src_lens else 0
        avg_tgt = sum(tgt_lens) / len(tgt_lens) if tgt_lens else 0
        stats[pair] = {
            "count": len(pairs),
            "avg_src_len": round(avg_src, 1),
            "avg_tgt_len": round(avg_tgt, 1),
            "max_src_len": max(src_lens) if src_lens else 0,
            "max_tgt_len": max(tgt_lens) if tgt_lens else 0,
        }
        print(f"\n=== {pair}: {len(pairs)} pairs ===")
        print(f"  avg src={avg_src:.1f}, avg tgt={avg_tgt:.1f}")
        print(f"  max src={max(src_lens) if src_lens else 0}, max tgt={max(tgt_lens) if tgt_lens else 0}")
        print("  Samples:")
        for src, tgt in pairs[:args.samples]:
            print(f"    [src] {src}")
            print(f"    [tgt] {tgt}")
            print()

    stats_path = data_dir / "inspect_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\nStats saved to {stats_path}")


if __name__ == "__main__":
    main()
