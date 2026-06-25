#!/usr/bin/env python3
"""
测试翻译模块。

用法：
    ./scripts/test_translation.py --source en --target zh "Hello world"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from translation.argos_engine import TranslationModule


def main():
    parser = argparse.ArgumentParser(description="Shadow Fiend translation test")
    parser.add_argument("text", help="Text to translate")
    parser.add_argument("--source", default="en", help="Source language")
    parser.add_argument("--target", default="zh", help="Target language")
    args = parser.parse_args()

    print("Shadow Fiend translation test")
    print("=" * 40)

    translator = TranslationModule(args.source, args.target)
    result = translator.translate(args.text)
    print(f"[{args.source}] {args.text}")
    print(f"[{args.target}] {result}")


if __name__ == "__main__":
    main()
