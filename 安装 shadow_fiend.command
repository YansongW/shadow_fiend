#!/usr/bin/env bash
# 双击运行以安装 shadow_fiend 依赖环境。
# 需要预先安装 Homebrew 并配置好 BlackHole 2ch。

cd "$(dirname "$0")"
./scripts/setup.sh

echo ""
echo "按回车键关闭窗口..."
read -r
