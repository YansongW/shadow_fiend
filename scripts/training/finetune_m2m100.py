#!/usr/bin/env python3
"""
Fine-tune facebook/m2m-100-418M on cleaned CCMatrix parallel corpus.

Usage:
    python scripts/training/finetune_m2m100.py \
        --data_dir data/translation_corpus_v0.0.5 \
        --output_dir models/m2m100-418M-zh-ja-ko-en \
        --model_name facebook/m2m-100-418M \
        --num_train_epochs 3 \
        --per_device_train_batch_size 8 \
        --learning_rate 5e-5

Requirements:
    pip install transformers datasets sacrebleu sentencepiece accelerate
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


LANG_MAP = {
    "ja-zh": "ja",
    "ko-zh": "ko",
    "en-zh": "en",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--model_name", default="facebook/m2m-100-418M")
    parser.add_argument("--max_source_length", type=int, default=128)
    parser.add_argument("--max_target_length", type=int, default=128)
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--per_device_train_batch_size", type=int, default=8)
    parser.add_argument("--per_device_eval_batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=5e-5)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--warmup_ratio", type=float, default=0.1)
    parser.add_argument("--save_steps", type=int, default=5000)
    parser.add_argument("--eval_steps", type=int, default=5000)
    parser.add_argument("--logging_steps", type=int, default=500)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4)
    parser.add_argument("--fp16", action="store_true")
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
            sources.append(src)
            targets.append(tgt)
    return sources, targets


def load_all_pairs(pairs: list[str], data_dir: Path):
    all_sources, all_targets, all_src_langs = [], [], []
    for pair in pairs:
        path = data_dir / f"{pair}.tsv"
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
        srcs, tgts = load_tsv(path)
        src_lang = LANG_MAP[pair]
        all_sources.extend(srcs)
        all_targets.extend(tgts)
        all_src_langs.extend([src_lang] * len(srcs))
    return all_sources, all_targets, all_src_langs


def split_raw_data(sources, targets, src_langs, valid_ratio: float = 0.1, test_ratio: float = 0.1):
    n = len(sources)
    indices = list(range(n))
    random.shuffle(indices)
    n_test = int(n * test_ratio)
    n_valid = int(n * valid_ratio)
    n_train = n - n_test - n_valid
    train_idx = indices[:n_train]
    valid_idx = indices[n_train:n_train + n_valid]
    test_idx = indices[n_train + n_valid:]
    return (
        [sources[i] for i in train_idx], [targets[i] for i in train_idx], [src_langs[i] for i in train_idx],
        [sources[i] for i in valid_idx], [targets[i] for i in valid_idx], [src_langs[i] for i in valid_idx],
        [sources[i] for i in test_idx], [targets[i] for i in test_idx], [src_langs[i] for i in test_idx],
    )


def build_dataset(sources, targets, src_langs, tokenizer, max_source_length: int, max_target_length: int):
    ds = Dataset.from_dict({
        "source": sources,
        "target": targets,
        "src_lang": src_langs,
    })

    def preprocess(example):
        tokenizer.src_lang = example["src_lang"]
        model_inputs = tokenizer(
            example["source"],
            max_length=max_source_length,
            truncation=True,
            padding=False,
        )
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(
                example["target"],
                max_length=max_target_length,
                truncation=True,
                padding=False,
            )
        model_inputs["labels"] = labels["input_ids"]
        model_inputs["forced_bos_token_id"] = tokenizer.lang_code_to_id["zh_CN"]
        return model_inputs

    ds = ds.map(preprocess, batched=False, remove_columns=ds.column_names)
    return ds


def save_test_set(test_sources, test_targets, test_src_langs, output_dir: Path):
    test_path = output_dir / "test_set.tsv"
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("source\ttarget\tsrc_lang\n")
        for src, tgt, lang in zip(test_sources, test_targets, test_src_langs):
            f.write(f"{src}\t{tgt}\t{lang}\n")
    print(f"Test set saved to {test_path}")


def main():
    args = parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    tokenizer = M2M100Tokenizer.from_pretrained(args.model_name)
    model = M2M100ForConditionalGeneration.from_pretrained(args.model_name)

    # 强制目标语言为简体中文
    model.config.forced_bos_token_id = tokenizer.lang_code_to_id["zh_CN"]

    pairs = ["ja-zh", "ko-zh", "en-zh"]
    data_dir = Path(args.data_dir)

    sources, targets, src_langs = load_all_pairs(pairs, data_dir)
    (
        train_src, train_tgt, train_lang,
        valid_src, valid_tgt, valid_lang,
        test_src, test_tgt, test_lang,
    ) = split_raw_data(sources, targets, src_langs)

    train_ds = build_dataset(
        train_src, train_tgt, train_lang,
        tokenizer, args.max_source_length, args.max_target_length,
    )
    valid_ds = build_dataset(
        valid_src, valid_tgt, valid_lang,
        tokenizer, args.max_source_length, args.max_target_length,
    )

    print(f"Train: {len(train_ds)}, Valid: {len(valid_ds)}, Test: {len(test_src)}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_test_set(test_src, test_tgt, test_lang, output_dir)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.num_train_epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_eval_batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        evaluation_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        fp16=args.fp16,
        report_to=["tensorboard"],
        remove_unused_columns=False,
    )

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Model saved to {output_dir}")


if __name__ == "__main__":
    main()
