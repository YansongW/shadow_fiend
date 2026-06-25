"""
shadow_fiend v0.0.2 端到端延迟批量测试。

对日/韩合成测试集各运行 e2e_latency_test，汇总统计并输出 JSON 报告。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import e2e_latency_test  # noqa: F401


def find_audio_files(root: Path, limit: int = 10) -> list[Path]:
    files = sorted(root.glob("*.wav"))
    return files[:limit]


def run_one(audio: Path, source: str, target: str = "zh") -> dict:
    cmd = [
        sys.executable,
        "tests/e2e_latency_test.py",
        "--audio", str(audio),
        "--source", source,
        "--target", target,
        "--asr-device", "mps",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"E2E test failed for {audio}")
    # Extract the JSON block (first '{' to last '}').
    start = result.stdout.find("{")
    end = result.stdout.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"No JSON found in E2E output for {audio}")
    return json.loads(result.stdout[start:end + 1])


def main():
    base = Path(__file__).parent / "asr_benchmark" / "synthetic"
    report: dict = {"ja": [], "ko": []}

    for lang in ("ja", "ko"):
        files = find_audio_files(base / lang / "audio", limit=10)
        for f in files:
            print(f"Testing {f.name}...")
            report[lang].append({
                "file": f.name,
                "result": run_one(f, lang),
            })

    # Summarize
    for lang in ("ja", "ko"):
        items = [r["result"] for r in report[lang]]
        for key in ["first_vad_speech_ms", "first_partial_ms", "first_final_ms"]:
            vals = [r[key] for r in items if r.get(key) is not None]
            report[f"{lang}_{key}_avg"] = round(sum(vals) / len(vals), 1) if vals else None

    out = Path(__file__).parent / "asr_benchmark" / "results" / "e2e_latency_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
