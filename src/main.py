"""
YingMo 入口模块。
"""

import argparse
import logging
import sys

from pipeline import TranslationPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="YingMo — Open real-time subtitle translation")
    parser.add_argument("--source", default="auto", help="Source language code (e.g. ja, ko, zh, en)")
    parser.add_argument("--target", default="zh", help="Target language code (e.g. zh, en)")
    parser.add_argument("--device", default="BlackHole 2ch", help="Audio input device name")
    parser.add_argument("--compact", action="store_true", help="Show only translated text")
    args = parser.parse_args()

    print(f"YingMo 影魔 启动中...")
    print(f"源语言: {args.source}, 目标语言: {args.target}")
    print("按 Ctrl+C 退出")

    pipeline = TranslationPipeline(
        source_lang=args.source,
        target_lang=args.target,
        device_name=args.device,
        compact=args.compact,
    )

    try:
        pipeline.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        pipeline.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
