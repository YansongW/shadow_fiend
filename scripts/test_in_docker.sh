#!/usr/bin/env bash
# shadow_fiend Docker 测试入口
# 用法：./scripts/test_in_docker.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> 构建并运行 Docker 单元测试"
docker compose -f docker-compose.test.yml up --build --remove-orphans

echo "==> Docker 测试完成"
