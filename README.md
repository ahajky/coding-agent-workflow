# 编程 Agent 协作工作流

> 一套以**文件**为状态载体、以 **Git** 为历史、以 **Skill** 为入口的协作协议。
> 目标只有一个：换对话、换 Agent、隔几个月回来，仍然知道「项目现在是什么状态、为什么这么设计、下一步做什么」。

## 它解决什么问题

人和编程 Agent 长期协作时，需求、分析、设计、决策、计划、代码和验证结果会散落在各个对话里。对话一关，上下文就没了。

这套协议把每类产出固定到唯一位置，让状态不依赖聊天历史：

- **职责明确**：每类文件有唯一、清晰的存放位置。
- **过程可追溯**：不只留最终代码，也留值得复用的中间产出。
- **状态可恢复**：新会话读文件就能接上，不必问"我们做到哪了"。
- **流程可复用**：接手旧项目、从零开始，走同一套机制。

三条判断贯穿全文：

1. **文件是事实来源，对话只是临时工作界面。**
2. **同一份信息只有一个权威来源。**
3. **只保留降低未来理解、决策、重复劳动成本的产出。**

## 四条铁律

写在每个项目的 `AGENTS.md` 里，连"小修"也不豁免：

1. **开工先恢复上下文**：先看 `work/active/` 有没有相关任务，有就先读它的 `handoff.md`。
2. **收工必写回状态**：`status`、`Completed`、`Current State`、`Next Actions`、`updated`。
3. **尊重信息归属**：长期结论进 `docs/`，任务过程留在 `work/active/<任务>/`。
4. **不写敏感信息**：密钥、凭证、内网地址、客户数据一律不入文档。

## 快速开始

### 1. 安装为 Codex Skill

仓库根目录就是技能目录，克隆下来可以直接用，不会多一层嵌套：

```bash
# 克隆：仓库名即技能目录名
git clone <仓库地址> ~/.codex/skills/coding-agent-workflow

# 或本地已有仓库，直接软链
ln -s "/path/to/this/repo" ~/.codex/skills/coding-agent-workflow
```

### 2. 让一个项目接入

```bash
cd ~/code/my-project          # 需是 Git 仓库
~/.codex/skills/coding-agent-workflow/scripts/init-project.sh . --name my-project
```

它会生成 `AGENTS.md`、`README.md` 与目录骨架（`docs/`、`work/`、`reports/`、`references/`），并往 `.gitignore` 加上 `scratch/` 规则；已存在的文件不覆盖。

接入已有项目时，如果 `docs/`、`reports/`、`work/` 已经存在但用途不同，先换根再跑：

```bash
~/.codex/skills/coding-agent-workflow/scripts/init-project.sh . \
  --tasks-root agent-work --docs-root docs/project
```

脚本会提示冲突并把映射写进 `AGENTS.md`。原则是**过程产物独占一个根，长期知识沿用项目已有结构**，不要把全部内容塞进一个总文件夹——那样会出现两套文档树。

### 3. 开一个任务

```bash
~/.codex/skills/coding-agent-workflow/scripts/init-task.sh \
  work/active/20261016-add-auth --title "加登录" --branch auto
```

生成 `brief.md`、`plan.md`、`handoff.md`，并切出 `feat/20261016-add-auth` 分支。

### 4. 日常循环

```
读 AGENTS.md → 读 handoff.md → 改代码 → 跑验证 → 更新 handoff → 提交
```

随时用这条命令查漏：

```bash
~/.codex/skills/coding-agent-workflow/scripts/check-project.sh .
```

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `SKILL.md` | 技能入口：何时触发、执行流程、脚本与模板清单 |
| `coding-agent-workflow-protocol.md` | 完整协议：原则、目录与信息归属、六阶段流程、版本约定、路线图 |
| `references/` | 按需加载的细则：文件规范、Git 最小基准、交接协议、产物保留策略、`AGENTS.md` 规则 |
| `templates/` | 项目级（`AGENTS.md` / `README.md`）与任务级（`brief` / `plan` / `handoff` / `validation` / `analysis`）模板 |
| `scripts/` | 初始化、完整性检查、Git 钩子安装 |
| `agents/openai.yaml` | 技能显示名与默认提示 |

## 一个任务长什么样

```
work/active/20261016-add-auth/
├── brief.md       # 是什么、边界、明确不做的事
├── plan.md        # 怎么做、验收标准
├── handoff.md     # 现在到哪了、下一步做什么
├── validation.md  # 按需：验证证据
├── analysis.md    # 按需：方案比较
└── scratch/       # 临时脚本与日志，不入库
```

**目录是默认约定，不是白名单；文件按需生成。** 一个只改两行的任务，写一句 `handoff.md` 也算完整。

## 版本

采用 `a.b.c`：`c` 是想到就改的小改动，`b` 是在真实项目上验证通过后进位，`a` 是新增功能或创意、由人指定。完整定义与变更历史见[协议文档](./coding-agent-workflow-protocol.md)。

## 不适用

一次性的独立脚本、与本项目文件无关的单点问答、不需要留下任何持久产物的临时对话——这些直接用 Agent 就好，不必套协议。
