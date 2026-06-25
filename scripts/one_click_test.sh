#!/usr/bin/env bash
# shadow_fiend 一键测试入口
# 用法：./scripts/one_click_test.sh [选项]
# 默认执行 setup → test → demo → logs → cleanup

set -euo pipefail

cd "$(dirname "$0")/.."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

info "shadow_fiend 一键测试启动"

# Check python3
if ! command -v python3 &> /dev/null; then
    error "未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
info "检测到 Python: $PY_VERSION"

# Parse args
ARGS=()
NO_CLEANUP=false
for arg in "$@"; do
    case "$arg" in
        --no-cleanup) NO_CLEANUP=true ;;
        *) ARGS+=("$arg") ;;
    esac
done

# Build test_runner args
RUNNER_ARGS=("all" "--duration" "60")
if [ "$NO_CLEANUP" = true ]; then
    RUNNER_ARGS+=("--no-cleanup")
fi
RUNNER_ARGS+=("${ARGS[@]}")

info "执行：python3 scripts/test_runner.py ${RUNNER_ARGS[*]}"

if python3 scripts/test_runner.py "${RUNNER_ARGS[@]}"; then
    ok "一键测试完成"
else
    error "一键测试失败"
    info "日志目录：$(pwd)/logs"
    info "如需保留环境排查，可运行：./scripts/one_click_test.sh --no-cleanup"
    exit 1
fi
