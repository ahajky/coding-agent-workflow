# Git 工作流（最小基准）

> 这一层只放**任何项目都必须遵守**的 Git 约束。
> 项目特有的部分——远程 PR 流程、发布节奏、hotfix、评审人制度、额外的提交类型——写在项目自己的 `AGENTS.md` 或 `docs/guides/` 里，**不要改这份基准**。
>
> 判断标准：任何 Git 约定，如果不能让"换个 Agent / 隔几个月回来"更容易恢复状态，就不该写进这里。

## 1. 什么进 Git

| 内容 | 进 Git | 说明 |
| --- | --- | --- |
| `docs/` | 是 | 长期知识，是恢复状态的主要依据 |
| `work/active/<任务>/` 的文档 | 是 | `brief.md` / `analysis.md` / `plan.md` / `validation.md` / `handoff.md` |
| `work/active/<任务>/scratch/` | 否 | 整目录 gitignore，随时可删 |
| `work/archive/<任务>/` | 是 | 归档本身就是一次提交 |
| `reports/` `references/` `src/` `tests/` `scripts/` | 是 | 大体积、二进制、含真实数据的走 gitignore，并在原地注明去向 |

- **不要在仓库级忽略 `*.log` / `*.tmp`**：会误伤需要跟踪的日志样本与测试夹具。
- **密钥、凭证、客户数据不入库。** 进了历史就等于泄露——删文件、回滚提交都不解除风险，必须轮换。

## 2. 分支

- **一任务一分支**（或一 Agent 一 worktree）；单文件小修、纯文档改动可以直接做在 `main` 上。
- 命名 `<type>/<任务目录名>`，例如 `feat/20261016-add-auth`。日期是任务主键的一部分，不是随手加的。
- 开了分支就把名字写进 `handoff.md` 的 `branch` 字段。
- 不要在多条分支上并行新建同名任务目录；分支合并回 `main` 后删除。
- 并行时用 worktree 隔离，放在项目同级目录：

```bash
git worktree add ../<项目名>-<任务目录名> -b feat/<任务目录名>
```

## 3. 提交

- **小步提交**：一次可独立验证的改动一个提交，一个提交只做一件事。
- 格式：`<type>(<任务目录名>): <说明>`。`type` 默认取 `feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `perf`。
- 直接做在 `main` 上的小修，括号里换成模块名（`fix(auth): ...`）。
- **`handoff.md` 随本次工作的提交一起带上**，不要收工后留在工作区。

## 4. 两条安全线

- **不改写已推送或共享的历史**：不 `rebase`、不 `commit --amend`、不 `push --force`。没推送的本地分支随便整理。
- **合并用 `merge`**（`git merge --no-ff <分支>`）；冲突时先读双方意图再合并，拿不准就保留双方并询问，不要擅自丢弃别人的逻辑；**不要用 `reset --hard` 丢改动**。

## 5. 归档

```bash
git mv work/active/<任务> work/archive/<任务>
git commit -m "chore(archive): <任务目录名>"
```

单独提交，让"任务结束"在历史里可查；合并、归档完成后删分支。

## 6. 项目自己的扩展

基准之上，项目按需要加约束。落地位置只有两个：

- 项目 `AGENTS.md` 的「Git 约定」一节——Agent 每次会话都会读，适合放**必须遵守**的补充；
- `docs/guides/`——适合放更长、更具体的操作说明。

常见的扩展方向（按需取用，不必都写）：

| 场景 | 典型补充 |
| --- | --- |
| 有远程、多人协作 | `main` 开保护、走 PR、至少 1 人批准、作者不自审 |
| 有对外交付 | tag 标发布、`CHANGELOG.md`、SemVer 规则 |
| 线上紧急修复 | `hotfix/` 从 `main` 切、修完合回并补 `validation.md` |
| 多人并行集成 | 增设 `develop` 缓冲分支，把本文的 `main` 换成它 |
| 已有团队提交规范 | 扩展 `type` 取值、`scope` 约定、footer 格式（如 issue 编号） |

扩展的底线：**不能违背第 1 节（入库范围与红线）和第 4 节（不改写历史、不改丢改动）**。其余都可以按场景调整。

## 7. 校验

| 检查项 | 谁做 |
| --- | --- |
| 是否在 Git 仓库里；不在则降级为"仅本地" | `check-project.sh` |
| `.gitignore` 是否覆盖 `work/active/*/scratch/` | `check-project.sh` |
| `handoff.md` 的 `branch` 是否指向存在的分支 | `check-project.sh` |
| `handoff.md` 是否有未提交的改动（收工没提交） | `check-project.sh` |
| 最近一次提交的信息格式 | `check-project.sh`（只提醒） |
| 提交前自动跑以上检查 | 可选：`scripts/install-git-hooks.sh` |

## 8. 不用 Git 的项目

协议降级为"仅本地"：跨机器、跨 Agent 协作与历史追溯都会失效。需要显式接受这个代价，`handoff.md` 的 `branch` 留空或写 `none`；第 2–5 节不适用。
