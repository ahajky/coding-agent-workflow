#!/usr/bin/env bash
# 检查项目的协作工作流文件是否齐备。
# 用法: check-project.sh [项目根目录]
# 退出码: 0 = 通过, 1 = 有缺失
set -uo pipefail

ROOT="${1:-.}"
if [ ! -d "$ROOT" ]; then
  echo "错误: 目录不存在: $ROOT" >&2
  exit 2
fi
cd "$ROOT"

status=0
missing=()

for item in AGENTS.md docs work work/active; do
  if [ ! -e "$item" ]; then
    missing+=("$item")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo "缺少必需项:"
  for m in "${missing[@]}"; do
    echo "  - $m"
  done
  status=1
fi

if [ -d work/active ]; then
  shopt -s nullglob
  for d in work/active/*/; do
    if [ ! -f "${d}handoff.md" ]; then
      echo "任务缺少 handoff.md: $d"
      status=1
    fi
  done
  shopt -u nullglob
fi

if [ "$status" -eq 0 ]; then
  echo "检查通过。"
fi

exit "$status"
