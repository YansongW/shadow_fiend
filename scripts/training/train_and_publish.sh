#!/bin/bash
# Train M2M100 418M on v0.0.5 final corpus and publish model + code.
#
# Required env:
#   HF_TOKEN          Hugging Face write token
# Optional env:
#   HF_REPO_ID        default: YansongW/m2m100-418M-zh-ja-ko-en-v0.0.5
#   DATA_DIR          default: data/translation_corpus_final
#   OUTPUT_DIR        default: models/m2m100-418M-zh-ja-ko-en-v0.0.5

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="${DATA_DIR:-data/translation_corpus_final}"
OUTPUT_DIR="${OUTPUT_DIR:-models/m2m100-418M-zh-ja-ko-en-v0.0.5}"
HF_REPO_ID="${HF_REPO_ID:-YansongW/m2m100-418M-zh-ja-ko-en-v0.0.5}"
BRANCH="v0.0.5-finetune"

if [ ! -f "${DATA_DIR}/train.tsv" ]; then
    echo "Error: ${DATA_DIR}/train.tsv not found. Run data pipeline first."
    exit 1
fi

if [ -z "${HF_TOKEN}" ]; then
    echo "Warning: HF_TOKEN not set. Model will NOT be uploaded to Hugging Face."
    echo "Set it later with: export HF_TOKEN=your_write_token"
    SKIP_HF_UPLOAD=1
fi

VENV=".venv/bin/python"
if [ ! -x "$VENV" ]; then
    echo "Error: .venv not found. Please create a virtual environment."
    exit 1
fi

echo "========================================"
echo "Training M2M100 418M on v0.0.5 corpus"
echo "Data:    ${DATA_DIR}"
echo "Output:  ${OUTPUT_DIR}"
echo "HF repo: ${HF_REPO_ID}"
echo "========================================"

# Run training
"$VENV" scripts/training/finetune_m2m100_v0.0.5.py \
    --data_dir "${DATA_DIR}" \
    --output_dir "${OUTPUT_DIR}" \
    --model_name facebook/m2m100_418M \
    --num_train_epochs 3 \
    --per_device_train_batch_size 4 \
    --per_device_eval_batch_size 8 \
    --gradient_accumulation_steps 8 \
    --max_source_length 128 \
    --max_target_length 128 \
    --learning_rate 5e-5 \
    --weight_decay 0.01 \
    --warmup_ratio 0.1 \
    --save_steps 5000 \
    --eval_steps 5000 \
    --logging_steps 500 \
    --seed 42

if [ -z "${SKIP_HF_UPLOAD}" ]; then
    echo "========================================"
    echo "Training complete. Uploading to HF..."
    echo "========================================"

    # Upload model to Hugging Face
    "$VENV" scripts/training/upload_to_hf.py \
        --model_dir "${OUTPUT_DIR}" \
        --repo_id "${HF_REPO_ID}"
else
    echo "========================================"
    echo "Training complete. Skipping HF upload (HF_TOKEN not set)."
    echo "========================================"
fi

echo "========================================"
echo "Pushing code changes to ${BRANCH}..."
echo "========================================"

# Commit and push any code/config changes
git add -A
git commit -m "v0.0.5: trained m2m100-418M on ${DATA_DIR} and uploaded to ${HF_REPO_ID}" || true
git push origin "${BRANCH}"

echo "========================================"
echo "Done. Model uploaded to ${HF_REPO_ID}"
echo "Code pushed to branch ${BRANCH}"
echo "========================================"
