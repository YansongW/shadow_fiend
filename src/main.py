"""
YiMu 入口模块。
MVE 阶段先打印项目信息，后续实现完整启动逻辑。
"""

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="YiMu — Open real-time subtitle translation")
    parser.add_argument("--source", default="auto", help="Source language code (e.g. ja, ko, zh)")
    parser.add_argument("--target", default="zh", help="Target language code (e.g. zh, en)")
    args = parser.parse_args()

    print(f"YiMu 启动中...")
    print(f"源语言: {args.source}, 目标语言: {args.target}")
    print("MVE 1 尚未完成，请等待后续实现。")


if __name__ == "__main__":
    main()
