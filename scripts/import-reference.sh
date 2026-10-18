#!/usr/bin/env bash
# 把外部参考资料复制进工作流目录，并在索引里登记来源。
# 拷贝的是"工作副本"：原件仍是权威，不要在这里改写原文。
# 用法: import-reference.sh <来源路径> [--name 名称] [--note 用途] [--root 项目根]
set -euo pipefail

SRC=""
NAME=""
NOTE="—"
ROOT="."

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "用法: import-reference.sh <来源路径> [--name 名称] [--note 用途] [--root 项目根]"
      echo ""
      echo "  --name   在工作流 references/ 下的目录名（默认取来源的目录名）"
      echo "  --note   用途，一句话，写进索引"
      exit 0
      ;;
    --name)
      NAME="${2:-}"; shift 2
      ;;
    --note)
      NOTE="${2:-}"; shift 2
      ;;
    --root)
      ROOT="${2:-}"; shift 2
      ;;
    --*)
      echo "未知参数: $1" >&2; exit 2
      ;;
    *)
      SRC="$1"; shift
      ;;
  esac
done

if [ -z "$SRC" ]; then
  echo "用法: import-reference.sh <来源路径> [--name 名称] [--note 用途] [--root 项目根]" >&2
  exit 2
fi

if [ ! -e "$SRC" ]; then
  echo "错误: 来源不存在: $SRC" >&2
  exit 1
fi

# 从 AGENTS.md 读工作流根目录，缺省 .agent
WFR=""
if [ -f "$ROOT/AGENTS.md" ]; then
  WFR="$(awk '
    NR==1 && $0 ~ /^---[[:space:]]*$/ { infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/ { exit }
    infm && index($0, "workflow_root:")==1 { v=$0; sub(/^[^:]*:[[:space:]]*/, "", v); print v; exit }
  ' "$ROOT/AGENTS.md")"
fi
[ -n "$WFR" ] || WFR=".agent"

REF_DIR="$ROOT/$WFR/references"
[ -n "$NAME" ] || NAME="$(basename "$SRC")"
DEST="$REF_DIR/$NAME"

if [ -e "$DEST" ]; then
  echo "错误: 目标已存在，不覆盖: $DEST" >&2
  echo "换个 --name，或先手动处理旧副本。" >&2
  exit 1
fi

SIZE="$(du -sh "$SRC" 2>/dev/null | awk '{print $1}')"
echo "来源: $SRC（${SIZE:-未知}）"
echo "目标: $DEST"

mkdir -p "$REF_DIR"
if [ -d "$SRC" ]; then
  if command -v rsync >/dev/null 2>&1; then
    mkdir -p "$DEST"
    rsync -a --exclude '.git' "$SRC/" "$DEST/"
  else
    cp -R "$SRC" "$DEST"
    if [ -d "$DEST/.git" ]; then
      echo "提醒: 来源里带有 .git，已一并复制；如不需要请手动删除 $DEST/.git" >&2
    fi
  fi
else
  cp "$SRC" "$DEST"
fi

# 索引：记录来源、时间、用途，方便日后核对原件是否更新
idx="$REF_DIR/README.md"
if [ ! -f "$idx" ]; then
  {
    echo "# 外部参考资料索引"
    echo ""
    echo "> 这里放的是**工作副本**：原件仍是权威，引用结论以原件为准。"
    echo "> 不要改写这里的原文；原件更新后重新导入，并在下表的「导入时间」上体现。"
    echo ""
    echo "| 名称 | 来源 | 导入时间 | 用途 |"
    echo "| --- | --- | --- | --- |"
  } > "$idx"
fi
printf '| `%s` | `%s` | %s | %s |\n' "$NAME" "$SRC" "$(date '+%Y-%m-%d')" "$NOTE" >> "$idx"

echo "已导入，索引已更新: $idx"
echo "提醒: 这是工作副本。原件变了要重新导入；体积大的材料确认只拷了用得上的部分。"
