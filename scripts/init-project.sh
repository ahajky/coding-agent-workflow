#!/usr/bin/env bash
# 为一个项目接入协作工作流：生成 AGENTS.md、README.md 与目录骨架。
# 已存在的文件不会被覆盖；同名且非空的目录会先做冲突提示。
# 用法: init-project.sh [项目根目录] [--name 项目名] [--tasks-root 目录] [--docs-root 目录]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

ROOT="."
NAME=""
TASKS_ROOT="work"
DOCS_ROOT="docs"

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help)
      echo "用法: init-project.sh [项目根目录] [--name 项目名] [--tasks-root 目录] [--docs-root 目录]"
      echo ""
      echo "  --tasks-root  任务工作区的根目录（默认 work）"
      echo "  --docs-root   长期文档的根目录（默认 docs）"
      echo ""
      echo "项目里已有同名但用途不同的目录时，用这两个参数换根，脚本会把映射写进 AGENTS.md。"
      exit 0
      ;;
    --name)
      NAME="${2:-}"; shift 2
      ;;
    --tasks-root)
      TASKS_ROOT="${2:-}"; shift 2
      ;;
    --docs-root)
      DOCS_ROOT="${2:-}"; shift 2
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

check_root() { # <名称> <值>
  local n="$1" v="$2"
  if [ -z "$v" ] || [ "${v#/}" != "$v" ]; then
    echo "错误: $n 必须是仓库内的相对路径（不能为空或以 / 开头）: ${v:-<空>}" >&2
    exit 2
  fi
}

TASKS_ROOT="$(trim_slash "$TASKS_ROOT")"
DOCS_ROOT="$(trim_slash "$DOCS_ROOT")"
check_root TASKS_ROOT "$TASKS_ROOT"
check_root DOCS_ROOT "$DOCS_ROOT"

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

# 已存在且非空的目录：可能同名不同义，先提示，不擅自改写项目原有结构
check_dir() { # <相对路径> <用途>
  local p="$ROOT/$1"
  if [ -d "$p" ] && [ -n "$(ls -A "$p" 2>/dev/null)" ]; then
    echo "提醒: $1 已存在且非空（$2）——含义相同就复用；不同请换名重跑（--tasks-root / --docs-root）"
    conflicts=$((conflicts + 1))
  fi
}

check_dir "$DOCS_ROOT" "长期文档"
check_dir "$TASKS_ROOT" "任务工作区"
check_dir reports "对外交付物"
check_dir references "外部参考资料"

for d in "$DOCS_ROOT/product" "$DOCS_ROOT/architecture" "$DOCS_ROOT/decisions" "$DOCS_ROOT/guides" \
         reports references "$TASKS_ROOT/active" "$TASKS_ROOT/archive"; do
  mkdir -p "$ROOT/$d"
done

agents="$ROOT/AGENTS.md"
agents_new=no
[ -f "$agents" ] || agents_new=yes

place AGENTS.md AGENTS.md
place README.md README.md

# 已存在的 AGENTS.md 不覆盖，提示人工合并
if [ "$agents_new" = no ]; then
  echo "提醒: AGENTS.md 已存在，未修改。请把模板里的四条铁律、目录导航、Git 约定合并进去，并补上 front-matter 的路径映射。"
fi

# 把路径映射写进 AGENTS.md：front-matter 给脚本读，正文路径给人读
if [ "$agents_new" = yes ] && [ -f "$agents" ]; then
  # 先替换正文路径，再用实际的根覆盖 front-matter 两行（顺序不能反）
  pattern="s|work/|$TASKS_ROOT/|g; s|docs/|$DOCS_ROOT/|g"
  pattern="$pattern; s|^tasks_root: .*|tasks_root: $TASKS_ROOT|; s|^docs_root: .*|docs_root: $DOCS_ROOT|"
  if sed --version >/dev/null 2>&1; then
    sed -i "$pattern" "$agents"
  else
    sed -i '' "$pattern" "$agents"
  fi
fi

# 忽略任务临时产物；.gitignore 不存在则创建（>> 会自动创建）
gi="$ROOT/.gitignore"
if grep -q "coding-agent-workflow" "$gi" 2>/dev/null; then
  : # 已经写过，不重复追加
else
  {
    echo ""
    echo "# coding-agent-workflow：任务临时产物不入库（可整目录删除）"
    echo "$TASKS_ROOT/active/*/scratch/"
  } >> "$gi"
  echo "更新: .gitignore"
fi

echo "已创建 $created 个文件，跳过 $skipped 个已存在文件。"
echo "目录骨架: $DOCS_ROOT/{product,architecture,decisions,guides}, reports/, references/, $TASKS_ROOT/{active,archive}"
if [ "$conflicts" -gt 0 ]; then
  echo "注意: 有 $conflicts 个同名目录已存在，请确认它们的用途与本工作流一致。"
fi
