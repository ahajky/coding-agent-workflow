#!/usr/bin/env bash
# 初始化一个任务工作区（从 templates/ 复制模板），可一并创建任务分支。
# 用法: init-task.sh <任务目录> [--title 标题] [--branch <分支名|auto>]
# 始终创建 brief.md、plan.md、handoff.md 三个必备文档。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

TASK_DIR=""
TITLE=""
BRANCH=""

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "用法: init-task.sh <任务目录> [--title 标题] [--branch <分支名|auto>]"
      exit 0
      ;;
    --title)
      TITLE="${2:-}"; shift 2
      ;;
    --branch)
      if [ -z "${2:-}" ]; then
        echo "错误: --branch 需要一个值（分支名，或 auto 表示 <type>/<任务目录名>）" >&2
        exit 2
      fi
      BRANCH="$2"; shift 2
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
  echo "用法: init-task.sh <任务目录> [--title 标题] [--branch <分支名|auto>]" >&2
  exit 2
fi

# 目录名按约定带日期前缀：YYYYMMDD-短语（或排序用的 YYYY-NNN-短语）。
# 只给了短语时自动补当天日期，保证任务目录与分支名始终可追溯。
TASK_DIR="$(printf '%s' "$TASK_DIR" | sed 's:/*$::')"
if [ -z "$TASK_DIR" ]; then
  echo "错误: 任务目录不能为空" >&2
  exit 2
fi
BASE="$(basename "$TASK_DIR")"
if ! printf '%s' "$BASE" | grep -qE '^([0-9]{8}|[0-9]{4}-[0-9]{3})-'; then
  DATED="$(date '+%Y%m%d')-$BASE"
  TASK_DIR="$(dirname "$TASK_DIR")/$DATED"
  echo "提醒: 任务目录缺少日期，已按约定改为: $TASK_DIR"
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

render brief.md brief.md
render plan.md plan.md
render handoff.md handoff.md

# 自动填入 handoff 的 front-matter：任务名与当前时刻
TASK_NAME="$(basename "$TASK_DIR")"
NOW="$(date '+%Y-%m-%d %H:%M')"
HANDOFF="$TASK_DIR/handoff.md"

sed_inplace() { # <表达式> <文件>
  if sed --version >/dev/null 2>&1; then
    sed -i "$1" "$2"
  else
    sed -i '' "$1" "$2"
  fi
}

if [ -f "$HANDOFF" ]; then
  sed_inplace "s|<任务目录名>|$TASK_NAME|g; s|<YYYY-MM-DD HH:MM>|$NOW|g" "$HANDOFF"
fi

# 可选：一并创建任务分支（--branch <分支名|auto>）
if [ -n "$BRANCH" ]; then
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "提醒: 不在 Git 仓库中，跳过建分支（handoff 的 branch 字段请填 none）" >&2
  else
    if [ "$BRANCH" = "auto" ]; then
      BRANCH="feat/$TASK_NAME"
    fi
    if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      echo "提醒: 分支 $BRANCH 已存在，直接切换" >&2
      git switch "$BRANCH"
    else
      git switch -c "$BRANCH"
    fi
    sed_inplace "s|^branch: .*|branch: $BRANCH|" "$HANDOFF"
    echo "已切换到分支: $BRANCH"
  fi
fi

echo "已创建任务工作区: $TASK_DIR"
ls -1 "$TASK_DIR"
echo "下一步: 填写 brief.md / plan.md，用 \"<type>($TASK_NAME): <说明>\" 提交"
