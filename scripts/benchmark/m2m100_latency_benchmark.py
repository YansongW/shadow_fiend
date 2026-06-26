#!/usr/bin/env python3
"""
m2m-100 418M 本地推理延迟与质量基准测试（隔离环境版）。

用法：
    source .venv-m2m-benchmark/bin/activate
    python scripts/benchmark/m2m100_latency_benchmark.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List

import psutil
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_NAME = "/tmp/m2m100_418M"
CACHE_DIR = Path.home() / ".cache" / "shadow_fiend_m2m_benchmark"
REPORT_DIR = Path("/tmp/m2m100_benchmark")
WARMUP_RUNS = 3
BENCHMARK_RUNS = 10

TEST_SENTENCES = {
    "ja-zh": [
        "こんにちは",
        "ありがとう",
        "すみません",
        "さようなら",
        "これは本当に美味しいですね",
        "明日の会議は何時からですか",
        "私はこの映画が好きです",
        "駅までどうやって行きますか",
        "お元気ですか",
        "この本を貸してください",
    ],
    "ko-zh": [
        "안녕하세요",
        "감사합니다",
        "죄송합니다",
        "안녕히 가세요",
        "이 영화 정말 재미있어요",
        "내일 회의는 몇 시에 시작하나요",
        "저는 이 책을 좋아해요",
        "역까지 어떻게 가나요",
        "잘 지내세요",
        "이 책 좀 빌려주세요",
    ],
    "en-zh": [
        "Hello",
        "Thank you",
        "I'm sorry",
        "Goodbye",
        "This is really delicious",
        "What time does the meeting start tomorrow",
        "I like this movie",
        "How do I get to the station",
        "How are you",
        "Please lend me this book",
    ],
}

LANG_MAP = {
    "ja-zh": ("ja", "zh"),
    "ko-zh": ("ko", "zh"),
    "en-zh": ("en", "zh"),
}


def get_memory_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def benchmark_m2m(pair: str) -> dict:
    src_lang, tgt_lang = LANG_MAP[pair]
    print(f"\n[Loading {MODEL_NAME} for {pair} ...]")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=str(CACHE_DIR))
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, cache_dir=str(CACHE_DIR))
    model.eval()

    # m2m-100 需要设置目标语言 token
    forced_bos_token_id = tokenizer.lang_code_to_id[tgt_lang]

    sentences = TEST_SENTENCES[pair]

    def translate(text: str) -> str:
        inputs = tokenizer(text, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=128,
                num_beams=1,
            )
        return tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].strip()

    # warmup
    print("[Warming up ...]")
    for s in sentences[:WARMUP_RUNS]:
        translate(s)

    latencies = []
    mem_before = get_memory_mb()
    print("[Benchmarking ...]")
    for _ in range(BENCHMARK_RUNS):
        for s in sentences:
            start = time.perf_counter()
            translate(s)
            latencies.append((time.perf_counter() - start) * 1000)
    mem_after = get_memory_mb()

    translations = [translate(s) for s in sentences]

    return {
        "model": MODEL_NAME,
        "pair": pair,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "p50": round(sorted(latencies)[len(latencies) // 2], 2),
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
        },
        "memory_mb": round(mem_after - mem_before, 2),
        "translations": list(zip(sentences, translations)),
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for pair in TEST_SENTENCES:
        results.append(benchmark_m2m(pair))

    report_path = REPORT_DIR / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
