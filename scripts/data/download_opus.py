#!/usr/bin/env python3
"""
下载 OPUS 平行语料并转换为 TSV。
支持语言对：ja-zh, ko-zh, en-zh
"""

from __future__ import annotations

import argparse
import re
import zipfile
from io import BytesIO
from pathlib import Path

import requests
from tqdm import tqdm


DATASETS = [
    ("TED2020", "v1"),
    ("Wikipedia", "v20210402"),
    ("News-Commentary", "v16"),
]

PAIRS = ["ja-zh", "ko-zh", "en-zh"]


def opus_url(corpus: str, version: str, pair: str) -> str:
    return f"https://object.pouta.csc.fi/OPUS-{corpus}/{version}/moses/{pair}.txt.zip"


def download_zip(url: str) -> bytes | None:
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            return None
        return resp.content
    except Exception as e:
        print(f"  Download error: {e}")
        return None


def extract_parallel(zip_bytes: bytes, pair: str) -> tuple[list[str], list[str]]:
    src_lang, tgt_lang = pair.split("-")
    src_lines, tgt_lines = [], []
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        src_file = f"{pair}.{src_lang}"
        tgt_file = f"{pair}.{tgt_lang}"
        if src_file not in zf.namelist() or tgt_file not in zf.namelist():
            # try alternative naming
            alt_src = [n for n in zf.namelist() if n.endswith(f".{src_lang}")]
            alt_tgt = [n for n in zf.namelist() if n.endswith(f".{tgt_lang}")]
            if not alt_src or not alt_tgt:
                raise ValueError(f"Cannot find {src_file} or {tgt_file} in zip")
            src_file, tgt_file = alt_src[0], alt_tgt[0]
        with zf.open(src_file) as f:
            src_lines = [line.decode("utf-8").strip() for line in f]
        with zf.open(tgt_file) as f:
            tgt_lines = [line.decode("utf-8").strip() for line in f]
    return src_lines, tgt_lines


def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/translation_corpus_opus")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    for pair in PAIRS:
        all_src, all_tgt = [], []
        for corpus, version in DATASETS:
            url = opus_url(corpus, version, pair)
            print(f"Downloading {corpus}/{version} {pair} ...")
            zip_bytes = download_zip(url)
            if zip_bytes is None:
                print(f"  Not available, skipping.")
                continue
            try:
                src_lines, tgt_lines = extract_parallel(zip_bytes, pair)
            except Exception as e:
                print(f"  Extraction error: {e}, skipping.")
                continue
            if len(src_lines) != len(tgt_lines):
                print(f"  Mismatched line counts ({len(src_lines)} vs {len(tgt_lines)}), skipping.")
                continue
            print(f"  Got {len(src_lines)} pairs")
            all_src.extend(src_lines)
            all_tgt.extend(tgt_lines)

        if not all_src:
            print(f"No data for {pair}")
            continue

        out_path = out_dir / f"{pair}.tsv"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("source\ttarget\n")
            for src, tgt in zip(all_src, all_tgt):
                src = clean_text(src)
                tgt = clean_text(tgt)
                if not src or not tgt:
                    continue
                f.write(f"{src}\t{tgt}\n")
        print(f"Wrote {len(all_src)} pairs to {out_path}")


if __name__ == "__main__":
    main()
