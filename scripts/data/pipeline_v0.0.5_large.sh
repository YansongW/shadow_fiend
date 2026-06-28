#!/bin/bash
# v0.0.5 大规模数据清洗 pipeline
# 从 CCMatrix 下载 300k/语言对，并完成语言识别、LaBSE、领域过滤

set -e

BASE_DIR="data/translation_corpus_v0.0.5_large"
PAIRS="ja-zh ko-zh en-zh"
MAX_PAIRS=300000
VENV=".venv/bin/python"

mkdir -p "$BASE_DIR"

echo "[1/4] Downloading CCMatrix (max $MAX_PAIRS per pair)..."
HF_ENDPOINT=https://hf-mirror.com $VENV scripts/data/download_and_clean_ccmatrix.py \
    --pairs ja-zh ko-zh en-zh \
    --output "$BASE_DIR" \
    --max_pairs $MAX_PAIRS

echo "[2/4] Language identification (fasttext)..."
for pair in $PAIRS; do
    $VENV scripts/data/filter_parallel_data_langid.py \
        --input "$BASE_DIR/${pair}.tsv" \
        --output "$BASE_DIR/${pair}.langid.tsv" \
        --pair $pair \
        --threshold 0.9
done

echo "[3/4] LaBSE semantic filtering..."
for pair in $PAIRS; do
    $VENV scripts/data/filter_parallel_data_labse.py \
        --input "$BASE_DIR/${pair}.langid.tsv" \
        --output "$BASE_DIR/${pair}.labse.tsv" \
        --threshold 0.6 \
        --batch_size 32 \
        --device cpu
done

echo "[4/4] Domain/religion/low-quality filtering..."
for pair in $PAIRS; do
    $VENV scripts/data/filter_parallel_data_domain.py \
        --input "$BASE_DIR/${pair}.labse.tsv" \
        --output "$BASE_DIR/${pair}.domain.tsv" \
        --pair $pair
done

echo "Pipeline completed. Results in $BASE_DIR"
