#!/usr/bin/env bash
# 双击运行以启动 shadow_fiend 实时字幕翻译。
# 默认：日语 -> 中文，可在下方修改 SOURCE/TARGET。

cd "$(dirname "$0")"

SOURCE="ja"
TARGET="zh"

echo "启动 shadow_fiend: $SOURCE -> $TARGET"
./scripts/run.sh --source "$SOURCE" --target "$TARGET"
