"""
shadow_fiend v0.0.2 端到端延迟测试。

模拟实时音频流，把合成音频按 chunk 喂给 VAD -> 流式 ASR -> 翻译，
记录各阶段耗时，不启动 UI/PyAudio。
"""

from __future__ import annotations

import argparse
import json
import logging
import wave
from pathlib import Path
from typing import Optional

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audio.silero_vad import SileroVADModule
from asr.streaming_sensevoice import StreamingSenseVoiceASR
from translation.argos_engine import TranslationModule

logging.basicConfig(level=logging.WARNING)


def load_audio(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as f:
        nchannels = f.getnchannels()
        sampwidth = f.getsampwidth()
        framerate = f.getframerate()
        nframes = f.getnframes()
        raw = f.readframes(nframes)

    if sampwidth == 2:
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    if nchannels == 2:
        audio = audio.reshape(-1, 2).mean(axis=1)
    return audio, framerate


def _record_first(value: Optional[float], marker: list) -> None:
    if marker[0] is None:
        marker[0] = value


def simulate_streaming(
    audio: np.ndarray,
    sample_rate: int,
    source_lang: str,
    target_lang: str,
    chunk_duration_ms: int = 40,
    asr_window_ms: int = 500,
    asr_hop_ms: int = 200,
    vad_threshold: float = 0.5,
    vad_min_speech_ms: int = 200,
    vad_min_silence_ms: int = 300,
    vad_max_utterance_ms: int = 5000,
    asr_device: str = "auto",
    warmup: bool = True,
) -> dict:
    import time

    chunk_samples = int(sample_rate * chunk_duration_ms / 1000)
    total_samples = len(audio)

    vad = SileroVADModule(
        sample_rate=sample_rate,
        threshold=vad_threshold,
        min_speech_ms=vad_min_speech_ms,
        min_silence_ms=vad_min_silence_ms,
        max_utterance_ms=vad_max_utterance_ms,
        device=asr_device,
    )
    asr = StreamingSenseVoiceASR(
        device=asr_device,
        window_ms=asr_window_ms,
        hop_ms=asr_hop_ms,
    )
    if warmup:
        asr.warmup(language=source_lang)
    translator = TranslationModule(
        source_lang=source_lang,
        target_lang=target_lang,
    )

    start_time = time.perf_counter()
    first_vad_speech_ms: list[Optional[float]] = [None]
    first_partial_ms: list[Optional[float]] = [None]
    first_partial_text: list[Optional[str]] = [None]
    first_final_ms: list[Optional[float]] = [None]
    first_final_text: list[Optional[str]] = [None]
    first_translation_ms: list[Optional[float]] = [None]
    first_translation_text: list[Optional[str]] = [None]

    partial_count = 0
    final_count = 0

    def handle_final(text: str, lang: str) -> None:
        nonlocal final_count
        final_count += 1
        if first_final_ms[0] is None:
            first_final_ms[0] = (time.perf_counter() - start_time) * 1000
            first_final_text[0] = text
        try:
            translated = translator.translate(text)
            if first_translation_ms[0] is None:
                first_translation_ms[0] = (time.perf_counter() - start_time) * 1000
                first_translation_text[0] = translated
        except Exception as e:
            logging.error("Translation error: %s", e)

    offset = 0
    while offset < total_samples:
        chunk = audio[offset:offset + chunk_samples]
        if len(chunk) < chunk_samples:
            chunk = np.pad(chunk, (0, chunk_samples - len(chunk)))

        now_ms = (time.perf_counter() - start_time) * 1000

        was_speaking = vad._is_speaking
        utterances = vad.add_audio(chunk)
        is_speaking = vad._is_speaking

        if not was_speaking and is_speaking:
            _record_first(now_ms, first_vad_speech_ms)
            asr.reset()

        if is_speaking:
            asr_result = asr.feed_audio(chunk, language=source_lang)
            if asr_result and asr_result.text:
                partial_count += 1
                if first_partial_ms[0] is None:
                    first_partial_ms[0] = (time.perf_counter() - start_time) * 1000
                    first_partial_text[0] = asr_result.text

        speech_ended = was_speaking and not is_speaking
        if speech_ended or utterances:
            final_result = asr.finalize(language=source_lang)
            if final_result and final_result.text:
                handle_final(final_result.text, final_result.language)
            asr.reset()

        offset += chunk_samples

    # Finalize trailing speech at stream end.
    if vad._is_speaking:
        final_result = asr.finalize(language=source_lang)
        if final_result and final_result.text:
            handle_final(final_result.text, final_result.language)

    return {
        "audio_duration_ms": round(total_samples / sample_rate * 1000, 1),
        "first_vad_speech_ms": round(first_vad_speech_ms[0], 1) if first_vad_speech_ms[0] else None,
        "first_partial_ms": round(first_partial_ms[0], 1) if first_partial_ms[0] else None,
        "first_partial_text": first_partial_text[0],
        "first_final_ms": round(first_final_ms[0], 1) if first_final_ms[0] else None,
        "first_final_text": first_final_text[0],
        "first_translation_ms": round(first_translation_ms[0], 1) if first_translation_ms[0] else None,
        "first_translation_text": first_translation_text[0],
        "partial_count": partial_count,
        "final_count": final_count,
        "engine": translator._engine_name,
    }


def main():
    parser = argparse.ArgumentParser(description="shadow_fiend E2E latency test")
    parser.add_argument("--audio", required=True, help="Path to 16kHz mono WAV")
    parser.add_argument("--source", default="ja", help="Source language")
    parser.add_argument("--target", default="zh", help="Target language")
    parser.add_argument("--asr-device", default="auto", help="ASR/VAD device")
    parser.add_argument("--chunk-duration-ms", type=int, default=40)
    parser.add_argument("--asr-window-ms", type=int, default=500)
    parser.add_argument("--asr-hop-ms", type=int, default=200)
    parser.add_argument("--vad-threshold", type=float, default=0.4)
    parser.add_argument("--vad-min-speech-ms", type=int, default=150)
    parser.add_argument("--vad-min-silence-ms", type=int, default=200)
    parser.add_argument("--no-warmup", action="store_true", help="Skip ASR warmup")
    args = parser.parse_args()

    audio, sr = load_audio(args.audio)
    result = simulate_streaming(
        audio,
        sr,
        args.source,
        args.target,
        chunk_duration_ms=args.chunk_duration_ms,
        asr_window_ms=args.asr_window_ms,
        asr_hop_ms=args.asr_hop_ms,
        vad_threshold=args.vad_threshold,
        vad_min_speech_ms=args.vad_min_speech_ms,
        vad_min_silence_ms=args.vad_min_silence_ms,
        asr_device=args.asr_device,
        warmup=not args.no_warmup,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
