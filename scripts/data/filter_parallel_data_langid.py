#!/usr/bin/env python3
"""
使用 fasttext 语言识别过滤平行语料，确保源/目标语言正确。

用法：
    python scripts/data/filter_parallel_data_langid.py \
        --input data/translation_corpus_v0.0.5/ja-zh.tsv \
        --output data/translation_corpus_v0.0.5/ja-zh.langid.tsv \
        --pair ja-zh \
        --model scripts/data/lid.176.bin \
        --threshold 0.9
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fasttext
from tqdm import tqdm


LANG_MAP = {
    "ja-zh": ("ja", "zh"),
    "ko-zh": ("ko", "zh"),
    "en-zh": ("en", "zh"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pair", required=True, choices=list(LANG_MAP.keys()))
    parser.add_argument("--model", default="data/pretrained/lid.176.bin")
    parser.add_argument("--threshold", type=float, default=0.9)
    return parser.parse_args()


def load_pairs(path: Path):
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


def detect_lang(model, text: str):
    """返回 (lang, score)。"""
    # fasttext 需要单行文本，替换换行符
    text = text.replace("\n", " ").strip()
    if not text:
        return None, 0.0
    labels, scores = model.predict(text, k=1)
    lang = labels[0].replace("__label__", "")
    return lang, float(scores[0])


def main():
    args = parse_args()
    src_lang, tgt_lang = LANG_MAP[args.pair]
    input_path = Path(args.input)
    output_path = Path(args.output)

    print(f"Loading fasttext model from {args.model} ...")
    model = fasttext.load_model(args.model)

    pairs = load_pairs(input_path)
    print(f"Loaded {len(pairs)} pairs from {input_path}")

    kept = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\tsrc_lang_conf\ttgt_lang_conf\n")
        for src, tgt in tqdm(pairs, desc="Language ID filtering"):
            src_detected, src_score = detect_lang(model, src)
            tgt_detected, tgt_score = detect_lang(model, tgt)

            src_ok = src_detected == src_lang and src_score >= args.threshold
            tgt_ok = tgt_detected == tgt_lang and tgt_score >= args.threshold

            if src_ok and tgt_ok:
                f.write(f"{src}\t{tgt}\t{src_score:.3f}\t{tgt_score:.3f}\n")
                kept += 1

    stats = {
        "input": str(input_path),
        "output": str(output_path),
        "pair": args.pair,
        "threshold": args.threshold,
        "total": len(pairs),
        "kept": kept,
        "removed": len(pairs) - kept,
        "retention_rate": round(kept / len(pairs), 4),
    }
    stats_path = output_path.with_suffix(output_path.suffix + ".stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\nKept {kept}/{len(pairs)} pairs ({stats['retention_rate']*100:.1f}%)")
    print(f"Stats saved to {stats_path}")


if __name__ == "__main__":
    main()
