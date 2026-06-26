#!/usr/bin/env python3
"""
探索 ja↔zh / ko↔zh / en↔zh 平行数据源。

用法：
    HF_ENDPOINT=https://hf-mirror.com python scripts/data/explore_parallel_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

OUTPUT_DIR = Path("docs/product")
OUTPUT_FILE = OUTPUT_DIR / "parallel_data_exploration_v0.0.5.json"

SOURCES = {
    "ccmatrix_ja_zh": ("yhavinga/ccmatrix", "ja-zh"),
    "ccmatrix_ko_zh": ("yhavinga/ccmatrix", "ko-zh"),
    "ccmatrix_en_zh": ("yhavinga/ccmatrix", "en-zh"),
    "ccmatrix_ja_zho": ("yhavinga/ccmatrix", "ja-zho"),
    "ccmatrix_ko_zho": ("yhavinga/ccmatrix", "ko-zho"),
}

SAMPLE_SIZE = 20
MAX_TOTAL = 100000  # 最多统计 10 万条就停止


def explore_source(name: str, dataset_name: str, config: str) -> dict:
    print(f"\n[Exploring {name}: {dataset_name}/{config}]")
    try:
        ds = load_dataset(
            dataset_name,
            config,
            streaming=True,
            split="train",
            trust_remote_code=True,
        )
    except Exception as e:
        print(f"  Failed to load: {e}")
        return {"status": "failed", "error": str(e)}

    samples = []
    total = 0
    src_lens = []
    tgt_lens = []
    empty = 0
    too_long = 0

    try:
        for sample in ds:
            total += 1
            if total > MAX_TOTAL:
                break

            trans = sample.get("translation", {})
            if not trans or len(trans) != 2:
                continue

            src, tgt = list(trans.values())
            if not src or not tgt:
                empty += 1
                continue
            if len(src) > 200 or len(tgt) > 200:
                too_long += 1
                continue

            src_lens.append(len(src))
            tgt_lens.append(len(tgt))

            if len(samples) < SAMPLE_SIZE:
                samples.append({"src": src, "tgt": tgt, "score": sample.get("score")})

            if total % 10000 == 0:
                print(f"  processed {total}, kept {len(src_lens)}")
    except Exception as e:
        print(f"  Failed during iteration: {e}")
        return {
            "status": "partial",
            "dataset": dataset_name,
            "config": config,
            "error": str(e),
            "total_seen": total,
            "valid_count": len(src_lens),
            "samples": samples,
        }

    return {
        "status": "ok",
        "dataset": dataset_name,
        "config": config,
        "total_seen": total,
        "valid_count": len(src_lens),
        "empty_count": empty,
        "too_long_count": too_long,
        "avg_src_len": round(sum(src_lens) / len(src_lens), 1) if src_lens else 0,
        "avg_tgt_len": round(sum(tgt_lens) / len(tgt_lens), 1) if tgt_lens else 0,
        "samples": samples,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, (dataset_name, config) in SOURCES.items():
        results[name] = explore_source(name, dataset_name, config)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved exploration report to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
