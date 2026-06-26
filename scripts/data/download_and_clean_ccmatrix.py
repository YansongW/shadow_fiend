#!/usr/bin/env python3
"""
下载并清洗 CCMatrix 平行语料，用于 shadow_fiend 翻译模型训练。

用法：
    HF_ENDPOINT=https://hf-mirror.com python scripts/data/download_and_clean_ccmatrix.py \
        --pairs ja-zh ko-zh en-zh \
        --output data/translation_corpus \
        --max_pairs 500000

环境要求：
    pip install datasets zhconv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from datasets import load_dataset
from zhconv import convert


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["ja-zh", "ko-zh", "en-zh"],
        help="Language pairs to download",
    )
    parser.add_argument(
        "--output",
        default="data/translation_corpus",
        help="Output directory",
    )
    parser.add_argument(
        "--max_pairs",
        type=int,
        default=500000,
        help="Max pairs per language direction",
    )
    parser.add_argument(
        "--min_len",
        type=int,
        default=3,
        help="Minimum sentence length",
    )
    parser.add_argument(
        "--max_len",
        type=int,
        default=200,
        help="Maximum sentence length",
    )
    parser.add_argument(
        "--min_ratio",
        type=float,
        default=0.3,
        help="Minimum source/target length ratio",
    )
    parser.add_argument(
        "--max_ratio",
        type=float,
        default=3.0,
        help="Maximum source/target length ratio",
    )
    return parser.parse_args()


def is_noisy(text: str) -> bool:
    """检测明显噪音。"""
    # 任何连续下划线（半角 _ 或全角 ＿，网页模板常见）
    if re.search(r"[_＿]{3,}", text):
        return True
    # 过多特殊字符（超过 30%）
    special_chars = len(re.findall(r"[^\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u0041-\u005a\u0061-\u007a\u0030-\u0039\u3000-\u303f\uff00-\uffef\s]", text))
    if len(text) > 0 and special_chars / len(text) > 0.3:
        return True
    # 过多数字
    digits = len(re.findall(r"\d", text))
    if len(text) > 0 and digits / len(text) > 0.5:
        return True
    # 宗教文本关键词黑名单（CCMatrix 中占比很高，与影视场景无关）
    religious_keywords = [
        # 中文
        "真主", "安拉", "阿拉", "穆罕默德", "易卜拉欣", "鲁特",
        "耶和华", "耶稣", "基督", "圣经",
        # 日文
        "アッラー", "ムハンマド", "イブラーヒーム", "ルート", "クルアーン",
        "主よ", "不信心", "慈悲あまねく", "啓示",
        # 韩文
        "하나님", "예수", "기독교", "성경", "알라",
        # 英文
        "qur'an", "quran", "allah", "muhammad", "ibrahim", "jesus christ",
    ]
    lower_text = text.lower()
    for kw in religious_keywords:
        if kw in lower_text or kw in text:
            return True
    return False


def clean_text(text: str, is_target: bool) -> str | None:
    """清洗单句文本。"""
    text = text.strip()
    # 目标语言转简体
    if is_target:
        text = convert(text, "zh-cn")
    # 统一空格
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def process_pair(pair: str, args: argparse.Namespace) -> dict:
    print(f"\n[Processing {pair}]")
    try:
        ds = load_dataset(
            "yhavinga/ccmatrix",
            pair,
            streaming=True,
            split="train",
            trust_remote_code=True,
        )
    except Exception as e:
        print(f"  Failed to load: {e}")
        return {"status": "failed", "error": str(e)}

    kept = 0
    seen = 0
    duplicates = 0
    seen_hashes = set()
    output_lines = []

    out_path = Path(args.output) / f"{pair}.tsv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\n")
        for sample in ds:
            seen += 1
            if seen > args.max_pairs * 5:  # 最多看 5 倍目标量
                break

            trans = sample.get("translation", {})
            if not trans or len(trans) != 2:
                continue

            src, tgt = list(trans.values())
            src = clean_text(src, is_target=False)
            tgt = clean_text(tgt, is_target=True)

            if not src or not tgt:
                continue
            if not (args.min_len <= len(src) <= args.max_len):
                continue
            if not (args.min_len <= len(tgt) <= args.max_len):
                continue

            ratio = len(src) / len(tgt) if len(tgt) > 0 else 0
            if not (args.min_ratio <= ratio <= args.max_ratio):
                continue

            if is_noisy(src) or is_noisy(tgt):
                continue

            # 去重
            h = hashlib.md5(f"{src}\t{tgt}".encode("utf-8")).hexdigest()
            if h in seen_hashes:
                duplicates += 1
                continue
            seen_hashes.add(h)

            f.write(f"{src}\t{tgt}\n")
            output_lines.append((src, tgt))
            kept += 1

            if kept >= args.max_pairs:
                break

            if seen % 10000 == 0:
                print(f"  seen={seen}, kept={kept}, dup={duplicates}")

    return {
        "status": "ok",
        "pair": pair,
        "seen": seen,
        "kept": kept,
        "duplicates": duplicates,
        "output": str(out_path),
    }


def main():
    args = parse_args()
    stats = {}
    for pair in args.pairs:
        stats[pair] = process_pair(pair, args)

    stats_path = Path(args.output) / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"\nStats saved to {stats_path}")


if __name__ == "__main__":
    main()
