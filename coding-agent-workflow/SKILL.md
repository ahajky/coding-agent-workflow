---
name: coding-agent-workflow
description: 为软件项目建立并维护一套人与编程 Agent 共用的文件与文档工作流：生成 AGENTS.md 入口、建立任务工作区、按阶段推进、保存有价值的中间产出、在中断后恢复状态并完成交接归档。用于接手已有项目、从零开始一个构思、或把现有项目的协作流程规范化。
metadata:
  short-description: 编程 Agent 协作工作流
---

# 编程 Agent 协作工作流

## 目标

让人与编程 Agent 的协作产物（需求、分析、设计、决策、计划、代码、验证）各有明确归属，并保证换了对话、换了 Agent、隔了几个月后，仍能从文件恢复状态。

核心原则：

- **文件是事实来源，对话只是临时工作界面。**
- **同一份信息只有一个权威来源**（见 `references/file-conventions.md`）。
- **只保留降低未来理解/决策/重复劳动成本的产出**（见 `references/artifact-policy.md`）。
- **不因为规则而制造文档**：文件按需生成，简单任务可以只有代码和一份 `handoff.md`。

## 何时触发

- 用户要在已有项目上开始一项任务（修 Bug、加功能、重构、调研）。
- 用户要从零开始一个构思或新项目。
- 用户要把某个项目的文件/文档/协作流程规范化，或需要中断后恢复。

不适用：一次性的独立脚本、与本项目文件无关的单点问答。

## 执行流程

### 1. 建立或恢复上下文

先读项目入口 `AGENTS.md`。它是协议的**常驻锚点**——Skill 可能不被触发，但 `AGENTS.md` 每次会话都会被读取，所以协议要靠它兜底。若项目里还没有 `AGENTS.md`，先用 `scripts/init-project.sh` 生成（规则见 `references/agents-md.md`），再继续。

然后判断这是"新任务"还是"恢复已有任务"。

- 若 `work/active/` 下已存在相关任务目录，**先读它的 `handoff.md`**，据此恢复，不要重新分析并覆盖已有成果。恢复顺序见 `references/handoff-protocol.md`。
- 若是新任务，先判断项目状态：已有项目走"梳理现状"，全新项目走"澄清构思"。
- 恢复时必须核对真实代码、测试结果与 Git 差异，不要盲信交接文档。

### 2. 建立任务工作区

`init-task.sh` 会建出 `brief.md`、`plan.md`、`handoff.md` 三个必备文档——**简单任务写短一点即可，不要为了凑格式而灌水**。`validation.md`、`analysis.md` 等按 `references/file-conventions.md` 的触发条件再补。任务目录命名也见该文件。

多文件改动、重构、需要验证的功能用 `init-task.sh --branch auto` 一并开分支，并把分支名写进 `handoff.md` 的 `branch` 字段；单文件小修与纯文档改动可以直接做在 `main` 上。分支、提交与 worktree 约定见 `references/git-workflow.md`。

### 3. 按阶段推进

六阶段：发现 → 设计 → 计划 → 实施 → 验证 → 交接。各阶段的进入/退出条件和循环回退规则见 `references/workflow.md`。这是可循环流程，不是单向前进的流水线。

### 4. 阶段切换时检查产出质量

不要只检查"文件是否存在"，要检查内容：

- 计划阶段结束：任务是否有明确的完成条件和验收标准。
- 验证阶段结束：测试是**真实执行过**，还是仅由 Agent 声称通过。
- 交接阶段结束：能否回答"完成了什么、改了哪些关键文件、跑了哪些验证、还有什么没解决、下一步做什么"。

### 5. 交接与归档

把长期有效的结论沉淀到 `docs/`，把任务结论与下一步写入 `handoff.md`（含 `status`/`phase`/`updated` 的 front-matter），结束的任务用 `git mv` 移入 `work/archive/` 并单独提交一次归档。写入规则见 `references/handoff-protocol.md`，归档与分支回收见 `references/git-workflow.md`。

## 参考文件（按需加载）

- [references/workflow.md](references/workflow.md)：六阶段详细流程、阶段门槛、循环回退。
- [references/agents-md.md](references/agents-md.md)：`AGENTS.md` 常驻入口的四条铁律与嵌套约定。
- [references/file-conventions.md](references/file-conventions.md)：目录树、各目录职责、信息权威来源、命名规则、规范外产物的处理、对外产出与外部输入。
- [references/artifact-policy.md](references/artifact-policy.md)：A/B/C 三级保留策略、决策记录与过程记录的区分。
- [references/handoff-protocol.md](references/handoff-protocol.md)：任务状态定义、`handoff.md` front-matter 与结构、恢复顺序、并发约定。
- [references/git-workflow.md](references/git-workflow.md)：最小 Git 基准（入库范围、分支、提交、两条安全线、归档、校验），以及"项目自己的约束往哪扩展"。

## 模板

全部模板位于本技能的 `templates/` 下，按**产物落点**分三类：

**项目级**（`init-project.sh` 自动放到项目根）

- `templates/AGENTS.md` → `AGENTS.md`（协议常驻锚点）
- `templates/README.md` → `README.md`（面向人类的总览）

**任务级**（落在 `work/active/<任务>/`）

- 自动（`init-task.sh`）：`brief.md`、`plan.md`、`handoff.md`
- 按需复制：`validation.md`、`analysis.md`，触发条件见 `references/file-conventions.md`

**长期知识**（手工复制到 `docs/decisions/`）

- `templates/adr.md` → `ADR-NNN-<标题>.md`（重命名并编号）

> 通则：**模板名 = 产物名**。唯一例外是 ADR，因为它需要编号。

## 脚本（确定性操作）

以下脚本位于**本技能的 `scripts/`**（注意与项目自己的 `scripts/` 区分）：

- `scripts/init-project.sh [项目根] [--name 项目名]`：为一个项目生成 `AGENTS.md`、`README.md` 与目录骨架（不覆盖已存在文件）。
- `scripts/init-task.sh <任务目录> [--title 标题] [--branch <分支名|auto>]`：创建任务工作区（`brief.md`、`plan.md`、`handoff.md`）并填好 `handoff` 的 front-matter；`--branch` 会一并创建任务分支并写入 `branch` 字段。
- `scripts/check-project.sh [项目根]`：检查必需文件与 `AGENTS.md` 铁律；校验每个任务的 front-matter（`task` 与目录名一致、`status`/`phase` 取值合法、`updated` 格式正确、`branch` 指向的分支是否存在）；检查 Git 约定（`.gitignore` 是否覆盖 `scratch/`、提交信息格式、`handoff.md` 是否仍未提交）；提醒未填占位符与停滞任务（`STALE_DAYS` 可调，默认 30）。
- `scripts/install-git-hooks.sh [项目根]`：安装（可选的）`pre-commit` 钩子，提交前自动跑 `check-project.sh`。

脚本仅负责确定性动作（建目录、查缺失），不要用提示词替代它们，也不要让 Agent 手工重复这些步骤。
