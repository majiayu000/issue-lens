# 五产品优化后测试方案（2026-10-02）

五份报告已生成，共 **60 条待评审、未执行的测试建议**，实际引用 41 条不同的历史 issue，并为这些来源保留 79 个不同关联 PR 的有界快照。关联不等于已修复，也不证明目标产品存在相同缺陷。

本批使用 Codex CLI 0.160.0 / `gpt-6.1-sol`，沿用上一批产品文档快照，并读取同一产品提交上的指定测试源码。语料仍是 2026-09-23 的本地快照；issue 提炼使用新的独立缓存，PR 证据本次实时获取。

## 结果入口

| 产品 | 建议数 | 实际引用 issue | 关联 PR | 未检出 / 部分覆盖 / 已有覆盖 |
|---|---:|---:|---:|---:|
| [rekey](rekey.md) · [JSON](rekey.json) | 12 | 6 | 10 | 4 / 8 / 0 |
| [remem](remem.md) · [JSON](remem.json) | 12 | 5 | 15 | 10 / 2 / 0 |
| [rclean](rclean.md) · [JSON](rclean.json) | 12 | 10 | 20 | 6 / 6 / 0 |
| [quotabar](quotabar.md) · [JSON](quotabar.json) | 12 | 11 | 18 | 3 / 8 / 1 |
| [dsh-desk](dsh-desk.md) · [JSON](dsh-desk.json) | 12 | 9 | 16 | 5 / 7 / 0 |

最后一列均为模型对所给测试文件的判断，不是全仓库覆盖率。未检出不等于没有测试，部分覆盖不等于已确认新增缺陷；已有覆盖的建议排在后面。PR 数只统计最终用例引用来源的已抓取快照，可能含无关的 fork 或包管理器更新，不能作为有效修复数量。

## 同模型对照

[rclean 完整对照与逐项判断](comparison/README.md) · [A：直接读 PRD](comparison/prd-only.md) · [B：加入历史材料](comparison/with-issues.md)

两组均为 12 条，核心风险高度重合。历史材料补充了子项目名称交换、年龄筛选后告警保留等具体边界，但没有证明整体更优；扫描根替换和混合恢复在基线中已经出现。加入材料也挤占了部分扫描入口覆盖。B 单次方案调用输入量约为 A 的 2.83 倍，尚不含前置检索、提炼和抓取成本。

## 固定输入与版本

| 产品 | 产品提交 | 提供的测试文件数 |
|---|---|---:|
| rekey | `e7b50943c154` | 4 |
| remem | `a3481d7d1c8c` | 4 |
| rclean | `05fec46f0713` | 5 |
| quotabar | `be367544f4b9` | 5 |
| dsh-desk | `99f0bdb7b217` | 3 |

文档、测试源码的完整路径、提交及 SHA-256 见 [输入清单](inputs/manifest.json)，原文保存在 inputs/ 下。报告里的绝对路径指向生成时的本地快照；查阅仓库副本时可按清单定位对应文件。这是有界源码审查，未运行这些产品的测试，也不代表评估了它们的最新发布版。

## 已完成的核对

- 五份报告的 PRD 哈希、需求逐字引文、历史 issue ID/URL/引文、测试源码哈希及唯一引文行号均已核对。
- 五个产品均实际调用 Codex，实际查询 GitHub PR，并完成基于 PR 证据的复核；所有状态保持 `draft_not_executed`。
- rclean 两个对照方案的模型、提示词哈希、需求主题、PRD 和测试文件一致；各使用一次新的生成，没有用旧版报告充当对照组。
- 生成器 47 项单元测试、Python 3.12 编译检查通过；包含真实启动器和子进程的超时终止回归测试。功能代码与超时清理修复已通过 GitHub CI。

运行中确实遇到过 180 秒超时、一次 300 秒超时、一次未正常完成的响应，以及一次测试引文不唯一；失败结果均未发布为正式报告。完成报告前进行了人工触发的重新生成，复用了本批已验证的提炼缓存；没有自动修补模型 JSON 或放宽引用校验。此次不能据成功产物声称全流程首轮通过率为 100%。

## 重跑示例

在仓库根目录，准备好语料库、Codex 登录和 GitHub 登录后运行；输出路径必须尚不存在：

```bash
ISSUE_LENS_LLM_ENGINE=codex ISSUE_LENS_MODEL=gpt-6.1-sol python3 s05_plan.py \
  --form cli --prd out/five-products-20261002/inputs/rclean.md \
  --tests out/five-products-20261002/inputs/tests/rclean/src/plan/tests.rs \
  --tests out/five-products-20261002/inputs/tests/rclean/src/clean/tests.rs \
  --tests out/five-products-20261002/inputs/tests/rclean/tests/graveyard_subcommands.rs \
  --tests out/five-products-20261002/inputs/tests/rclean/tests/cli/pipe_output.rs \
  --tests out/five-products-20261002/inputs/tests/rclean/tests/ignore_file.rs \
  --with-pr-evidence --out out/rclean-next.md
```

其他产品使用清单中各自的形态、文档和测试文件。模型输出有随机性，来源随时间变化；重复命令不能保证相同清单。与 [10 月 1 日旧样本](../five-products-20261001/README.md) 比较时，应保留当时没有测试源码与 PR 证据、没有固定同一模型的差别。
