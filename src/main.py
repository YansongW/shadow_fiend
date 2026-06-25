"""
shadow_fiend 入口模块。
"""

import argparse
import logging
import sys
import threading

from pipeline import TranslationPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="shadow_fiend — Open real-time subtitle translation")
    parser.add_argument("--source", default="auto", help="Source language code (e.g. ja, ko, zh, en)")
    parser.add_argument("--target", default="zh", help="Target language code (e.g. zh, en)")
    parser.add_argument("--device", default="BlackHole 2ch", help="Audio input device name")
    parser.add_argument("--asr-device", default="auto", help="Device for ASR inference (auto/cpu/cuda/mps)")
    parser.add_argument("--max-utterance-ms", type=int, default=5000, help="Max utterance length in ms (default 5000)")
    parser.add_argument("--min-silence-ms", type=int, default=350, help="Min silence length to end utterance in ms (default 350)")
    parser.add_argument("--min-speech-ms", type=int, default=200, help="Min speech length to form utterance in ms (default 200)")
    parser.add_argument("--compact", action="store_true", help="Show only translated text")
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Auto-stop after N seconds (useful for automated testing)",
    )
    args = parser.parse_args()

    print(f"shadow_fiend 启动中...")
    print(f"源语言: {args.source}, 目标语言: {args.target}")
    if args.duration:
        print(f"测试模式：{args.duration} 秒后自动退出")
    print("按 Ctrl+C 退出")

    pipeline = TranslationPipeline(
        source_lang=args.source,
        target_lang=args.target,
        device_name=args.device,
        asr_device=args.asr_device,
        compact=args.compact,
        max_utterance_ms=args.max_utterance_ms,
        min_silence_ms=args.min_silence_ms,
        min_speech_ms=args.min_speech_ms,
    )

    timer = None
    if args.duration:

        def _auto_stop():
            print("\n[test] 达到设定运行时长，自动退出")
            pipeline.stop()

        timer = threading.Timer(args.duration, _auto_stop)
        timer.daemon = True
        timer.start()

    try:
        pipeline.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        pipeline.stop()
        sys.exit(0)
    finally:
        if timer is not None:
            timer.cancel()


if __name__ == "__main__":
    main()
