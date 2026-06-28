#!/usr/bin/env python3
"""
Fine-tune facebook/m2m100_418M on the v0.0.5 final corpus.

Reads pre-split train.tsv / val.tsv / test.tsv from --data_dir.
Optimized for Apple Silicon Mac mini (MPS).

Usage:
    .venv/bin/python scripts/training/finetune_m2m100_v0.0.5.py \
        --data_dir data/translation_corpus_final \
        --output_dir models/m2m100-418M-zh-ja-ko-en-v0.0.5
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset
from transformers import (
    M2M100ForConditionalGeneration,
    M2M100Tokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True, help="Directory containing train.tsv, val.tsv, test.tsv")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--model_name", default="facebook/m2m100_418M")
    parser.add_argument("--max_source_length", type=int, default=128)
    parser.add_argument("--max_target_length", type=int, default=128)
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--max_steps", type=int, default=-1, help="If > 0, overrides num_train_epochs")
    parser.add_argument("--per_device_train_batch_size", type=int, default=2)
    parser.add_argument("--per_device_eval_batch_size", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--warmup_ratio", type=float, default=0.1)
    parser.add_argument("--save_steps", type=int, default=5000)
    parser.add_argument("--eval_steps", type=int, default=5000)
    parser.add_argument("--logging_steps", type=int, default=500)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def load_tsv(path: Path):
    sources, targets = [], []
    with open(path, "r", encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            src, tgt = parts
            if not src or not tgt:
                continue
            sources.append(src)
            targets.append(tgt)
    return sources, targets


def build_dataset(sources, targets, src_langs, tokenizer, max_source_length: int, max_target_length: int):
    ds = Dataset.from_dict({
        "source": sources,
        "target": targets,
        "src_lang": src_langs,
    })

    def preprocess(example):
        tokenizer.src_lang = example["src_lang"]
        tokenizer.tgt_lang = "zh"
        model_inputs = tokenizer(
            example["source"],
            max_length=max_source_length,
            truncation=True,
            padding=False,
        )
        labels = tokenizer(
            text_target=example["target"],
            max_length=max_target_length,
            truncation=True,
            padding=False,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    ds = ds.map(preprocess, batched=False, remove_columns=ds.column_names)
    return ds


def detect_device():
    if torch.backends.mps.is_available():
        try:
            # Quick MPS smoke test
            torch.zeros(1).to("mps")
            return "mps"
        except Exception:
            print("MPS available but failed smoke test, falling back to CPU")
            return "cpu"
    return "cpu"


def main():
    args = parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = detect_device()
    print(f"Using device: {device}")

    print(f"Loading model and tokenizer: {args.model_name}")
    tokenizer = M2M100Tokenizer.from_pretrained(args.model_name)
    model = M2M100ForConditionalGeneration.from_pretrained(args.model_name)
    model.to(device)

    # Force target language to Chinese
    model.config.forced_bos_token_id = tokenizer.lang_code_to_id["zh"]

    # Load pre-split data
    print(f"Loading data from {data_dir}")
    train_src, train_tgt = load_tsv(data_dir / "train.tsv")
    val_src, val_tgt = load_tsv(data_dir / "val.tsv")
    test_src, test_tgt = load_tsv(data_dir / "test.tsv")

    # Assign source languages based on file content heuristic
    # Since final corpus mixes pairs, we infer from source script.
    # Fallback: metadata.jsonl contains the pair info.
    def infer_src_lang(text: str) -> str:
        # Simple heuristic: presence of Hiragana/Katakana -> ja, Hangul -> ko, else en
        # This is imperfect but sufficient for M2M100 which uses lang codes.
        if any("\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" for c in text):
            return "ja"
        if any("\uac00" <= c <= "\ud7af" for c in text):
            return "ko"
        return "en"

    train_lang = [infer_src_lang(s) for s in train_src]
    val_lang = [infer_src_lang(s) for s in val_src]
    test_lang = [infer_src_lang(s) for s in test_src]

    print(f"Train: {len(train_src)}, Val: {len(val_src)}, Test: {len(test_src)}")

    # Save test set for later evaluation
    test_path = output_dir / "test_set.tsv"
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\tsrc_lang\n")
        for src, tgt, lang in zip(test_src, test_tgt, test_lang):
            f.write(f"{src}\t{tgt}\t{lang}\n")
    print(f"Test set saved to {test_path}")

    train_ds = build_dataset(
        train_src, train_tgt, train_lang,
        tokenizer, args.max_source_length, args.max_target_length,
    )
    val_ds = build_dataset(
        val_src, val_tgt, val_lang,
        tokenizer, args.max_source_length, args.max_target_length,
    )

    # MPS does not fully support fp16 for this model; keep fp16 disabled.
    fp16 = False

    training_args_kwargs = dict(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        fp16=fp16,
        report_to=["tensorboard"],
        remove_unused_columns=False,
        # Mac-friendly defaults
        dataloader_num_workers=0,
    )

    if args.max_steps > 0:
        training_args_kwargs["max_steps"] = args.max_steps
    else:
        training_args_kwargs["num_train_epochs"] = args.num_train_epochs

    training_args = Seq2SeqTrainingArguments(**training_args_kwargs)

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Model saved to {output_dir}")


if __name__ == "__main__":
    main()
