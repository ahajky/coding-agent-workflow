#!/usr/bin/env bash
# 安装 pre-commit 钩子：提交前自动跑 check-project.sh。
# 钩子是可选增强——不安装也不影响协议有效性，只是把"软约定"变成提交时会被拦下的硬检查。
# 用法: install-git-hooks.sh [项目根目录]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$SCRIPT_DIR/check-project.sh"
ROOT="${1:-.}"

if [ ! -d "$ROOT" ]; then
  echo "错误: 目录不存在: $ROOT" >&2
  exit 2
fi

if [ ! -f "$CHECK" ]; then
  echo "错误: 找不到 check-project.sh: $CHECK" >&2
  exit 1
fi

if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "错误: $ROOT 不是 Git 仓库，无法安装钩子。" >&2
  exit 1
fi

HOOKS_DIR="$(cd "$ROOT" && git rev-parse --git-path hooks)"
mkdir -p "$HOOKS_DIR"
HOOK="$HOOKS_DIR/pre-commit"

if [ -e "$HOOK" ] && ! grep -q "coding-agent-workflow" "$HOOK" 2>/dev/null; then
  echo "错误: $HOOK 已存在且不是本工具生成的，不覆盖。请先备份并手工合并。" >&2
  exit 1
fi

cat > "$HOOK" <<EOF
#!/usr/bin/env bash
# 由 coding-agent-workflow 的 install-git-hooks.sh 生成（可重新运行覆盖）。
# 提交前检查工作流文件与 Git 约定；跳过检查请用 git commit --no-verify
set -uo pipefail
ROOT="\$(git rev-parse --show-toplevel)"
CHECK="$CHECK"
if [ -f "\$CHECK" ]; then
  bash "\$CHECK" "\$ROOT" || {
    echo "" >&2
    echo "工作流检查未通过，已阻止本次提交。" >&2
    echo "修正后重试；确要跳过请用 git commit --no-verify" >&2
    exit 1
  }
else
  echo "提醒: 找不到 check-project.sh（\$CHECK），跳过工作流检查" >&2
fi
EOF

chmod +x "$HOOK"
echo "已安装: $HOOK"
echo "提交前将自动运行: $CHECK"
echo "跳过检查: git commit --no-verify"
