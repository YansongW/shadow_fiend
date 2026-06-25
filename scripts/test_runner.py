#!/usr/bin/env python3
"""
shadow_fiend 一键测试工具。

用法：
    python scripts/test_runner.py setup
    python scripts/test_runner.py test
    python scripts/test_runner.py demo --duration 30
    python scripts/test_runner.py logs
    python scripts/test_runner.py cleanup
    python scripts/test_runner.py all --duration 30

功能：
    - 检测 macOS 环境、Python 版本、Homebrew
    - 自动安装 portaudio / ffmpeg / blackhole-2ch
    - 创建隔离的 .venv-test 虚拟环境
    - 安装依赖并预下载 SenseVoice / Argos 模型
    - 运行单元测试
    - 运行限定秒数的端到端 demo，并自动录屏
    - 打包日志、录屏和环境信息
    - 清理所有测试产物
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

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

DEFAULT_DEMO_DURATION = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def colored(text: str, color: str) -> str:
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
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
    cmd: list,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
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


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def check_python_version():
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        fail(
            f"需要 Python 3.10+，当前为 {version.major}.{version.minor}.{version.micro}\n"
            "请安装 Python 3.10+：brew install python@3.11"
        )
    log(f"Python 版本符合要求：{version.major}.{version.minor}.{version.micro}", "green")


def check_homebrew() -> bool:
    if command_exists("brew"):
        log("Homebrew 已安装", "green")
        return True
    log("Homebrew 未安装", "red")
    log("请访问 https://brew.sh 安装，然后重新运行本脚本", "yellow")
    return False


def check_macos():
    if platform.system() != "Darwin":
        fail("端到端 demo 和自动录屏目前仅支持 macOS")


def blackhole_installed() -> bool:
    return Path("/Library/Audio/Plug-Ins/HAL/BlackHole2ch.driver").exists()


def install_brew_package(pkg: str):
    log(f"安装 {pkg} ...", "yellow")
    result = run(["brew", "install", pkg], timeout=600)
    if result.returncode != 0:
        fail(f"{pkg} 安装失败，请手动运行：brew install {pkg}")
    log(f"{pkg} 安装完成", "green")


def ensure_brew_packages():
    needed = []
    if not command_exists("ffmpeg"):
        needed.append("ffmpeg")
    # portaudio is a library; check via pkg-config or brew list
    try:
        subprocess.run(["pkg-config", "--exists", "portaudio"], check=True)
    except Exception:
        needed.append("portaudio")

    for pkg in needed:
        install_brew_package(pkg)

    if not blackhole_installed():
        log("BlackHole 2ch 未安装，尝试自动安装 ...", "yellow")
        install_brew_package("blackhole-2ch")
        if not blackhole_installed():
            fail("BlackHole 2ch 安装后仍未检测到，请重启或手动安装")
    else:
        log("BlackHole 2ch 已安装", "green")


def prompt_audio_routing():
    log("=" * 60, "cyan")
    log("音频路由检查", "cyan")
    log("=" * 60, "cyan")
    log("shadow_fiend 需要把播放器声音同时输出到 BlackHole 2ch。", "yellow")
    log("请按以下步骤配置（只需一次）：", "yellow")
    log("1. 打开 Audio MIDI Setup（/Applications/Utilities/Audio MIDI Setup.app）", "yellow")
    log("2. 点击左下角 + → 创建多输出设备", "yellow")
    log("3. 同时勾选你的扬声器/耳机 和 BlackHole 2ch", "yellow")
    log("4. 在系统设置 → 声音 → 输出中，选择这个多输出设备", "yellow")
    log("=" * 60, "cyan")


def detect_default_output_contains_blackhole() -> bool:
    """Try to detect if BlackHole is part of the current default output."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPAudioDataType", "-xml"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        )
        return "BlackHole" in result.stdout
    except Exception:
        return False


def check_screen_recording_permission() -> bool:
    """Check if the terminal has screen recording permission."""
    try:
        result = subprocess.run(
            ["screencapture", "-v", "-t", "mov", "-C", "/dev/null"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        # If it exits quickly without doing anything meaningful, permission may be denied.
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_setup(args: argparse.Namespace):
    log("==> 步骤 1/5：检查环境", "yellow")
    check_python_version()
    check_macos()
    if not check_homebrew():
        fail("Homebrew 是必要依赖")

    log("==> 步骤 2/5：安装系统依赖", "yellow")
    ensure_brew_packages()

    log("==> 步骤 3/5：音频路由提示", "yellow")
    prompt_audio_routing()
    if not detect_default_output_contains_blackhole():
        log("未能确认 BlackHole 已加入当前默认输出", "yellow")
        log("如果你已配置好多输出设备，可继续；否则请先配置", "yellow")
        if not os.environ.get("SHADOW_FIEND_SKIP_CONFIRM"):
            try:
                input("已配置好？按回车继续，或 Ctrl+C 退出：")
            except KeyboardInterrupt:
                print()
                sys.exit(0)
    else:
        log("检测到当前输出包含 BlackHole", "green")

    log("==> 步骤 4/5：创建隔离虚拟环境 .venv-test", "yellow")
    if VENV_DIR.exists():
        log(".venv-test 已存在，跳过创建")
    else:
        run([sys.executable, "-m", "venv", str(VENV_DIR)])
        log("虚拟环境创建完成", "green")

    log("==> 步骤 5/5：安装 Python 依赖", "yellow")
    pip = get_venv_pip()
    run([str(pip), "install", "--upgrade", "pip"], timeout=120)
    run([str(pip), "install", "-r", "requirements.txt"], timeout=600)
    log("依赖安装完成", "green")

    log("==> 预下载模型", "yellow")
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
    duration = args.duration or DEFAULT_DEMO_DURATION
    log(f"==> 运行端到端 demo（{duration} 秒后自动退出）", "yellow")
    if not VENV_DIR.exists():
        fail("虚拟环境不存在，请先运行：python scripts/test_runner.py setup")

    if platform.system() != "Darwin":
        fail("端到端 demo 目前仅支持 macOS")

    recording_path = ensure_logs_dir() / f"demo_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mov"
    log(f"录屏文件：{recording_path}", "cyan")
    log("第一次录屏需要授权屏幕录制权限，请按系统提示操作", "yellow")

    # Start screen recording.
    screen_recorder = subprocess.Popen(
        ["screencapture", "-v", "-t", "mov", "-C", str(recording_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Give screencapture a moment to initialize.
    time.sleep(2)

    if screen_recorder.poll() is not None:
        _, stderr = screen_recorder.communicate()
        fail(f"录屏启动失败：{stderr or '未知错误'}，请检查屏幕录制权限")

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
        demo_process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            env={**os.environ, **env},
            stdout=fh,
            stderr=subprocess.STDOUT,
        )

        try:
            demo_process.wait(timeout=duration + 30)
        except subprocess.TimeoutExpired:
            log("demo 未能在预期时间内结束，强制终止", "yellow")
            demo_process.terminate()
            try:
                demo_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                demo_process.kill()

    # Stop recording.
    log("停止录屏...", "blue")
    screen_recorder.terminate()
    try:
        screen_recorder.wait(timeout=10)
    except subprocess.TimeoutExpired:
        screen_recorder.kill()

    if recording_path.exists() and recording_path.stat().st_size > 0:
        log(f"录屏已保存：{recording_path}", "green")
    else:
        log("警告：录屏文件为空或不存在，可能需要屏幕录制权限", "yellow")

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

    # Copy logs (including screen recordings)
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

    setup_parser = subparsers.add_parser("setup", help="检测环境并安装依赖")
    setup_parser.add_argument("--yes", action="store_true", help="跳过音频路由确认提示")

    test_parser = subparsers.add_parser("test", help="运行单元测试")
    test_parser.add_argument("--headless", action="store_true", help="跳过 GUI/音频测试")

    demo_parser = subparsers.add_parser("demo", help="运行端到端 demo 并自动录屏")
    demo_parser.add_argument("--duration", type=int, default=DEFAULT_DEMO_DURATION, help="运行秒数（默认 30）")
    demo_parser.add_argument("--source", default="ja", help="源语言（默认 ja）")
    demo_parser.add_argument("--target", default="zh", help="目标语言（默认 zh）")

    subparsers.add_parser("logs", help="打包测试日志和录屏")
    subparsers.add_parser("cleanup", help="删除测试环境与产物")

    all_parser = subparsers.add_parser("all", help="一键执行 setup→test→demo→logs→cleanup")
    all_parser.add_argument("--duration", type=int, default=DEFAULT_DEMO_DURATION, help="demo 运行秒数（默认 30）")
    all_parser.add_argument("--source", default="ja", help="源语言（默认 ja）")
    all_parser.add_argument("--target", default="zh", help="目标语言（默认 zh）")
    all_parser.add_argument("--no-cleanup", action="store_true", help="保留测试环境")
    all_parser.add_argument("--headless", action="store_true", help="单元测试跳过 GUI/音频")
    all_parser.add_argument("--yes", action="store_true", help="跳过音频路由确认提示")

    args = parser.parse_args()

    if getattr(args, "yes", False):
        os.environ["SHADOW_FIEND_SKIP_CONFIRM"] = "1"

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
