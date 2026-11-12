#!/usr/bin/env bash
# 同时安装 pre-commit 与 commit-msg；不覆盖其他工具的钩子。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-.}"
cd "$ROOT"
git rev-parse --is-inside-work-tree >/dev/null
# 在目标仓库内解析，支持从其他 cwd 安装、worktree 和 core.hooksPath。
HOOKS_DIR="$(git rev-parse --git-path hooks)"
for kind in pre-commit commit-msg; do
  hook="$HOOKS_DIR/$kind"
  if [ -L "$hook" ]; then echo "错误: 不覆盖符号链接钩子 $hook" >&2; exit 1; fi
  if [ -e "$hook" ] && ! grep -q '^# coding-agent-workflow managed hook$' "$hook" && ! grep -q '^# 由 coding-agent-workflow 的 install-git-hooks.sh 生成' "$hook"; then
    echo "错误: $hook 已存在且不属于本工作流，两个钩子均未修改。" >&2
    exit 1
  fi
done
mkdir -p "$HOOKS_DIR"
# 运行时读取路径，技能搬迁后重新运行安装或更新此本地配置即可。
git config --local codingAgentWorkflow.scripts "$SCRIPT_DIR"
for kind in pre-commit commit-msg; do
  {
    cat <<'EOF'
#!/usr/bin/env bash
# coding-agent-workflow managed hook
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SCRIPTS="$(git config --get codingAgentWorkflow.scripts)"
if [ ! -f "$SCRIPTS/check-project.sh" ] || [ ! -f "$SCRIPTS/check-commit-message.py" ]; then
  echo "工作流工具已移动或缺失，阻止提交；请重新运行 install-git-hooks.sh。" >&2
  exit 1
fi
EOF
    if [ "$kind" = pre-commit ]; then
      echo 'bash "$SCRIPTS/check-project.sh" "$ROOT" --strict'
    else
      echo 'python3 "$SCRIPTS/check-commit-message.py" "$1"'
    fi
  } > "$HOOKS_DIR/$kind"
  chmod +x "$HOOKS_DIR/$kind"
  echo "已安装: $HOOKS_DIR/$kind"
done
echo "pre-commit 检查工作区与索引；commit-msg 检查本次消息。显式跳过：git commit --no-verify。"
