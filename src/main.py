"""
shadow_fiend 入口模块。
"""

import argparse
import logging
import sys
import threading

from pipeline_streaming import StreamingTranslationPipeline

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
    parser.add_argument("--chunk-duration-ms", type=int, default=40, help="Audio chunk duration in ms (default 40)")
    parser.add_argument("--vad-threshold", type=float, default=0.4, help="Silero VAD speech threshold (default 0.4)")
    parser.add_argument("--vad-max-utterance-ms", type=int, default=5000, help="Max utterance length in ms (default 5000)")
    parser.add_argument("--vad-min-silence-ms", type=int, default=200, help="Min silence length to end utterance in ms (default 200)")
    parser.add_argument("--vad-min-speech-ms", type=int, default=150, help="Min speech length to form utterance in ms (default 150)")
    parser.add_argument("--asr-window-ms", type=int, default=500, help="Streaming ASR window in ms (default 500)")
    parser.add_argument("--asr-hop-ms", type=int, default=200, help="Streaming ASR hop in ms (default 200)")
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

    pipeline = StreamingTranslationPipeline(
        source_lang=args.source,
        target_lang=args.target,
        device_name=args.device,
        asr_device=args.asr_device,
        compact=args.compact,
        chunk_duration_ms=args.chunk_duration_ms,
        vad_threshold=args.vad_threshold,
        vad_max_utterance_ms=args.vad_max_utterance_ms,
        vad_min_silence_ms=args.vad_min_silence_ms,
        vad_min_speech_ms=args.vad_min_speech_ms,
        asr_window_ms=args.asr_window_ms,
        asr_hop_ms=args.asr_hop_ms,
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
