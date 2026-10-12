#!/usr/bin/env bash
# 检查项目的协作工作流文件是否齐备，并校验每个活跃任务 handoff 的 front-matter。
# 用法: check-project.sh [项目根目录]
# 环境变量: STALE_DAYS（默认 30）——超过多少天未更新视为停滞
# 退出码: 0 = 通过, 1 = 有问题
set -uo pipefail

ROOT="${1:-.}"
if [ ! -d "$ROOT" ]; then
  echo "错误: 目录不存在: $ROOT" >&2
  exit 2
fi
cd "$ROOT"

STALE_DAYS="${STALE_DAYS:-30}"
VALID_STATUS="planned in_progress blocked in_review done abandoned"
status=0
warnings=0

problem() {
  echo "问题: $1"
  status=1
}

# 1) 必需项
missing=()
for item in AGENTS.md docs work work/active; do
  [ -e "$item" ] || missing+=("$item")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "缺少必需项:"
  for m in "${missing[@]}"; do
    echo "  - $m"
  done
  status=1
fi

# 2) AGENTS.md 是否写了铁律（粗查 handoff 关键词）
if [ -f AGENTS.md ] && ! grep -q "handoff" AGENTS.md; then
  problem "AGENTS.md 未提到 handoff —— 可能缺了「开工读 / 收工写」的铁律"
fi

# front-matter 取字段
fm_field() {
  awk -v f="$2" '
    NR==1 && $0 ~ /^---[[:space:]]*$/ { infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/ { exit }
    infm && index($0, f ":")==1 { v=$0; sub(/^[^:]*:[[:space:]]*/, "", v); print v; exit }
  ' "$1"
}

to_epoch() {
  date -j -f "%Y-%m-%d" "$1" +%s 2>/dev/null || date -d "$1" +%s 2>/dev/null
}

# 3) 每个活跃任务
if [ -d work/active ]; then
  shopt -s nullglob
  for d in work/active/*/; do
    case "$(basename "$d")" in
      scratch) continue ;;
    esac

    h="${d}handoff.md"
    if [ ! -f "$h" ]; then
      problem "$d 缺少 handoff.md"
      continue
    fi

    st="$(fm_field "$h" status)"
    if [ -z "$st" ]; then
      problem "$h 缺少 front-matter 的 status"
    else
      ok=0
      for s in $VALID_STATUS; do
        [ "$st" = "$s" ] && ok=1
      done
      [ "$ok" -eq 1 ] || problem "$h 的 status 非法: $st"
    fi

    up="$(fm_field "$h" updated)"
    if [ -z "$up" ]; then
      problem "$h 缺少 front-matter 的 updated"
    else
      ep="$(to_epoch "$up")"
      if [ -z "$ep" ]; then
        problem "$h 的 updated 不是 YYYY-MM-DD: $up"
      else
        now="$(date +%s)"
        age=$(( (now - ep) / 86400 ))
        if [ "$age" -gt "$STALE_DAYS" ]; then
          echo "提醒（停滞）: $d 已 $age 天未更新（阈值 $STALE_DAYS 天）"
          warnings=$((warnings + 1))
        fi
      fi
    fi
  done
  shopt -u nullglob
fi

if [ "$status" -eq 0 ]; then
  if [ "$warnings" -gt 0 ]; then
    echo "检查通过（另有 $warnings 条提醒）。"
  else
    echo "检查通过。"
  fi
fi
exit "$status"
