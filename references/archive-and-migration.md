# 归档检索与 1.x 布局迁移

## 归档查询

```bash
python3 /path/to/skill/scripts/archive-index.py /path/to/project --query "令牌 刷新"
python3 /path/to/skill/scripts/archive-index.py /path/to/project --status done --json
python3 /path/to/skill/scripts/archive-index.py /path/to/project --write
```

查询以当前 `work/archive/<任务>/` 下所有 Markdown 文档为来源，按任务名、分支和正文匹配全部关键词，不区分大小写。结果包含 handoff、文档路径与标题、Goal 摘要、状态及 updated。updated 是任务最后更新时间，不冒充完成时间；不存在的提交/PR 关联不推断，有关记录可写进 handoff 或 analysis 并全文检索。

默认查询不写文件，Markdown 输出链接以项目根为基准；`--json` 为脚本集成提供项目相对路径。`--write` 在 `.workflow/archive-index.json` 重建全部归档的可删除索引，包含可搜索正文。索引不人工编辑、不作为新的结论权威，也不进入 Git。查询始终读真实归档，避免旧索引造成漏查。保留 Markdown 的附件链接可从结果文档继续访问，二进制附件不做内容搜索。

scratch、.git 与符号链接不索引。缺 handoff、无效内容等情况输出提醒并退出 1，仍展示可读取任务，不能声称结果完整；输入/路径错误退出 2。归档根不存在时返回空集合。全文读取适合个人项目，不是海量文档搜索服务。

## 1.x 到 2.x 的保守迁移

```bash
python3 /path/to/skill/scripts/migrate-project.py /path/to/project
python3 /path/to/skill/scripts/migrate-project.py /path/to/project --personal-doc docs/guides
python3 /path/to/skill/scripts/migrate-project.py /path/to/project --personal-doc docs/guides --apply
```

没有旧 front-matter 映射时必须显式给出 `--tasks-root work --docs-root docs`，不根据目录名猜测。默认目标 `.agent`，可用 `--workflow-root agent-work` 改变；目标已存在、路径交叠、符号链接或未知任务内容会拒绝整次迁移。

- 自动识别 `tasks_root/active`、`tasks_root/archive` 中具有 handoff 的任务，连同证据、scratch 与其他任务材料迁到新 `work/`。
- docs_root 中的文档必须经 `--personal-doc <项目相对文件或子目录>` 选择，可重复；禁止直接选整个 docs_root，避免把混合的正式文档整库私人化。不选择也可只迁任务，正式文档留在项目原位。
- 原 reports/references 留在原位。它们在 1.x 可能是正式成品/共享输入，与新版个人草稿/工作副本不等价，不能整目录搬。
- 通用铁律及 Git 约定必须精确匹配已收录 1.x 模板（1.1.0—1.2.2）或当前目标模板；有自定义则先报冲突。自定义补充移入单独章节后再合并模板，不直接删掉。
- 更换 root 字段、迁移已识别通用规则并建立同步基线。项目定位、命令与其他章节保留；导航中的明确旧任务和选定个人文档路径重写，补充新工作区导航与未搬内容说明。

## 链接、索引与 Git

所迁 Markdown 中的常见行内链接/图片、引用式链接及项目相对路径代码引用会重定位：移动目标的链接指向新位置，未移动目标的链接根据新文件位置计算。外部 URL、绝对路径与锚点保留。复杂 Markdown/HTML、自定义脚本里的路径和非 Markdown 内容不自动解析；工具对可能受影响的项目外部 Markdown 入链只报告，正式文件仍由执行者审查后修改。

工具不会重新编造旧任务的 brief、plan、phase 或验证结果。迁移后须运行检查、补最小真实字段、确认归档状态，并重建归档索引。`check-project.sh --strict` 没通过时不得声称整个项目已完成验证，即使布局已搬迁。

被 Git 跟踪的旧文件会列在计划中；工具不改索引、不创建提交，应用后应审查旧路径删除，新工作流目录和入口按默认规则加入 gitignore。若入口原本被跟踪，仍需决定是否取消跟踪；个人目录不擅自推送到团队仓库。

## 应用与恢复边界

默认预览零写入。应用前再次核对源字节和 gitignore，保存 `.workflow/migration.json`，包含入口、所迁原件及旧 gitignore 内容，用于本次迁移事故恢复，不是跨机器整工作区备份功能。先写所有目标，再改入口与 ignore，最后核对并删除原文件；旧空目录保留。

普通写入失败会尽量恢复源文件、入口与 ignore，保留目标与记录供核查；不承诺断电事务，也没有通用迁移撤销命令。迁移后出现编辑时应逐文件对照记录恢复，不能整目录覆盖。全程遵守一个写者约定，不与其他 Agent 同时迁移。

本轮按用户决定暂缓“跨机器整工作区备份/恢复”。手动拷贝或临时调整 Git 忽略由使用者自行安排；升级/迁移保留的局部回滚原件继续保留。
