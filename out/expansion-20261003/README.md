# 从历史案例到实际回归测试：2026-10-03

本次实际运行 rclean 的 5 个场景，最终全部通过，没有发现新的产品缺陷。其中 2 个场景复核已有核心行为，3 个补充边界已写成 rclean 原生 Rust 测试，见 [PR #418](https://github.com/majiayu000/rclean/pull/418)。这说明部分历史建议可以落实为具体回归检查，不构成整体优于直接阅读代码的证明。

## 实测结果

测试基于 rclean 主分支 `3ea1704d05363c67b46b4e7619eeb02a3400862d`，在独立检出中用 Rust 1.95.0 编译，运行平台为 macOS。Python 接受测试使用该提交的真实二进制，并为每条场景创建独立的 HOME、配置、缓存和 graveyard 临时目录。二进制 SHA-256、版本、命令和退出码保存在 [rclean-results.json](rclean-results.json)。

| 场景 | 历史来源 | 对当前代码的判断 | 实际结果 |
|---|---|---|---|
| 子项目交换名称后，根忽略文件仍按正确作用域排除候选；额外不匹配 glob 不干扰结果 | [ripgrep #3376](https://github.com/BurntSushi/ripgrep/issues/3376) | 补充组合边界，已提交新测试 | 通过 |
| 年龄过滤移除全部候选后，保留非法忽略文件造成的不完整告警 | [career-ops #2495](https://github.com/career-ops-hq/career-ops/issues/2495) | 已有大小过滤告警测试；补充年龄过滤 | 通过 |
| `free` 空间不足已确定退出码 3 时，下游断管仍保留 3 | [rtk #1004](https://github.com/rtk-ai/rtk/issues/1004)、[zx #640](https://github.com/google/zx/issues/640) | 已有短缺和断管的分开测试；补充组合条件 | 通过 |
| 恢复目标已存在时，拒绝覆盖，目标文件和存储中的原内容都保留 | [career-ops #995](https://github.com/career-ops-hq/career-ops/issues/995) | 已有核心恢复冲突测试；本次额外核对数据 | 通过 |
| `restore --dry-run --to` 不创建目标父目录，不改变 payload 或 manifest | 当前产品恢复契约及同批恢复建议 | 已有同等核心测试，复核通过，没有重复提交 | 通过 |

“补充边界”依据当前仓库相关测试源码审查，不是形式化证明整个项目此前不可能覆盖该行为。三个新增 Rust 测试见 PR 提交 `de3cf66f8c81efff333b8645c46212cc5f9ec394`。没有修改 rclean 生产逻辑。

首次夹具曾错误地把 `.rcleanignore` 放在子项目中，并期望父级扫描自动读取它。运行时两个子项目都被列出；检查当前 README 和 `src/scan/mod.rs` 后确认，产品只承诺读取扫描根的忽略文件。因此这是假设不适用，不是产品缺陷。已将测试改为根目录的明确路径规则，保留 [首次运行记录](rclean-initial-results.json)。没有通过放宽断言掩盖产品失败。

[可复跑脚本](../../experiments/rclean_acceptance.py) · [使用方法](../../docs/using-issue-lens.md)

## 已实现的利用入口

- `s05_plan.py --diff`：根据明确代码改动筛选需求和历史案例，生成 3–5 条优先测试建议；需求引文仍来自产品文档。无相关要求的改动会返回待确认说明，不编造用例。
- `s06_curate.py`：按 AND 关键词及指定来源挑选记录，利用既有提炼区分 bug、feature、question、unclear，再按触发机制归组。原始数据不删除，排除项和未分析数量保持可见。
- `--with-pr-evidence`：优先抓取当前关闭事件的 PR，再取显式关闭候选；不再把任意 fork、Homebrew 更新等交叉引用当成首选修复。附带最近 8 条评论，保留截断标志。
- `s02_fetch_issues.py --repos`：按实际功能补充指定来源，不受 topic 热度名单限制。

## 新增来源和公开数据

| 来源 | 用途 | 本次新增 | 查询总量 |
|---|---|---:|---:|
| restic/restic | 备份恢复、目标冲突、恢复中断 | 100 | 609 |
| rclone/rclone | 文件复制、同步和路径行为 | 100 | 476 |
| electron-userland/electron-builder | 安装、升级和更新器状态 | 100 | 981 |

仍使用 closed + linked:pr + reason:completed 的查询，并按热度截取；这些条件不等于全部是 bug。全库现为 **82 个仓库、31,084 条 issue**。原 79 库保持 9 月 23 日快照，并非本次重新抓取。

[完整在线目录](../corpus/README.md) · [新版 SQLite/JSONL 数据包](https://github.com/majiayu000/issue-lens/releases/tag/corpus-2026-10-03)

公开包保留全部记录，其中 25 条正文因疑似凭证格式遮盖，原文链接仍在。模型缓存不随原始语料发布。

## 真实证据抓取与模型调用状态

[evidence-samples.json](evidence-samples.json) 保存 5 条 issue 的真实 GitHub 证据抓取结果，共 8 个 PR 引用、23 条有界评论。包括 GitHub CLI 的真实关闭 PR、ripgrep 的显式关闭候选，以及新来源 restic/electron-builder 的讨论。关闭关系不等于已验证根因；评论和补丁均有数量或长度上限。

两次新的自动案例整理调用均失败，没有生成成功报告：当前本机 Codex CLI 为 0.156.1，已登录 ChatGPT，但服务明确返回 `gpt-6.1-sol` 不受该账户支持。没有自动换模型，也没有把人工整理或测试替身充当真实模型结果。待明确允许切换后，使用已经实现的命令重跑恢复和更新器两个任务，并运行按 diff 的端到端样例。

按 diff 的真实输入已保存在 [inputs](inputs/)：来自 rclean 已合并提交 `a74990d` 的 `src/free.rs`、`src/stdio.rs` 改动及同提交 README、测试文件。这些输入不是自动生成报告，暂不声称该完整模型流程实测成功。

## 已完成验证

- issue-lens：58 项离线单元测试和 Python 编译检查通过；涵盖 diff 传递、无关改动、分组遗漏/重复 ID、来源筛选、GitHub 关闭关系和 HTTP 200 中的 GraphQL 错误。
- rclean：5 项真实二进制接受测试通过；13 项 ignore 测试和 4 项 pipe 测试通过；fmt 和全目标 clippy 通过。
- rclean [CI](https://github.com/majiayu000/rclean/actions/runs/37047958067)：Ubuntu、macOS、Windows，以及 Rust 1.95 MSRV 检查全部通过，包含完整测试和 release build。PR 已准备好审阅，尚未合并。
- 82 个在线索引页面、31,084 条唯一链接与公开 SQLite/JSONL 逐条对应；数据库完整性和 FTS 内容一致性检查通过。
