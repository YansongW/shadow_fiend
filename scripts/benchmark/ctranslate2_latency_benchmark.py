#!/usr/bin/env python3
"""
CTranslate2 vs Transformers 翻译延迟基准测试（隔离环境版）。

测试目标：
- 在 shadow_fiend 实际关心的短句上，对比 transformers + opus-mt 与 CTranslate2 的延迟。
- 验证 INT8 量化对延迟和翻译质量的影响。

用法：
    source .venv-ctranslate2-benchmark/bin/activate
    python scripts/benchmark/ctranslate2_latency_benchmark.py

输出：
    /tmp/ctranslate2_benchmark/report.json
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

import psutil
import sacrebleu

# ---------- 配置 ----------

MODEL_NAMES = {
    "ja-en": "Helsinki-NLP/opus-mt-ja-en",
    "en-zh": "Helsinki-NLP/opus-mt-en-zh",
}

# 日语/英语/中文短句，模拟 VAD 切出的 utterance
TEST_SENTENCES = {
    "ja-en": [
        "こんにちは",
        "ありがとうございます",
        "すみません、少し待ってください",
        "これは本当に美味しいですね",
        "明日の会議は何時からですか",
        "私はこの映画が好きです",
        "駅までどうやって行きますか",
        "お元気ですか",
        "さようなら、また明日",
        "この本を貸してください",
    ],
    "en-zh": [
        "Hello",
        "Thank you very much",
        "I'm sorry, please wait a moment",
        "This is really delicious",
        "What time does the meeting start tomorrow",
        "I like this movie",
        "How do I get to the station",
        "How are you",
        "Goodbye, see you tomorrow",
        "Please lend me this book",
    ],
}

CACHE_DIR = Path.home() / ".cache" / "shadow_fiend_ct2_benchmark"
CT2_MODEL_ROOT = CACHE_DIR / "ct2_models"
REPORT_DIR = Path("/tmp/ctranslate2_benchmark")
WARMUP_RUNS = 5
BENCHMARK_RUNS = 20


# ---------- 工具函数 ----------


def get_memory_mb() -> float:
    """返回当前进程 RSS 内存（MB）。"""
    return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)


def convert_model(pair: str, quantization: str | None) -> Path:
    """将 HF opus-mt 模型转换为 CTranslate2 格式。"""
    model_name = MODEL_NAMES[pair]
    quant_suffix = quantization or "fp32"
    output_dir = CT2_MODEL_ROOT / f"{pair.replace('-', '_')}_{quant_suffix}"

    if output_dir.exists():
        print(f"[convert] {pair} {quant_suffix} already exists at {output_dir}")
        return output_dir

    print(f"[convert] {pair} -> {quant_suffix} ...")
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "ctranslate2.converters.transformers",
        "--model",
        model_name,
        "--output_dir",
        str(output_dir),
        "--trust_remote_code",
    ]
    if quantization:
        cmd.extend(["--quantization", quantization])

    cmd.append("--force")
    subprocess.run(cmd, check=True)
    return output_dir


def benchmark_transformers(sentences: List[str], pair: str) -> dict:
    """使用 transformers + opus-mt 翻译并测量延迟。"""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    model_name = MODEL_NAMES[pair]
    print(f"[transformers] loading {model_name} ...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(CACHE_DIR / "hf"))
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=str(CACHE_DIR / "hf"))
    model.eval()

    # warmup
    for s in sentences[:WARMUP_RUNS]:
        inputs = tokenizer(s, return_tensors="pt", padding=True)
        with torch.no_grad():
            model.generate(**inputs, num_beams=1, max_length=128)

    latencies = []
    mem_before = get_memory_mb()
    for _ in range(BENCHMARK_RUNS):
        for s in sentences:
            inputs = tokenizer(s, return_tensors="pt", padding=True)
            start = time.perf_counter()
            with torch.no_grad():
                outputs = model.generate(**inputs, num_beams=1, max_length=128)
            latencies.append((time.perf_counter() - start) * 1000)
    mem_after = get_memory_mb()

    # 生成参考翻译用于质量评估
    translations = []
    for s in sentences:
        inputs = tokenizer(s, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = model.generate(**inputs, num_beams=1, max_length=128)
        translations.append(tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].strip())

    return {
        "backend": "transformers",
        "pair": pair,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "p50": round(sorted(latencies)[len(latencies) // 2], 2),
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
        },
        "memory_mb": round(mem_after - mem_before, 2),
        "translations": translations,
    }


def benchmark_ctranslate2(sentences: List[str], pair: str, quantization: str | None) -> dict:
    """使用 CTranslate2 翻译并测量延迟。"""
    import ctranslate2

    model_dir = convert_model(pair, quantization)
    backend_label = f"ctranslate2_{quantization or 'fp32'}"
    print(f"[{backend_label}] loading {model_dir} ...")

    compute_type = quantization or "default"
    translator = ctranslate2.Translator(str(model_dir), device="cpu", compute_type=compute_type)

    # 使用 transformers tokenizer（CTranslate2 不自带 tokenizer）
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAMES[pair], cache_dir=str(CACHE_DIR / "hf"))

    def translate(text: str) -> str:
        tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
        results = translator.translate_batch([tokens], beam_size=1, max_decoding_length=128)
        output_tokens = results[0].hypotheses[0]
        return tokenizer.decode(tokenizer.convert_tokens_to_ids(output_tokens), skip_special_tokens=True).strip()

    # warmup
    for s in sentences[:WARMUP_RUNS]:
        translate(s)

    latencies = []
    mem_before = get_memory_mb()
    for _ in range(BENCHMARK_RUNS):
        for s in sentences:
            start = time.perf_counter()
            translate(s)
            latencies.append((time.perf_counter() - start) * 1000)
    mem_after = get_memory_mb()

    translations = [translate(s) for s in sentences]

    return {
        "backend": backend_label,
        "pair": pair,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 2),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "p50": round(sorted(latencies)[len(latencies) // 2], 2),
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
        },
        "memory_mb": round(mem_after - mem_before, 2),
        "translations": translations,
    }


def compute_bleu(references: List[str], hypotheses: List[str]) -> float:
    """计算 sacreBLEU（单句列表用 corpus_bleu）。"""
    refs = [[r] for r in references]
    return sacrebleu.corpus_bleu(hypotheses, list(zip(*refs))).score


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    import torch  # noqa: F401

    results = []

    for pair in MODEL_NAMES:
        sentences = TEST_SENTENCES[pair]
        print(f"\n===== Pair: {pair} =====")

        # transformers 基准
        r_tf = benchmark_transformers(sentences, pair)
        results.append(r_tf)
        print(f"  transformers mean={r_tf['latency_ms']['mean']} ms")

        # CTranslate2 fp32
        r_ct2_fp32 = benchmark_ctranslate2(sentences, pair, quantization=None)
        results.append(r_ct2_fp32)
        print(f"  ctranslate2_fp32 mean={r_ct2_fp32['latency_ms']['mean']} ms")

        # CTranslate2 int8
        r_ct2_int8 = benchmark_ctranslate2(sentences, pair, quantization="int8")
        results.append(r_ct2_int8)
        print(f"  ctranslate2_int8 mean={r_ct2_int8['latency_ms']['mean']} ms")

        # 以 transformers 为参考，计算 CTranslate2 的 BLEU
        bleu_fp32 = compute_bleu(r_tf["translations"], r_ct2_fp32["translations"])
        bleu_int8 = compute_bleu(r_tf["translations"], r_ct2_int8["translations"])
        r_ct2_fp32["bleu_vs_transformers"] = round(bleu_fp32, 2)
        r_ct2_int8["bleu_vs_transformers"] = round(bleu_int8, 2)
        print(f"  BLEU vs transformers: fp32={bleu_fp32:.2f}, int8={bleu_int8:.2f}")

    report_path = REPORT_DIR / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
