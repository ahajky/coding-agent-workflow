#!/usr/bin/env bash
# 初始化一个任务工作区（从 templates/ 复制模板）。
# 用法: init-task.sh <任务目录> [--title 标题] [--minimal]
#   --minimal  只创建 handoff.md（适用于很小改动）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

TASK_DIR=""
TITLE=""
MINIMAL=0

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "用法: init-task.sh <任务目录> [--title 标题] [--minimal]"
      exit 0
      ;;
    --title)
      TITLE="${2:-}"; shift 2
      ;;
    --minimal)
      MINIMAL=1; shift
      ;;
    --*)
      echo "未知参数: $1" >&2; exit 2
      ;;
    *)
      TASK_DIR="$1"; shift
      ;;
  esac
done

if [ -z "$TASK_DIR" ]; then
  echo "用法: init-task.sh <任务目录> [--title 标题] [--minimal]" >&2
  exit 2
fi

if [ -e "$TASK_DIR" ]; then
  echo "错误: $TASK_DIR 已存在，不覆盖。" >&2
  exit 1
fi

mkdir -p "$TASK_DIR"

render() {
  local tpl="$TEMPLATES_DIR/$1" out="$TASK_DIR/$2"
  if [ ! -f "$tpl" ]; then
    echo "缺少模板: $tpl" >&2
    return 1
  fi
  if [ -n "$TITLE" ]; then
    sed "s/<任务标题>/$TITLE/g" "$tpl" > "$out"
  else
    cp "$tpl" "$out"
  fi
}

render handoff.md handoff.md
if [ "$MINIMAL" -eq 0 ]; then
  render brief.md brief.md
  render plan.md plan.md
  render validation.md validation.md
fi

# 自动填入 handoff 的 front-matter：任务名与当前时刻
TASK_NAME="$(basename "$TASK_DIR")"
NOW="$(date '+%Y-%m-%d %H:%M')"
HANDOFF="$TASK_DIR/handoff.md"
if [ -f "$HANDOFF" ]; then
  if sed --version >/dev/null 2>&1; then
    sed -i "s|<任务目录名>|$TASK_NAME|g; s|<YYYY-MM-DD HH:MM>|$NOW|g" "$HANDOFF"
  else
    sed -i '' "s|<任务目录名>|$TASK_NAME|g; s|<YYYY-MM-DD HH:MM>|$NOW|g" "$HANDOFF"
  fi
fi

echo "已创建任务工作区: $TASK_DIR"
ls -1 "$TASK_DIR"
