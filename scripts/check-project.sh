#!/usr/bin/env bash
# 检查项目的协作工作流文件是否齐备，校验任务 handoff 的 front-matter，并检查 Git 约定。
# 用法: check-project.sh [项目根目录] [--strict]
# 环境变量: STALE_DAYS（默认 30）——超过多少天未更新视为停滞
# 退出码: 0 = 通过, 1 = 有问题
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-.}"
STRICT=no
if [ "${2:-}" = --strict ]; then STRICT=yes; elif [ -n "${2:-}" ]; then echo "未知参数: $2" >&2; exit 2; fi
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
  python3 "$SCRIPT_DIR/workflow_io.py" field "$1" "$2"
}

# 接受 "YYYY-MM-DD HH:MM" 与 "YYYY-MM-DD"
to_epoch() {
  python3 - "$1" <<'PYCODE'
from datetime import datetime
import sys
for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
    try:
        print(int(datetime.strptime(sys.argv[1], fmt).timestamp())); break
    except ValueError:
        pass
else:
    sys.exit(1)
PYCODE
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
WFR="$(fm_field AGENTS.md workflow_root)" || exit 1
[ -n "$WFR" ] || WFR=".agent"
python3 "$SCRIPT_DIR/workflow_io.py" path . "$WFR" || exit 1

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

  for f in brief.md plan.md handoff.md; do
    [ -f "${d}${f}" ] || problem "$d 缺少 $f"
  done
  case "$name" in
    [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-*|[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9]-*) ;;
    *) warn "$d 缺少日期前缀（约定 YYYYMMDD-短语），日后不好按时间排序与去重" ;;
  esac

  if [ ! -f "$h" ]; then
    return 0
  fi

  t="$(fm_field "$h" task)" || { problem "$h 的 front-matter 无效"; return 0; }
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

  if [ "$want_stale" = yes ]; then
    case "$st" in done|abandoned) problem "$h 已结束但仍留在 active，请归档" ;; esac
  else
    case "$st" in done|abandoned) ;; *) problem "$h 归档任务必须是 done 或 abandoned" ;; esac
  fi
  if [ "$st" = done ] && [ "$ph" != close ]; then problem "$h 的 done 必须对应 close 阶段"; fi

  up="$(fm_field "$h" updated)"
  if [ -z "$up" ]; then
    problem "$h 缺少 front-matter 的 updated"
  else
    ep="$(to_epoch "$up")"
    if [ -z "$ep" ]; then
      problem "$h 的 updated 格式不对（应为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM）: $up"
    elif [ "$ep" -gt "$(( $(date +%s) + 300 ))" ]; then
      problem "$h 的 updated 是未来时间"
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
    ""|*"<"*) problem "负责人未填 $h" ;;
  esac

  br="$(fm_field "$h" branch)"
  case "$br" in
    ""|*"<"*) problem "$h 的 branch 未填" ;;
    none|main|master) : ;;
    *)
      if [ "$IS_GIT" = yes ] && [ "$want_stale" = yes ] && [ -z "$(git for-each-ref --format='%(refname)' "refs/heads/$br" "refs/remotes/*/$br")" ]; then
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
    check_task "$d" no
  done
  shopt -u nullglob
fi

# ---------- 5) Git 约定 ----------
if [ "$IS_GIT" = yes ]; then
  tracked="$(GIT_LITERAL_PATHSPECS=1 git ls-files -- "$WFR/")"
  if [ -n "$tracked" ]; then
    if [ "$STRICT" = yes ]; then problem "工作流目录 $WFR 已被 Git 跟踪，请从索引移除个人文件"; else warn "工作流目录 $WFR 已被 Git 跟踪（修改 .gitignore 不会取消跟踪）"; fi
  elif ! git check-ignore -q -- "$WFR/" 2>/dev/null; then
    warn "工作流目录 $WFR 未被 .gitignore 排除"
  fi
  if git ls-files --error-unmatch AGENTS.md >/dev/null 2>&1; then
    shared="$(git show :AGENTS.md | python3 "$SCRIPT_DIR/workflow_io.py" field - workflow_shared_agents)"
    if [ "$STRICT" = yes ] && [ "$shared" != true ]; then
      problem "AGENTS.md 已被跟踪；团队确认共用时设置 workflow_shared_agents: true，否则从索引移除"
    elif [ "$shared" != true ]; then
      warn "AGENTS.md 已被跟踪；团队共享需显式设置 workflow_shared_agents: true"
    fi
  elif ! git check-ignore -q -- AGENTS.md 2>/dev/null; then
    warn "AGENTS.md 未被 .gitignore 排除"
  fi
  # git ls-files 使用本次提交的索引，包含 add -f 的新文件；删除已暂存的文件不再阻止。
  # 消息由 commit-msg 检查，不读取上一次提交。

else
  warn "不在 Git 仓库中：协议降级为「仅本地」，跨机器 / 跨 Agent 恢复与历史追溯都会失效"
fi

# ---------- 6) 外部资料索引 ----------
refd="$WFR/references"
if [ -d "$refd" ] && [ -n "$(ls -A "$refd" 2>/dev/null)" ] && [ ! -f "$refd/README.md" ]; then
  warn "$refd 里有内容但没有 README.md 索引——记下来源、导入时间与用途，否则日后没人知道它从哪来"
fi

# ---------- 7) 入口升级状态（只检测，不改写） ----------
if [ -f AGENTS.md ] && command -v python3 >/dev/null 2>&1; then
  upgrade_output="$(python3 "$SCRIPT_DIR/update-project.py" . --check 2>&1)"
  upgrade_code=$?
  case "$upgrade_code" in
    0) ;;
    3) warn "工作流入口有可用更新：python3 $SCRIPT_DIR/update-project.py .（仅预览）" ;;
    *) warn "工作流升级需处理：$upgrade_output" ;;
  esac
fi

if [ "$status" -eq 0 ]; then
  if [ "$warnings" -gt 0 ]; then
    echo "检查通过（另有 $warnings 条提醒）。"
  else
    echo "检查通过。"
  fi
fi
exit "$status"
