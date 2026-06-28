#!/bin/bash
# OPUS 数据清洗 pipeline

set -e

BASE_DIR="data/translation_corpus_opus"
PAIRS="ja-zh ko-zh en-zh"
VENV=".venv/bin/python"

echo "[1/3] Language identification..."
for pair in $PAIRS; do
    $VENV scripts/data/filter_parallel_data_langid.py \
        --input "$BASE_DIR/${pair}.tsv" \
        --output "$BASE_DIR/${pair}.langid.tsv" \
        --pair $pair \
        --threshold 0.9
done

echo "[2/3] LaBSE semantic filtering..."
for pair in $PAIRS; do
    $VENV scripts/data/filter_parallel_data_labse.py \
        --input "$BASE_DIR/${pair}.langid.tsv" \
        --output "$BASE_DIR/${pair}.labse.tsv" \
        --threshold 0.6 \
        --batch_size 32 \
        --device cpu
done

echo "[3/3] Domain filtering..."
for pair in $PAIRS; do
    $VENV scripts/data/filter_parallel_data_domain.py \
        --input "$BASE_DIR/${pair}.labse.tsv" \
        --output "$BASE_DIR/${pair}.domain.tsv" \
        --pair $pair
done

echo "OPUS pipeline completed."
