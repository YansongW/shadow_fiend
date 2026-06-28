# v0.0.5 Fine-tuning Task

## Objective
Fine-tune `facebook/m2m100_418M` on the cleaned v0.0.5 parallel corpus (586k unique pairs across ja-zh, ko-zh, en-zh) and publish the model to Hugging Face.

## Data Location
Local directory (gitignored): `data/translation_corpus_final/`
- `train.tsv`: 574,465 pairs
- `val.tsv`: 5,861 pairs
- `test.tsv`: 5,861 pairs

If the data is not on the target machine, run the data pipeline from `main` first:
```bash
git checkout main
bash scripts/data/pipeline_v0.0.5_large_from_langid.sh
bash scripts/data/pipeline_opus.sh
.venv/bin/python scripts/data/generate_final_report.py
```

## Branch
`v0.0.5-finetune`

## Hardware
Apple Silicon Mac mini with MPS support. Expected memory usage: ~10–14 GB during training.

## Training
```bash
cd /path/to/shadow_fiend
bash scripts/training/train_and_publish.sh
```

The wrapper:
1. Runs `finetune_m2m100_v0.0.5.py`.
2. On success, commits any code changes and pushes to `origin v0.0.5-finetune`.
3. Uploads the trained model to Hugging Face.

## Training Hyperparameters (Mac mini friendly)
- Model: `facebook/m2m100_418M`
- Epochs: 3
- Batch size: 2 per device
- Gradient accumulation: 16 (effective batch 32)
- Max source/target length: 128
- Learning rate: 5e-5
- Weight decay: 0.01
- Warmup ratio: 0.1
- FP16: disabled on MPS (MPS does not fully support fp16 training for this model)
- Device: auto-detected (`mps` if available, else `cpu`)

## Expected Outputs
- Local model: `models/m2m100-418M-zh-ja-ko-en-v0.0.5/`
- Hugging Face repo: `YansongW/m2m100-418M-zh-ja-ko-en-v0.0.5`

## Environment Variables
```bash
export HF_TOKEN=your_huggingface_write_token
export HF_REPO_ID=YansongW/m2m100-418M-zh-ja-ko-en-v0.0.5
```

## Troubleshooting
- **OOM**: reduce `--per_device_train_batch_size` to 1 and increase `--gradient_accumulation_steps` to 32.
- **MPS error**: training script auto-falls back to CPU if MPS fails.
- **Data not found**: re-run data pipeline on `main` or copy `data/translation_corpus_final/` from another machine.

## Post-training
After the model is uploaded, create a model card on Hugging Face and tag with:
- `m2m100`
- `translation`
- `ja-zh`, `ko-zh`, `en-zh`
- `mac-mini`, `mps`
