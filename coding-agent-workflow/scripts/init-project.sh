#!/usr/bin/env bash
# 为一个项目接入协作工作流：生成 AGENTS.md、README.md 与目录骨架。
# 已存在的文件不会被覆盖。
# 用法: init-project.sh [项目根目录] [--name 项目名]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

ROOT="."
NAME=""

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "用法: init-project.sh [项目根目录] [--name 项目名]"
      exit 0
      ;;
    --name)
      NAME="${2:-}"; shift 2
      ;;
    --*)
      echo "未知参数: $1" >&2; exit 2
      ;;
    *)
      ROOT="$1"; shift
      ;;
  esac
done

if [ ! -d "$ROOT" ]; then
  echo "错误: 目录不存在: $ROOT" >&2
  exit 2
fi

created=0
skipped=0

place() { # <模板名> <目标相对路径>
  local tpl="$TEMPLATES_DIR/$1" out="$ROOT/$2"
  if [ ! -f "$tpl" ]; then
    echo "缺少模板: $tpl" >&2
    exit 1
  fi
  if [ -e "$out" ]; then
    echo "跳过（已存在）: $2"
    skipped=$((skipped + 1))
    return 0
  fi
  mkdir -p "$(dirname "$out")"
  if [ -n "$NAME" ]; then
    sed "s/<项目名>/$NAME/g" "$tpl" > "$out"
  else
    cp "$tpl" "$out"
  fi
  echo "创建: $2"
  created=$((created + 1))
}

for d in docs/product docs/architecture docs/decisions docs/guides work/active work/archive; do
  mkdir -p "$ROOT/$d"
done

place AGENTS.md AGENTS.md
place README.md README.md

# 若有 .gitignore 且尚未忽略原始日志，则补上
gi="$ROOT/.gitignore"
if [ -f "$gi" ] && ! grep -q "coding-agent-workflow" "$gi" 2>/dev/null; then
  {
    echo ""
    echo "# coding-agent-workflow：原始日志与临时文件不入库"
    echo "work/active/*/scratch/"
    echo "*.log"
    echo "*.tmp"
  } >> "$gi"
  echo "更新: .gitignore"
fi

echo "已创建 $created 个文件，跳过 $skipped 个已存在文件。"
echo "目录骨架: docs/{product,architecture,decisions,guides}, work/{active,archive}"
