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

状态写在 `handoff.md` 的 `## Status`。

## `handoff.md` 结构

```markdown
# Task Handoff

## Status
in_progress

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
2. 读当前任务的 `handoff.md`。
3. 按 `References` 读必要的计划、需求、决策文档。
4. 检查真实代码、测试结果与 Git 工作区差异，**核对文档是否落后于真实状态**。
5. 从 `Next Actions` 的第一项继续。

> 文件记录的是上一次确认的状态，不一定是此刻的真实状态。恢复时务必以代码与 Git 为准做校正。

## 恢复时的行为约束

- **不要重新开始**：已有任务目录存在时，先读再判断，不覆盖已有分析。
- **不要盲信文档**：文档与代码冲突时，以代码为准并修正文档。
- **进度变化要写回**：每次阶段推进或中断前，更新 `handoff.md` 的 Status、Completed、Current State、Next Actions。

## 归档

任务进入 `done` 或 `abandoned` 后：

1. 把长期结论沉淀到 `docs/`。
2. 修剪 `handoff.md`，只留对后人有用的事实（结论、关键文件、验证证据、遗留问题）。
3. 将任务目录从 `work/active/` 移到 `work/archive/`。
