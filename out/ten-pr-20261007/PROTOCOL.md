# 固定 10 PR 对照协议

执行范围是 10 个不同项目的真实修复 PR，不以 rclean 旧结果替代。使用现有 Issue Lens 的 diff 需求筛选、FTS/模型检索、提炼、关联 PR 证据、方案提示词与引用检查。仅添加薄实验脚本，不扩语料，不新增评测服务。

## 固定条件

- Issue Lens：`cb5163970ea7d3ccc41a62207e4bbc390bb1d303`；公开 corpus-2026-10-03 下载校验通过，31,084 条，SQLite integrity_check=ok。原库只读。
- 每个 PR 的实际 head SHA、完整 diff 和哈希，以及提供的文档、生产代码、测试源码均冻结在 `*.input.json`；真实 native checks 使用同一 head 的完整文件。
- 文档/代码/测试的实际提供范围见 `input-audit.json`：README 上限18,000字符；单个代码/测试文件前60,000字符，完整diff保留。全文哈希与提供片段哈希分开核对；未提供的尾部不能认定没有覆盖。技术复核读取同一head的完整文件。
- 同一个 `gpt-6.1-sol` 请求、Codex CLI 0.160.0、同一 PLAN_PROMPT；不自动换模型。CLI 成功回执提供 requested_model、thread_id、usage，不提供独立验证的供应商底层模型身份。
- 需求筛选只调用一次，两个组共享其结果。A 提供文档、PR说明、diff、代码、指定测试；B 只额外提供历史 sources。模型只分析供应文本，无 shell/browser/tools。两组共同输入和提示词哈希须一致。
- 用既有 retrieve/extract_batch/attach_pr_evidence 流程，最多三个历史来源。目标项目排除；issue 创建时间必须早于目标 PR 合并时间。新抓 PR/评论仍可能晚于目标 PR，当前快照不能冒充历史时间点信息。
- 每个 PR 各一次有效 A/B 生成。按 PR 号奇偶交替调用次序，减少总是后调用 B 的缓存/时段偏差；这是确定性次序，不是随机试验。实际失败、手动重跑和无需求/无历史结果都保留。
- 这是根据可在当前 macOS、Python 环境执行测试的公开 merged fix PR 选择的十项目便利样本，不代表所有语言、桌面设备或未合并 PR。PR 自带测试可使大量建议已有覆盖；不能把成功测试认作发现新缺陷。

## 判断和执行

逐建议保留：是否适用、已有覆盖引用、执行方法、native 结果、是否发现问题、是否新增测试、误报/无关理由，以及维护者是否采纳、实际有效、评价耗时。模型自己的 coverage 是待复核推断。技术执行者判断与真实维护者评价分开；未获人类评价时，采纳率、有效采纳数、维护者额外审查时间保持空值。

原生 pytest/unittest 文件先复核 PR 的真实行为，再由执行者检查两组可迁移建议；临时新增检查只放到该项目的独立 clone。只验证当前 diff；对平台专属场景记录受限，不伪造设备验收。真实缺陷要求可观察失败和独立复现，不以历史 issue 或模型推理替代。

成本记录包含每个阶段的实际秒数、Codex usage、失败调用数与缓存边界。调用耗时不等于人类审查耗时。订阅额度与实际账单/单价无法从回执得到，不编造美元费用；前置检索/提炼/抓证据须另算，不能只报告 A/B 单次方案 tokens。

## 复跑

准备已校验语料、Codex 登录和只在环境中的 GitHub 凭据。提供新的输出目录：

```sh
ISSUE_LENS_LLM_ENGINE=codex ISSUE_LENS_MODEL=gpt-6.1-sol \
python3 experiments/ten_pr_comparison.py \
  --inputs out/ten-pr-20261007 \
  --db /absolute/path/issues.db --out /absolute/path/new-run
```

单样本重跑附 `--sample pallets--click`，仍必须用新的输出目录。输出目录已经存在时拒绝覆盖；阶段失败返回非零并留下 status.json，失败的配对不能参与收益统计。重新生成具有随机性，不保证相同建议。获取样本和原生测试命令、环境版本保存在报告的 acquisition/native evidence。
