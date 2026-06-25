#!/usr/bin/env python3
"""
shadow_fiend 一键测试工具。

用法：
    python scripts/test_runner.py setup
    python scripts/test_runner.py test
    python scripts/test_runner.py demo --duration 60
    python scripts/test_runner.py logs
    python scripts/test_runner.py cleanup
    python scripts/test_runner.py all --duration 60

功能：
    - 创建隔离的 .venv-test 虚拟环境
    - 安装依赖并预下载 SenseVoice / Argos 模型
    - 运行单元测试
    - 运行限定秒数的端到端 demo
    - 打包日志和环境信息
    - 清理所有测试产物
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = PROJECT_ROOT / ".venv-test"
LOGS_DIR = PROJECT_ROOT / "logs"
CACHE_DIR = Path.home() / ".cache" / "shadow_fiend-test"
REPORTS_DIR = PROJECT_ROOT / "test-reports"

# Environment variables to keep all model caches under CACHE_DIR
CACHE_ENV = {
    "HF_HOME": str(CACHE_DIR / "huggingface"),
    "MODELSCOPE_CACHE": str(CACHE_DIR / "modelscope"),
    "ARGOS_TRANSLATE_DATA_DIR": str(CACHE_DIR / "argos-translate"),
    "TRANSFORMERS_CACHE": str(CACHE_DIR / "transformers"),
    "TORCH_HOME": str(CACHE_DIR / "torch"),
}

SENSEVOICE_MODEL = "iic/SenseVoiceSmall"
ARGOS_PAIRS = [
    ("en", "zh"),
    ("zh", "en"),
    ("en", "ja"),
    ("ja", "en"),
    ("en", "ko"),
    ("ko", "en"),
]

# Tests to skip in headless / Docker mode
HEADLESS_SKIPS = ["test_ui.py", "test_audio_capture.py"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def colored(text: str, color: str) -> str:
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "reset": "\033[0m",
    }
    if os.environ.get("NO_COLOR"):
        return text
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def log(message: str, color: str = "blue"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {colored(message, color)}")


def fail(message: str, exit_code: int = 1):
    log(message, "red")
    log(f"日志目录：{LOGS_DIR}", "yellow")
    sys.exit(exit_code)


def ensure_logs_dir() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def get_venv_python() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_venv_pip() -> Path:
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def run(
    cmd: list[str],
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    merged_env.update(CACHE_ENV)
    if env:
        merged_env.update(env)

    working_dir = cwd or PROJECT_ROOT
    log_file = ensure_logs_dir() / f"cmd_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log"

    log(f"Run: {' '.join(cmd)}", "blue")
    if capture:
        with open(log_file, "a", encoding="utf-8") as fh:
            fh.write(f"# {' '.join(cmd)}\n")
            fh.write(f"# cwd: {working_dir}\n\n")
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                env=merged_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
            )
            fh.write(result.stdout or "")
        return result
    else:
        return subprocess.run(
            cmd,
            cwd=working_dir,
            env=merged_env,
            timeout=timeout,
        )


def check_python_version():
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        fail(f"需要 Python 3.10+，当前为 {version.major}.{version.minor}.{version.micro}")
    log(f"Python 版本符合要求：{version.major}.{version.minor}.{version.micro}", "green")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_setup(args: argparse.Namespace):
    log("==> 步骤 1/4：检查环境", "yellow")
    check_python_version()

    if platform.system() != "Darwin":
        log("警告：非 macOS 系统，端到端 demo 可能无法运行音频捕获", "yellow")

    log("==> 步骤 2/4：创建隔离虚拟环境 .venv-test", "yellow")
    if VENV_DIR.exists():
        log(".venv-test 已存在，跳过创建")
    else:
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
        log("虚拟环境创建完成", "green")

    log("==> 步骤 3/4：安装 Python 依赖", "yellow")
    pip = get_venv_pip()
    run([str(pip), "install", "--upgrade", "pip"], timeout=120)
    run([str(pip), "install", "-r", "requirements.txt"], timeout=600)
    log("依赖安装完成", "green")

    log("==> 步骤 4/4：预下载模型", "yellow")
    _download_models()
    log("模型预下载完成", "green")

    log("==> setup 完成", "green")


def _download_models():
    python = get_venv_python()

    # Pre-download SenseVoice model
    sensevoice_script = PROJECT_ROOT / "scripts" / "_download_sensevoice.py"
    sensevoice_script.write_text(
        f"""
import os
os.environ.setdefault("HF_HOME", "{CACHE_ENV['HF_HOME']}")
os.environ.setdefault("MODELSCOPE_CACHE", "{CACHE_ENV['MODELSCOPE_CACHE']}")
os.environ.setdefault("TRANSFORMERS_CACHE", "{CACHE_ENV['TRANSFORMERS_CACHE']}")
os.environ.setdefault("TORCH_HOME", "{CACHE_ENV['TORCH_HOME']}")

from funasr import AutoModel
print("Downloading SenseVoice model...")
model = AutoModel(
    model="{SENSEVOICE_MODEL}",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    device="cpu",
)
print("SenseVoice model downloaded.")
""".strip(),
        encoding="utf-8",
    )
    result = run([str(python), str(sensevoice_script)], timeout=1800)
    if result.returncode != 0:
        fail("SenseVoice 模型下载失败")

    # Pre-download Argos language packages
    argos_script = PROJECT_ROOT / "scripts" / "_download_argos.py"
    pairs_json = json.dumps(ARGOS_PAIRS)
    argos_script.write_text(
        f"""
import os
os.environ.setdefault("ARGOS_TRANSLATE_DATA_DIR", "{CACHE_ENV['ARGOS_TRANSLATE_DATA_DIR']}")

import argostranslate.package
import argostranslate.translate

pairs = {pairs_json}
installed = {{(p.from_code, p.to_code) for p in argostranslate.package.get_installed_packages()}}
for from_code, to_code in pairs:
    if (from_code, to_code) in installed:
        print(f"Argos package {{from_code}}->{{to_code}} already installed")
        continue
    print(f"Installing Argos package {{from_code}}->{{to_code}}...")
    available = argostranslate.package.get_available_packages()
    pkg = next((p for p in available if p.from_code == from_code and p.to_code == to_code), None)
    if pkg is None:
        raise RuntimeError(f"Argos package {{from_code}}->{{to_code}} not available")
    argostranslate.package.install_from_path(pkg.download())
    print(f"Installed {{from_code}}->{{to_code}}")
print("Argos packages ready.")
""".strip(),
        encoding="utf-8",
    )
    result = run([str(python), str(argos_script)], timeout=1200)
    if result.returncode != 0:
        fail("Argos 语言包下载失败")


def cmd_test(args: argparse.Namespace):
    log("==> 运行单元测试", "yellow")
    if not VENV_DIR.exists():
        fail("虚拟环境不存在，请先运行：python scripts/test_runner.py setup")

    python = get_venv_python()
    cmd = [str(python), "-m", "pytest", "tests/", "-v"]

    if args.headless:
        log("headless 模式：跳过 GUI/音频相关测试", "yellow")
        for skip in HEADLESS_SKIPS:
            cmd.extend(["--ignore", f"tests/{skip}"])

    result = run(cmd, timeout=600)
    if result.returncode != 0:
        fail("单元测试未通过")
    log("单元测试通过", "green")


def cmd_demo(args: argparse.Namespace):
    duration = args.duration or 60
    log(f"==> 运行端到端 demo（{duration} 秒后自动退出）", "yellow")
    if not VENV_DIR.exists():
        fail("虚拟环境不存在，请先运行：python scripts/test_runner.py setup")

    python = get_venv_python()
    cmd = [
        str(python),
        "-m",
        "src.main",
        "--source",
        args.source or "ja",
        "--target",
        args.target or "zh",
        "--duration",
        str(duration),
    ]

    log_file = ensure_logs_dir() / f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log(f"demo 日志：{log_file}", "blue")

    env = dict(CACHE_ENV)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

    with open(log_file, "w", encoding="utf-8") as fh:
        fh.write(f"# demo {' '.join(cmd)}\n\n")
        process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            env={**os.environ, **env},
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
        try:
            process.wait(timeout=duration + 30)
        except subprocess.TimeoutExpired:
            log("demo 未能在预期时间内结束，强制终止", "yellow")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

    log("demo 结束", "green")


def cmd_logs(args: argparse.Namespace):
    log("==> 收集日志并生成报告", "yellow")
    ensure_logs_dir().mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"shadow_fiend-test-report-{timestamp}"
    report_dir = REPORTS_DIR / report_name
    report_dir.mkdir(parents=True, exist_ok=True)

    # Environment info
    env_info = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "timestamp": timestamp,
    }
    (report_dir / "env_info.json").write_text(json.dumps(env_info, indent=2), encoding="utf-8")

    # pip list
    if VENV_DIR.exists():
        pip = get_venv_pip()
        result = run([str(pip), "list"], capture=True)
        (report_dir / "pip_list.txt").write_text(result.stdout or "", encoding="utf-8")

    # Copy logs
    logs_dest = report_dir / "logs"
    if LOGS_DIR.exists() and any(LOGS_DIR.iterdir()):
        shutil.copytree(LOGS_DIR, logs_dest)

    # Cache manifest
    cache_manifest = []
    if CACHE_DIR.exists():
        for root, dirs, files in os.walk(CACHE_DIR):
            for f in files:
                cache_manifest.append(os.path.relpath(os.path.join(root, f), CACHE_DIR))
    (report_dir / "cache_manifest.txt").write_text("\n".join(sorted(cache_manifest)), encoding="utf-8")

    # Zip it
    zip_path = REPORTS_DIR / f"{report_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(report_dir):
            for f in files:
                full = Path(root) / f
                zf.write(full, arcname=full.relative_to(REPORTS_DIR))

    log(f"报告已生成：{zip_path}", "green")
    return zip_path


def cmd_cleanup(args: argparse.Namespace):
    log("==> 清理测试环境", "yellow")

    targets = [
        (".venv-test", VENV_DIR),
        ("logs", LOGS_DIR),
        ("test-reports", REPORTS_DIR),
        ("cache", CACHE_DIR),
    ]

    for name, path in targets:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            log(f"已删除 {name}: {path}", "blue")

    # Remove temp download scripts
    for script in ["_download_sensevoice.py", "_download_argos.py"]:
        p = PROJECT_ROOT / "scripts" / script
        if p.exists():
            p.unlink()

    log("清理完成", "green")


def cmd_all(args: argparse.Namespace):
    log("==> 一键测试开始", "yellow")
    try:
        cmd_setup(args)
        cmd_test(args)
        cmd_demo(args)
        report = cmd_logs(args)
        log(f"测试报告：{report}", "green")
    finally:
        if not args.no_cleanup:
            cmd_cleanup(args)
        else:
            log("跳过 cleanup（--no-cleanup）", "yellow")
    log("==> 一键测试完成", "green")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        prog="test_runner",
        description="shadow_fiend 一键测试工具",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="创建隔离环境并下载模型")

    test_parser = subparsers.add_parser("test", help="运行单元测试")
    test_parser.add_argument("--headless", action="store_true", help="跳过 GUI/音频测试")

    demo_parser = subparsers.add_parser("demo", help="运行端到端 demo")
    demo_parser.add_argument("--duration", type=int, default=60, help="运行秒数（默认 60）")
    demo_parser.add_argument("--source", default="ja", help="源语言（默认 ja）")
    demo_parser.add_argument("--target", default="zh", help="目标语言（默认 zh）")

    subparsers.add_parser("logs", help="打包测试日志")
    subparsers.add_parser("cleanup", help="删除测试环境与产物")

    all_parser = subparsers.add_parser("all", help="一键执行 setup→test→demo→logs→cleanup")
    all_parser.add_argument("--duration", type=int, default=60, help="demo 运行秒数（默认 60）")
    all_parser.add_argument("--source", default="ja", help="源语言（默认 ja）")
    all_parser.add_argument("--target", default="zh", help="目标语言（默认 zh）")
    all_parser.add_argument("--no-cleanup", action="store_true", help="保留测试环境")
    all_parser.add_argument("--headless", action="store_true", help="单元测试跳过 GUI/音频")

    args = parser.parse_args()

    commands = {
        "setup": cmd_setup,
        "test": cmd_test,
        "demo": cmd_demo,
        "logs": cmd_logs,
        "cleanup": cmd_cleanup,
        "all": cmd_all,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
