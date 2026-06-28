#!/usr/bin/env python3
"""
使用 LaBSE 对平行语料进行语义相似度过滤。

用法：
    HF_ENDPOINT=https://hf-mirror.com python scripts/data/filter_parallel_data_labse.py \
        --input data/translation_corpus_v0.0.5/ja-zh.tsv \
        --output data/translation_corpus_v0.0.5/ja-zh.labse.tsv \
        --threshold 0.65 \
        --batch_size 64
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input TSV file")
    parser.add_argument("--output", required=True, help="Output TSV file")
    parser.add_argument("--threshold", type=float, default=0.65, help="LaBSE cosine similarity threshold")
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--model", default="sentence-transformers/LaBSE")
    parser.add_argument("--device", default=None, help="cuda/cpu/mps")
    return parser.parse_args()


def load_pairs(path: Path):
    sources, targets = [], []
    with open(path, "r", encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            sources.append(parts[0])
            targets.append(parts[1])
    return sources, targets


def encode_in_batches(model, texts: list[str], batch_size: int, show_progress: bool = True):
    return model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    device = args.device or ("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Loading LaBSE on {device} ...")
    model = SentenceTransformer(args.model, device=device)

    print(f"Loading pairs from {input_path} ...")
    sources, targets = load_pairs(input_path)
    print(f"Total pairs: {len(sources)}")

    print("Encoding source sentences ...")
    src_embeddings = encode_in_batches(model, sources, args.batch_size)
    print("Encoding target sentences ...")
    tgt_embeddings = encode_in_batches(model, targets, args.batch_size)

    similarities = np.sum(src_embeddings * tgt_embeddings, axis=1)

    kept = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\tscore\n")
        for src, tgt, score in tqdm(zip(sources, targets, similarities), total=len(sources), desc="Filtering"):
            if score >= args.threshold:
                f.write(f"{src}\t{tgt}\t{score:.4f}\n")
                kept += 1

    stats = {
        "input": str(input_path),
        "output": str(output_path),
        "threshold": args.threshold,
        "total": len(sources),
        "kept": kept,
        "removed": len(sources) - kept,
        "retention_rate": round(kept / len(sources), 4),
        "mean_similarity": round(float(np.mean(similarities)), 4),
    }
    stats_path = output_path.with_suffix(output_path.suffix + ".stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\nKept {kept}/{len(sources)} pairs ({stats['retention_rate']*100:.1f}%)")
    print(f"Mean similarity: {stats['mean_similarity']}")
    print(f"Stats saved to {stats_path}")


if __name__ == "__main__":
    main()
