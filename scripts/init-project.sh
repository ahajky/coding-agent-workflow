#!/usr/bin/env bash
# 为一个项目接入协作工作流：生成 AGENTS.md、README.md 与工作流目录。
# 工作流的个人产出集中在 workflow_root（默认 .agent/），入口 AGENTS.md 留在根目录，
# 两者默认都排除在项目版本控制之外。
# 已存在的文件不会被覆盖。
# 用法: init-project.sh [项目根目录] [--name 项目名] [--workflow-root 目录]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

ROOT="."
NAME=""
WFR=".agent"

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "用法: init-project.sh [项目根目录] [--name 项目名] [--workflow-root 目录]"
      echo ""
      echo "  --workflow-root  工作流目录，状态与过程产出都放在它下面（默认 .agent）"
      echo ""
      echo "AGENTS.md 与工作流目录默认写入 .gitignore：个人工作流内容不进代码提交。"
      exit 0
      ;;
    --name)
      NAME="${2:-}"; shift 2
      ;;
    --workflow-root)
      WFR="${2:-}"; shift 2
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

trim_slash() { # 去掉结尾的斜杠
  local p="$1"
  while [ "${p%/}" != "$p" ]; do p="${p%/}"; done
  printf '%s' "$p"
}

WFR="$(trim_slash "$WFR")"
if [ -z "$WFR" ] || [ "${WFR#/}" != "$WFR" ] || [ "$WFR" = "." ]; then
  echo "错误: --workflow-root 必须是仓库内的相对路径（不能为空、不能是 .、不能以 / 开头）: ${WFR:-<空>}" >&2
  exit 2
fi

created=0
skipped=0
conflicts=0

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

# 工作流目录已存在且非空：可能是在复用，也可能是别的工具在用
if [ -d "$ROOT/$WFR" ] && [ -n "$(ls -A "$ROOT/$WFR" 2>/dev/null)" ]; then
  echo "提醒: $WFR 已存在且非空——确认它确实是本工作流的目录；不是的话用 --workflow-root 换一个名字"
  conflicts=$((conflicts + 1))
fi

for d in docs/product docs/architecture docs/decisions docs/guides \
         reports references work/active work/archive; do
  mkdir -p "$ROOT/$WFR/$d"
done

agents="$ROOT/AGENTS.md"
agents_new=no
[ -f "$agents" ] || agents_new=yes

place AGENTS.md AGENTS.md
place README.md README.md

if [ "$agents_new" = no ]; then
  echo "提醒: AGENTS.md 已存在，未修改。请把模板里的四条铁律、目录导航、Git 约定合并进去，并补上 front-matter 的 workflow_root。"
fi

# 把工作流根目录写进 AGENTS.md：front-matter 给脚本读，正文路径给人读
if [ "$agents_new" = yes ] && [ -f "$agents" ]; then
  pattern="s|\.agent/|$WFR/|g; s|^workflow_root: .*|workflow_root: $WFR|"
  if sed --version >/dev/null 2>&1; then
    sed -i "$pattern" "$agents"
  else
    sed -i '' "$pattern" "$agents"
  fi
fi

# 个人工作流不进版本控制；.gitignore 不存在则创建（>> 会自动创建）
gi="$ROOT/.gitignore"
gi_changed=no
if ! grep -q "coding-agent-workflow" "$gi" 2>/dev/null; then
  {
    echo ""
    echo "# coding-agent-workflow：个人工作流，不进代码提交"
  } >> "$gi"
  gi_changed=yes
fi
for ignore_entry in "$WFR/" "AGENTS.md"; do
  if ! grep -Fxq "$ignore_entry" "$gi" 2>/dev/null; then
    echo "$ignore_entry" >> "$gi"
    gi_changed=yes
  fi
done
if [ "$gi_changed" = yes ]; then
  echo "更新: .gitignore"
fi

if git -C "$ROOT" ls-files --error-unmatch AGENTS.md >/dev/null 2>&1; then
  echo "提醒: AGENTS.md 已被 Git 跟踪。新增忽略不会取消跟踪；要让工作流只留在本地，请执行: git -C \"$ROOT\" rm --cached AGENTS.md"
fi

echo "已创建 $created 个文件，跳过 $skipped 个已存在文件。"
echo "工作流目录: $WFR/{docs/{product,architecture,decisions,guides},work/{active,archive},reports,references}"
echo "已有外部资料? 用 scripts/import-reference.sh <路径> --note \"用途\" 导入并登记来源。"
if [ "$conflicts" -gt 0 ]; then
  echo "注意: $WFR 里已有内容，请确认没有覆盖别的用途。"
fi
