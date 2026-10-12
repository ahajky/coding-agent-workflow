---
task: <任务目录名>
status: planned
phase: discover
owner: <负责人：人 或 agent>
updated: <YYYY-MM-DD HH:MM>
---

# Task Handoff

> 用途：任务的恢复入口。只放"下次进来必须知道的东西"，正文尽量控制在一屏内；
> 细节回链到 `plan.md` / `analysis.md`，不要在这里复述。
> `status` 只允许：planned / in_progress / blocked / in_review / done / abandoned
> `phase` 只允许：discover / design / plan / execute / verify / close
> `updated` 每次收工都要改成当时的日期与时间（精确到分钟），供脚本判断先后与停滞。

## Goal

<本任务要解决什么问题>

## Completed

- <已完成的工作>

## Current State

<当前代码、设计与任务进展；文档与代码不一致时以代码为准>

## Blockers

<尚未解决的问题与原因；没有就写"无">

## Next Actions

1. <下一步行动，对应验收条件>

## Validation

- <已运行的测试及结果>
- <尚未执行的验证>

## References

- 任务简报：`brief.md`
- 实施计划：`plan.md`
- <相关需求>
- <相关决策>
