---
# 路径映射：工作流的所有产出都放在这个目录下，默认不进版本控制。
# 想换位置就改下面一行（如 agent-work），并同步更新「目录导航」表。
workflow_root: .agent
---

# AGENTS.md

> 本文件是编程 Agent 进入本项目的入口，请在**任何任务开始前**读完本文件。

## 项目定位

<一句话说明项目是什么、为谁解决什么问题。>

## 工作流铁律（必须遵守）

本项目使用「编程 Agent 协作工作流」。以下四条不可省略：

1. **开工先恢复上下文**：任何任务开始前，先看 `.agent/work/active/` 下是否有相关任务目录；有就读它的 `handoff.md`，据此继续，**不要重新分析、不要覆盖已有成果**。
2. **收工必写回状态**：任务完成或中断前，更新 `handoff.md` 的 `status`、`Completed`、`Current State`、`Next Actions`、`updated`。
3. **尊重信息归属**：任务过程留在 `.agent/work/active/<任务>/`，我的理解与决策留在 `.agent/docs/`；**这些是个人工作记忆，不直接写进项目正式文档**。要让它们成为团队共识，经讨论后搬过去，并在原处留一条指针。
4. **不写敏感信息**：文档中不出现密钥、token、密码、内网地址、客户个人数据。

重活（新功能、重构、调研）按六阶段推进：发现 → 设计 → 计划 → 实施 → 验证 → 交接；小修可以不建完整文档，但**第 1、2 条不豁免**。完整规则见 `coding-agent-workflow` 技能。

## 目录导航

以下路径都在 `workflow_root`（默认 `.agent/`）下：

| 位置 | 内容 |
| --- | --- |
| `docs/product/` | 我对目标与需求的理解（待团队确认的写在最前） |
| `docs/architecture/` | 我梳理的架构与代码地图 |
| `docs/decisions/` | 我认可的决策与理由（ADR） |
| `docs/guides/` | 我踩过的坑、可复用的操作步骤 |
| `reports/` | 交付物草稿（定稿后再搬进项目正式位置） |
| `references/` | 外部资料的**工作副本**（只读；来源与导入时间记在 `references/README.md`） |
| `work/active/<任务>/` | 当前任务工作区（含 handoff.md） |
| `work/archive/` | 已结束任务 |

> 本表是**实际路径的权威**。改了上面的 `workflow_root`，这里的路径同步改。

## 常用命令

```bash
# 安装依赖
<命令>

# 运行测试
<命令>

# 代码检查
<命令>

# 本地运行
<命令>
```

## Git 约定

基准规则见 `coding-agent-workflow` 技能的 `references/git-workflow.md`。本项目必须遵守的只有这几条：

- 一任务一分支：`<type>/<任务目录名>`；单文件小修与纯文档改动可直接提交 `main`。
- 提交：`<type>(<任务目录名>): <说明>`，一个提交只做一件事。
- 不改写已推送的历史（rebase / amend / force push），合并用 `merge`。
- **`.agent/` 整个目录不进版本控制**：代码提交里不出现这套工作流的内容。任务对应哪个代码分支，写在 `handoff.md` 的 `branch` 字段里。

本项目特有的补充约束（PR 流程、发布、评审等）写在本节下面，不要改基准。

## 任务路由

- 修 Bug：先读 `.agent/docs/architecture/` 下的架构与代码地图，以及相关任务的 `handoff.md`。
- 加功能：先读 `.agent/docs/product/`（需求）和 `.agent/docs/architecture/`（架构）。
- 重构 / 迁移：先读 `.agent/docs/decisions/`，确认既有约束再动手。

具体文件名由本项目自行约定；某份文档还没建立，先补再动手。
