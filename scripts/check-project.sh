#!/usr/bin/env bash
# 检查项目的协作工作流文件是否齐备，校验任务 handoff 的 front-matter，并检查 Git 约定。
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
VALID_PHASE="discover design plan execute verify close"
status=0
warnings=0

problem() {
  echo "问题: $1"
  status=1
}

warn() {
  echo "提醒: $1"
  warnings=$((warnings + 1))
}

in_list() { # <值> <空格分隔的取值列表>
  local v="$1" item
  for item in $2; do
    [ "$v" = "$item" ] && return 0
  done
  return 1
}

# 取 front-matter 字段值
fm_field() {
  awk -v f="$2" '
    NR==1 && $0 ~ /^---[[:space:]]*$/ { infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/ { exit }
    infm && index($0, f ":")==1 { v=$0; sub(/^[^:]*:[[:space:]]*/, "", v); print v; exit }
  ' "$1"
}

# 接受 "YYYY-MM-DD HH:MM" 与 "YYYY-MM-DD"
to_epoch() {
  date -j -f "%Y-%m-%d %H:%M" "$1" +%s 2>/dev/null \
    || date -j -f "%Y-%m-%d" "$1" +%s 2>/dev/null \
    || date -d "$1" +%s 2>/dev/null
}

# 检测"整行就是占位符"的行（可带列表前缀），按文件汇总
check_placeholders() { # <文件>
  local f="$1" n
  [ -f "$f" ] || return 0
  n="$(grep -cE '^[[:space:]]*([-*][[:space:]]+|[0-9]+\.[[:space:]]+)?<[^>]+>[[:space:]]*$' "$f" 2>/dev/null)"
  if [ "${n:-0}" -gt 0 ]; then
    warn "占位符未填 $n 处：$f"
  fi
}

# ---------- Git 仓库检测（后面的任务校验会用到） ----------
IS_GIT=no
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  IS_GIT=yes
fi

# ---------- 路径映射（AGENTS.md front-matter，缺省用默认值） ----------
WFR="$(fm_field AGENTS.md workflow_root)"
[ -n "$WFR" ] || WFR=".agent"

# ---------- 1) 必需项 ----------
missing=()
for item in AGENTS.md "$WFR" "$WFR/work/active"; do
  [ -e "$item" ] || missing+=("$item")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "缺少必需项:"
  for m in "${missing[@]}"; do
    echo "  - $m"
  done
  status=1
fi

# ---------- 2) AGENTS.md 与项目级文档 ----------
if [ -f AGENTS.md ] && ! grep -q "handoff" AGENTS.md; then
  problem "AGENTS.md 未提到 handoff —— 可能缺了「开工读 / 收工写」的铁律"
fi
check_placeholders AGENTS.md
check_placeholders README.md

# ---------- 3) 任务目录 ----------
check_task() { # <任务目录> <yes|no 是否检查停滞>
  local d="$1" want_stale="$2" name h t st ph up ep ow f now age
  name="$(basename "$d")"
  h="${d}handoff.md"

  if [ ! -f "$h" ]; then
    problem "$d 缺少 handoff.md"
    return 0
  fi

  t="$(fm_field "$h" task)"
  if [ -z "$t" ]; then
    problem "$h 缺少 front-matter 的 task"
  elif [ "$t" != "$name" ]; then
    problem "$h 的 task（$t）与目录名（$name）不一致"
  fi

  st="$(fm_field "$h" status)"
  if [ -z "$st" ]; then
    problem "$h 缺少 front-matter 的 status"
  elif ! in_list "$st" "$VALID_STATUS"; then
    problem "$h 的 status 非法: $st"
  fi

  ph="$(fm_field "$h" phase)"
  if [ -z "$ph" ]; then
    problem "$h 缺少 front-matter 的 phase"
  elif ! in_list "$ph" "$VALID_PHASE"; then
    problem "$h 的 phase 非法: $ph"
  fi

  up="$(fm_field "$h" updated)"
  if [ -z "$up" ]; then
    problem "$h 缺少 front-matter 的 updated"
  else
    ep="$(to_epoch "$up")"
    if [ -z "$ep" ]; then
      problem "$h 的 updated 格式不对（应为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM）: $up"
    elif [ "$want_stale" = "yes" ]; then
      now="$(date +%s)"
      age=$(( (now - ep) / 86400 ))
      if [ "$age" -gt "$STALE_DAYS" ]; then
        warn "停滞 $d 已 $age 天未更新（阈值 $STALE_DAYS 天）"
      fi
    fi
  fi

  ow="$(fm_field "$h" owner)"
  case "$ow" in
    *"<"*) warn "负责人未填 $h" ;;
  esac

  br="$(fm_field "$h" branch)"
  case "$br" in
    ""|"<"*|none|main|master)
      : ;;
    *)
      if [ "$IS_GIT" = yes ] && ! git show-ref --verify --quiet "refs/heads/$br"; then
        warn "$h 的 branch（$br）在本地找不到对应分支（可能已合并删除）"
      fi
      ;;
  esac

  for f in brief.md analysis.md plan.md validation.md handoff.md; do
    check_placeholders "${d}${f}"
  done
}

if [ -d "$WFR/work/active" ]; then
  shopt -s nullglob
  for d in "$WFR"/work/active/*/; do
    case "$(basename "$d")" in
      scratch) continue ;;
    esac
    check_task "$d" yes
  done
  shopt -u nullglob
fi

# ---------- 4) 归档任务 ----------
if [ -d "$WFR/work/archive" ]; then
  shopt -s nullglob
  for d in "$WFR"/work/archive/*/; do
    [ -f "${d}handoff.md" ] || problem "$d 缺少 handoff.md"
  done
  shopt -u nullglob
fi

# ---------- 5) Git 约定 ----------
if [ "$IS_GIT" = yes ]; then
  if ! git check-ignore -q -- "$WFR" 2>/dev/null; then
    warn "工作流目录 $WFR 未被 .gitignore 排除——多人协作时它会跟着代码一起被提交"
  fi

  subject="$(git log -1 --pretty=%s 2>/dev/null || true)"
  if [ -n "$subject" ] && ! grep -qE '^([a-z]+\([^)]+\)|[0-9]+\.[0-9]+\.[0-9]+): .+' <<<"$subject"; then
    warn "最近一次提交信息不符合约定格式（应为 <type>(<任务目录名>): <说明>，或版本提交 <版本>: <说明>）: $subject"
  fi
else
  warn "不在 Git 仓库中：协议降级为「仅本地」，跨机器 / 跨 Agent 恢复与历史追溯都会失效"
fi

if [ "$status" -eq 0 ]; then
  if [ "$warnings" -gt 0 ]; then
    echo "检查通过（另有 $warnings 条提醒）。"
  else
    echo "检查通过。"
  fi
fi
exit "$status"
