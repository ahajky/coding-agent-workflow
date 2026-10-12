# 任务状态与恢复

## 任务状态定义

| 状态 | 含义 |
| --- | --- |
| `planned` | 已建立任务工作区，尚未开始实施 |
| `in_progress` | 正在实施；可能有未完成的步骤 |
| `blocked` | 被外部因素或未决问题卡住，需要人类或外部输入 |
| `in_review` | 实施完成，等待验证/审查 |
| `done` | 已完成验证，结论已沉淀 |
| `abandoned` | 主动放弃，需记录原因与可能的后续 |

状态写在 `handoff.md` 顶部的 front-matter 里，让人和脚本都能读。

## front-matter 字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `task` | 是 | 任务目录名（与目录保持一致） |
| `status` | 是 | 必须是上表六个状态之一 |
| `owner` | 是 | 当前负责人（人或 agent） |
| `updated` | 是 | 最后更新日期 `YYYY-MM-DD`，每次收工都要改 |
| `branch` | 否 | 关联分支 / worktree，便于并行协作 |

`status` 与 `updated` 是脚本检查的锚点，其余正文允许自由书写。

## `handoff.md` 结构

```markdown
---
task: 20261010-add-auth
status: in_progress
owner: aha
updated: 2026-10-10
---

## Goal
本任务希望解决什么问题。

## Completed
- 已完成的工作
- 已验证的行为

## Current State
当前代码、设计和任务进展。

## Blockers
尚未解决的问题与原因。

## Next Actions
1. 下一步行动
2. 对应的验收条件

## Validation
- 已运行的测试及结果
- 尚未执行的验证

## References
- 相关需求文档
- 相关决策记录
```

它是**精简的恢复入口**，不是冗长报告。细节放 `plan.md` / `analysis.md`，这里只放"下次进来必须知道的东西"。

## 恢复顺序

1. 读 `AGENTS.md`，了解项目规则与导航。
2. 读当前任务的 `handoff.md`；任务若已结束，读 `work/archive/<任务>/handoff.md`。
3. 按 `References` 读必要的计划、需求、决策文档。
4. 检查真实代码、测试结果与 Git 工作区差异，**核对文档是否落后于真实状态**。
5. 从 `Next Actions` 的第一项继续。

> 文件记录的是上一次确认的状态，不一定是此刻的真实状态。恢复时务必以代码与 Git 为准做校正。

## 恢复时的行为约束

- **不要重新开始**：已有任务目录存在时，先读再判断，不覆盖已有分析。
- **不要盲信文档**：文档与代码冲突时，以代码为准并修正文档。
- **进度变化要写回**：每次阶段推进或中断前，更新 `handoff.md` 的 `status`、`Completed`、`Current State`、`Next Actions`、`updated`。

## 长度约束

`handoff.md` 是恢复入口，不是报告。**正文目标控制在一屏以内**。一旦超了，说明细节该挪走：实施细节 → `plan.md`、方案权衡 → `analysis.md`、长期结论 → `docs/`、原始输出 → 不入库（或 `scratch/`，已被 gitignore）。

## 并发写入

front-matter 让冲突**可见**，但不解决覆盖。约定：

- **同一任务同一时间只允许一个写者**（一个人或一个 agent）。
- 确需并行时，用**分支或 worktree 隔离**，各写各自的副本。
- 合并前先比对双方 `updated`：以晚的一方为基线，逐条合并 `Completed` / `Next Actions`，不要整段覆盖。

## 归档

任务进入 `done` 或 `abandoned` 后：

1. 把长期结论沉淀到 `docs/`。
2. 修剪 `handoff.md`，只留对后人有用的事实（结论、关键文件、验证证据、遗留问题）。
3. 将任务目录从 `work/active/` 移到 `work/archive/`。
