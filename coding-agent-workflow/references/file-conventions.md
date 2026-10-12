# 文件与目录规范

## 目录树

```
my-project/
├── AGENTS.md                 # Agent 项目入口
├── README.md                 # 面向人类的总览
├── docs/                     # 长期知识
│   ├── product/              # 目标、需求
│   ├── architecture/         # 架构、代码地图
│   ├── decisions/            # ADR
│   └── guides/               # 开发约定、上手文档
├── work/
│   ├── active/               # 当前任务工作区
│   └── archive/              # 已结束任务
├── src/
├── tests/
└── scripts/
```

按需裁剪，不必每个项目都建全。

## 目录职责

| 位置 | 负责 | 不负责 |
| --- | --- | --- |
| `AGENTS.md` | 项目规则、目录导航、测试命令、文档维护要求、任务路由 | 不做百科全书 |
| `docs/` | 长期有效的目标、需求、架构、决策、约定 | 不记一次性任务过程 |
| `work/active/` | 当前任务的需求澄清、调查、方案、计划、验证、交接 | 不放正式测试/脚本 |
| `work/archive/` | 已结束任务的重要结论、关键过程、验证证据 | 不存临时日志、重复草稿 |
| `src/ tests/ scripts/` | 正式代码、测试、可复用脚本 | 不作文档沉淀地 |

## 信息权威来源（唯一）

| 信息 | 权威来源 |
| --- | --- |
| 项目目标与长期需求 | `docs/product/` |
| 当前有效架构 | `docs/architecture/` |
| 技术选择的理由 | `docs/decisions/`（ADR） |
| 某任务如何实施 | `work/active/<任务>/plan.md` |
| 任务的测试与验收结果 | `work/active/<任务>/validation.md` |
| 当前进度与下一步 | `work/active/<任务>/handoff.md` |
| 历史会话原文 | Agent 自身的会话记录系统 |

> 任务文档记录过程，长期文档记录仍然有效的结论。方案一旦成为长期决策，就沉淀到 `docs/decisions/` 或架构文档。

## 任务目录命名

格式：`YYYY-NNN-<短横线短语>`，例如 `2026-001-add-auth`。

- `YYYY`：年份；`NNN`：当年顺序号（可全局唯一即可）。
- 短语用小写英文、短横线分词，说明任务主题。

## 任务目录的最小文件集

按复杂度选择，不要机械套全：

| 复杂度 | 至少包含 |
| --- | --- |
| 简单（改一行、小修） | `handoff.md` |
| 一般（加一个小功能） | `brief.md`（可合入 handoff）、`plan.md`、`validation.md`、`handoff.md` |
| 复杂（新模块、调研、跨模块改动） | `brief.md`、`analysis.md`、`plan.md`、`validation.md`、`handoff.md`，必要时加 ADR |

## `AGENTS.md` 应包含

- 项目一句话定位与当前主任务。
- 目录导航：去哪找需求、架构、决策、当前任务。
- 常用命令：构建、测试、Lint、运行。
- 文档维护要求：什么时候更新哪些文档。
- 任务路由：不同任务该先读哪些文件。

保持精简，指向细节而非复制细节。
