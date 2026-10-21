# 语料清洗与状态机类来源 · 2026-10-21

**结论：语料干不干净，主要看从哪些仓库取样，不太看取样后的规则怎么写。** 从运行多年的分布式/状态机类系统里取带 bug 标签、按讨论数排序的 issue，人工抽样的真实缺陷率是 83%，写明根因的有 78%。原语料随机抽样是 60% 和 17%。规则分层能把原语料的 core 层提到约 75% 真缺陷，但改了一轮规则后精度没有再上升。

要支撑的决定：issue-lens 后续是继续扩大来源数量，还是收窄到高质量来源。放弃条件：如果新来源抽样的真实缺陷率不能明显高于原语料（约 60%），就停止扩充。结果：明显更高，**采用“收窄到高质量来源 + 规则分层”的方向**；规则分层本身停在当前版本，不再继续调。

## 做了什么

1. `s07_quality.py`：按标签、正文模板、👍、评论数、作者占比、重复标题把每条 issue 分成 core / usable / low / excluded，写入 `issue_quality` 表，原始记录不删。`s04_search.py --tier` 可以按层过滤。
2. `s02_fetch_issues.py` 新增 `--label`（只取某个 bug 标签）、`--sort comments`（按讨论数排序），并开始保存 `author_association`。
3. 新形态 `distributed`：17 个仓库（etcd、consul、nomad、cockroach、tikv、tidb、rocksdb、vitess、yugabyte、scylla、kubernetes、containerd、moby、nats、temporal、hashicorp/raft、openraft），每库取讨论最多的 400 条带 bug 标签 issue，共 4,281 条。命令见 [collect.sh](collect.sh)，日志见 [collect.log](collect.log)。
4. 5+1 个独立 reviewer 按同一份 [RUBRIC](RUBRIC.md) 各审 30 条，每条读正文、评论和关闭它的 PR。

## 抽样结果（每组 30 条）

| 样本 | 真实缺陷 yes | 根因 yes / partial | 有具体触发条件 | 涉及状态/时序 | 分层不认同 |
|---|---:|---:|---:|---:|---:|
| 原语料随机 | 18 | 5 / 9 | 19 | 2 | 14 |
| 原语料 core（v1 规则） | 23 | 10 / 12 | 24 | 9 | 7 |
| 原语料 core（v2 规则） | 24 | 19 / 8 | 25 | 12 | 8 |
| 原语料 excluded | 1 | 5 / 0 | 6 | 1 | 1 |
| 分布式·共识协调 | 25 | 24 / 6 | 28 | 13 | — |
| 分布式·数据库 | 26 | 24 / 5 | 29 | 17 | — |
| 分布式·编排运行时 | 24 | 22 / 5 | 25 | 18 | — |

逐条判断：`review_*.json`。v1 和 v2 两个 core 样本是分别抽的，不是同一批 30 条。

- **排除基本可靠**：被排除的 30 条里只有 1 条误杀（expo#11736 带 docs 标签的相机 bug），v2 规则已用 bug 模板修正。
- **core 精度停在约 75%**：误入 core 的主要是没有真正修复的关闭（维护者 wontfix、关闭 PR 没合并或只改了日志）、依赖升级、构建打包问题。只看已入库字段判断不了“关闭它的 PR 有没有修好”，这是规则的上限。
- **CI 自动开的测试失败单**（cockroach roachtest）：3 条里 2 条是测试自身的问题，但 cockroach#104709 是真实的 raft 提案泄漏缺陷，所以只降到 low，不排除。
- **样本偏差**：共识组的 30 条里 etcd 只有 2 条，没有 hashicorp/raft 和 openraft（这两个库一共只有 10 条），一半是 UI/CLI 问题。选举、快照压缩、成员变更这几类还没被抽样覆盖。编排组没有抽到 temporal。

## 学到的故障模式

- [共识协调](lessons_distributed_consensus.md)：旧角色后台逻辑残留、生命周期事件没传到订阅方、并发绕过限额、身份变更后沿用旧序号等 7 类
- [分布式数据库](lessons_distributed_databases.md)：领导权/成员变更残留旧状态、异步组件循环等待、在线 schema 变更时缓存/租约没失效、MVCC 墓碑与 GC 可见性、跨版本/崩溃的格式不兼容等 7 类
- [编排运行时](lessons_distributed_orchestration.md)：守护进程重启后状态不全、升级与版本偏斜、失败路径不回滚、锁和阻塞 I/O 竞态等 7 类

每类都写了机制、可迁移的测试思路和支撑的 issue 链接；reviewer 已标出哪些模式证据足（采用）、哪些只有一两条（待验证）。

## 未做 / 未知

- 分层没有读关闭 PR 的内容，所以“关闭但没修”的 issue 挡不住。要再提高 core 精度，只能按需抓 PR 证据（已有 `--with-pr-evidence` 的同类逻辑），没有做全库抓取。
- 分布式来源和六类显式来源都还没进公开语料快照。
- 样本由 `sample.py`（seed 20261021）和一次内联抽样（v2 core，seed 202610212，排除前两批已抽 id）生成；样本文件含 issue 正文，没有提交，抽样清单见 [samples.json](samples.json)。
