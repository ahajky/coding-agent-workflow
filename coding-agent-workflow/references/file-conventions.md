# 文件与目录规范

## 目录树

```
my-project/
├── AGENTS.md                 # Agent 项目入口（协议锚点）
├── README.md                 # 面向人类的总览
├── docs/                     # 长期知识
│   ├── product/              # 目标、需求（如 requirements.md）
│   ├── architecture/         # 架构、代码地图（如 overview.md、codebase-map.md）
│   ├── decisions/            # ADR（ADR-NNN-<标题>.md）
│   └── guides/               # 开发约定、经验、上手文档
├── work/
│   ├── active/               # 当前任务工作区
│   │   └── <YYYYMMDD-短语>/
│   │       ├── brief.md / analysis.md / plan.md / validation.md / handoff.md
│   │       └── scratch/      # 临时脚本与数据（不入库，可整目录丢弃）
│   └── archive/              # 已结束任务
├── src/
├── tests/
└── scripts/                  # 项目里可复用的正式脚本
```

按需裁剪，不必每个项目都建全。文档类的标准产物名只是**约定**：目录先建，文件按需生成，不预创建空文档。

## 占位符约定

- `<...>` 表示**待填**：必须替换成真实内容，或整行删掉。`check-project.sh` 会扫描"整行就是占位符"的行并提醒。
- `（...）` 只用于句中的补充说明，**不要**用它充当占位符。
- 提交前不该留下未填的 `<...>`。

## 目录职责

| 位置 | 负责 | 不负责 |
| --- | --- | --- |
| `AGENTS.md` | 项目规则、目录导航、测试命令、文档维护要求、任务路由 | 不做百科全书 |
| `README.md` | 面向人类的总览：这是什么、怎么开始 | 不写 Agent 规则（那是 `AGENTS.md` 的职责） |
| `docs/` | 长期有效的目标、需求、架构、决策、约定 | 不记一次性任务过程 |
| `work/active/` | 当前任务的需求澄清、调查、方案、计划、验证、交接 | 不放正式测试/脚本 |
| `work/active/<任务>/scratch/` | 该任务的临时验证脚本、日志、抓包、中间数据（不入库，可整体删除） | 不放结论；不放正式测试；不作为任务证据的唯一存放地 |
| `work/archive/` | 已结束任务的重要结论、关键过程、验证证据 | 不存临时日志、重复草稿 |
| `src/ tests/ scripts/` | 正式代码、测试、可复用脚本 | 不作文档沉淀地 |

## 信息权威来源（唯一）

| 信息 | 权威来源 |
| --- | --- |
| 项目目标与长期需求 | `docs/product/` |
| 当前有效架构 | `docs/architecture/` |
| 技术选择的理由 | `docs/decisions/`（ADR） |
| 操作性经验与上手说明 | `docs/guides/` |
| 任务的背景与调查 | `work/active/<任务>/brief.md`、`analysis.md` |
| 某任务如何实施 | `work/active/<任务>/plan.md` |
| 任务的测试与验收结果 | `work/active/<任务>/validation.md` |
| 当前进度与下一步 | `work/active/<任务>/handoff.md` |
| 历史会话原文 | Agent 自身的会话记录系统 |

> 任务文档记录过程，长期文档记录仍然有效的结论。方案一旦成为长期决策，就沉淀到 `docs/decisions/` 或架构文档。

## 任务目录命名

格式：`YYYYMMDD-<短横线短语>`，例如 `20261010-add-auth`。

- 以**日期 + 短语**为主键，避免多人 / 多分支并行时撞号。
- 需要人工排序时可在前面加顺序号（`2026-001-add-auth`），但冲突时**以日期 + 短语为准**，不要求全局唯一。
- 短语用小写英文、短横线分词，说明任务主题。

## Git 与 work/ 的关系

默认约定：**`docs/` 与 `work/` 都纳入版本控制**。只有进了 Git，"换 Agent / 换机器 / 隔几个月恢复"才真正成立。

为降低噪音与冲突：

- `work/active/<任务>/scratch/` **整个目录**加入 `.gitignore`，原始日志与临时脚本不入库。
- **不要**在仓库级忽略 `*.log`、`*.tmp`——那会误伤项目里需要跟踪的日志样本或测试夹具。
- 尽量**一个任务一个分支**（或一个 Agent 一个 worktree）；不要在多条分支上并行新建同名任务目录。
- 提交信息带上任务目录名，便于回溯。

若项目不用 Git：协议降级为"仅本地"——跨机器、跨 Agent 协作与历史追溯都会失效，需要显式接受这个代价。

## 任务目录的最小文件集

按复杂度选择，不要机械套全：

| 复杂度 | 至少包含 |
| --- | --- |
| 简单（改一行、小修） | `handoff.md` |
| 一般（加一个小功能） | `brief.md`（可合入 handoff）、`plan.md`、`validation.md`、`handoff.md` |
| 复杂（新模块、调研、跨模块改动） | `brief.md`、`analysis.md`、`plan.md`、`validation.md`、`handoff.md`，必要时加 ADR |

## `AGENTS.md` 应包含

`AGENTS.md` 是协议的**常驻入口**（Skill 可能不被触发，但 `AGENTS.md` 每次会话都会读）。它的四条铁律、必备内容与嵌套约定，见 [agents-md.md](agents-md.md)。模板见 `templates/AGENTS.md`，可用 `scripts/init-project.sh` 生成。
