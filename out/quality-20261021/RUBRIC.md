# 抽样核对标准（所有 reviewer 共用）

每条 issue 输出一个 JSON 对象：

| 字段 | 取值 | 判断 |
|---|---|---|
| `id` / `url` | 原样 | |
| `is_real_defect` | yes / no / unclear | 产品实际行为违背文档、契约或合理预期，且已被修复。功能请求、提问、文档、纯测试基础设施、依赖升级、用户误用 = no |
| `has_root_cause` | yes / partial / no | issue 正文、评论或关闭它的 PR 是否说明了**机制**（为什么会错），而不只是症状 |
| `has_trigger` | yes / no | 是否给出能构造测试的具体触发条件（输入、时序、配置、故障注入） |
| `state_machine` | yes / no | 缺陷是否涉及状态转换、顺序、并发、重试/超时、恢复、成员或版本变更 |
| `tier_agree` | yes / no / n/a | 是否同意样本里 `tier` 字段的分层（只在 baseline 样本里填） |
| `lesson` | 字符串或 null | 一句可迁移到同类产品的测试思路（中文），没有则 null |
| `evidence` | 字符串 | 支撑判断的一句原文短引（<=20 词）或 PR 链接 |

规则：
- 先读样本 JSON 里的正文（已截断到 4000 字符）。正文不足以判断根因时，可以用 `gh issue view <url> --comments` 或 `gh pr view` 读关闭它的 PR，每条最多两次调用。网络失败就按已有信息判断，写 unclear，不要编造。
- 只读：不评论、不提交、不改任何仓库或数据库。
- 判断依据要能被别人复查；拿不准就写 unclear，不要凑数。
