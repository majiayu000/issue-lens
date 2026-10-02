# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是从同类产品历史问题迁移的测试建议，不是目标产品的已确认缺陷。

产品形态：cli；语料：16054 条；本次选入：12 条；测试建议：8 条。

来源只含 issue 标题与正文；没有读取关联 PR 补丁或评论。根因与适用性仍需人工复核。

## 需求与检索范围

- **R1 宿主集成与跨会话记忆：Claude/Codex 自动注入和总结；Cursor v1 仅 macOS/Linux MCP 安装及手动运行时能力，不要求自动捕获、会话注入或修复**：Start a new Claude Code or Codex CLI session after installation. remem should inject relevant project memory at session start and summarize durable memory after the session stops.
  检索词：installation, configuration, capture, restore；选入候选 2 条。
- **R2 搜索正确性：项目隔离、中英文检索、有限图扩展及内容去重**：- Entity-index and trusted typed-graph expansion (bounded 2-hop retrieval) - Project-scoped entity search (no cross-project leakage) - CJK segmentation support - Chinese-English synonym expansion - Title-weighted BM25 (\`bm25(fts, 10.0, 1.0)\`) - Content-hash deduplication via \`topic\_key\`
  检索词：search, isolation, tokenization, deduplication；选入候选 2 条。
- **R3 实验性上下文包：预算、来源和选择审计，投毒拦截与高风险弃答；查询嵌入仅本地，不要求稳定 API**：- The experimental MCP \`context\_bundle\` tool compiles a versioned, budgeted,   source-attributed SessionStart context bundle with a complete selection/drop   audit, including redacted poisoning-gate drops and canonical memory, session,   and preference preselection reasons. Poisoned session/workstream text is   rejected before it can steer implicit retrieval. High-risk requests return   only user-authored trusted memories and abstain when none survive. It requires   \`schema\_version: 1\`; its foreground query embeddings are local-only, ambient   reranking is disabled, retrieval weights are fixed to the bundle v1 policy   instead of ambient overrides, and the effective local embedding   provider/model/dimensions are fingerprinted into \`plan\_hash\`. The shape is   intentionally not yet a stable API commitment.
  检索词：poisoning, provenance, redaction, truncation；选入候选 2 条。
- **R4 记忆治理：抑制策略跨默认读取入口生效，保留源记录和显式审计；反馈默认不改变排序**：\`remem memory suppress\` applies a default-read policy without deleting the source row. Targets can be \`memory:&lt;id&gt;\`, \`claim:&lt;id&gt;\`, \`topic:&lt;key&gt;\`, \`entity:&lt;name&gt;\`, \`pattern:&lt;text&gt;\`, or a bare memory id/topic key. Default search, SessionStart context, profile-summary sources, preferences, lessons, current-state lookup, MCP search, and REST search exclude active suppressions. Use \`--include-suppressed\` on search when an audit needs to inspect suppressed evidence explicitly. \`remem why &lt;id&gt;\` reports whether the memory is currently suppressed and which policy matched it. \`remem memory feedback\` records \`relevant\`, \`not-relevant\`, \`harmful\`, \`stale\`, or \`too-noisy\` events without changing ranking by default.
  检索词：filtering, suppression, consistency, audit；选入候选 2 条。
- **R5 失败恢复：精确 ID 重试与隔离确认，归档恢复受单工作进程约束，失败或中断后仍保持隔离**：If the quarantined range has also archived, the pending command accepts \`--include-archived\` only for a dual-confirmation dry-run. The write must use the exact worker command with the same ID, both acknowledgements, and an explicit \`--profile\`. That worker refuses to write while another worker holds the singleton, atomically requeues and claims only the target task, and returns partial, failed, timed-out, or interrupted attempts to archived quarantine instead of exposing them to the ordinary daemon queue.
  检索词：retry, quarantine, concurrency, rollback；选入候选 2 条。
- **R6 原始会话读取：精确会话隔离、完整内容、快照分页和显式游标错误；查询只读，旧模式不自动迁移**：\`remem raw messages\` reads one exact \`(source\_root, project, session\_id)\` tuple without truncating stored content. It orders rows by \`(created\_at\_epoch ASC, id ASC)\`, defaults to 500 rows per page, and returns an opaque \`next\_cursor\` when \`has\_more\` is true. The first page freezes a maximum row ID; subsequent pages bind the cursor to the same selectors and snapshot, so concurrent appends do not create duplicates, omissions, or cross-session mixing. Invalid, stale, or selector-mismatched cursors fail explicitly; a missing tuple returns a successful empty envelope. \`raw search\`, \`raw sessions\`, \`raw messages\`, and \`raw reconcile\` open the current schema read-only, so a writer lock does not trigger migration contention and stale schemas fail with a migration diagnostic.
  检索词：pagination, snapshot, cursor, isolation；选入候选 1 条。
- **R7 CLI 脚本契约：列明支持的命令在 JSON 模式下仅向标准输出写入一个 JSON 对象**：These commands emit one JSON object and no human text on stdout when \`--json\` is set:
  检索词：serialization, stdout, parsing；选入候选 1 条。
- **R8 本地数据与接口安全：静态加密、目录和密钥权限、仅本机监听及令牌认证**：- SQLCipher encryption at rest (\`remem encrypt\`) - Data directory permissions (\`0700\`) - Key file permissions (\`0600\`) - REST API binds localhost only (\`127.0.0.1\`) and requires   \`Authorization: Bearer $(cat ~/.remem/.api-token)\` - API token file permissions (\`0600\`)
  检索词：encryption, permission, authentication, credential；选入候选 1 条。

## Cursor 安装恢复

### TC001 协调更新失败后恢复原有配置及文件缺失状态

对应需求：R1；状态：未执行。

前置条件：分别在 macOS 和 Linux 的隔离用户目录测试 Cursor v1 安装。；准备两组配置：两文件均存在且包含第三方条目；一个文件存在、另一个文件不存在。；保存安装前文件存在性及配置内容快照，具备阶段性写入故障注入条件。

1. 执行 remem install --target cursor，在一个配置文件已应用、后续配置应用尚未完成时注入写入失败。
2. 比较失败后 ~/.cursor/hooks.json 和 ~/.cursor/mcp.json 与安装前快照。
3. 移除故障并重新安装，检查 MCP 注册、第三方条目及能力提示。

**预期结果：** 补偿回滚恢复原有配置语义；本次操作新建的文件不作为残留配置保留。重新安装后注册 remem MCP，保留第三方条目，不注册 Cursor 自动捕获或 SessionStart hook，并显示 session-init: not supported on cursor。

迁移理由（模型建议）：原文证据指出备份中不存在路径时，回滚会吞掉 checkout 失败。迁移的是“部分更新创建了原先不存在的对象”这一恢复边界，适用于 PRD 明确的 Cursor staged apply 与补偿回滚；不将其视为跨文件原子事务，也不声称 remem 已存在同类缺陷。

- 来源：[career-ops-hq/career-ops — update-system rollback() should delete paths absent from backup branch](https://github.com/career-ops-hq/career-ops/issues/466)
  原文证据：\`update-system.mjs\` \`rollback()\` currently swallows checkout failures when a path was absent from the backup branch.

## 默认读取策略

### TC002 同一抑制策略在所有规定的默认读取入口生效

对应需求：R4；状态：未执行。

前置条件：准备可被检索、注入及相关派生读取入口引用的测试记忆和未抑制对照记录。；针对 memory、claim、topic、entity、pattern 及裸 ID/topic 目标分别准备能够匹配的样本。；Claude Code 或 Codex CLI 集成已配置，MCP 和本机 REST API 可用于读取同一测试存储。

1. 逐组应用 remem memory suppress，并记录被匹配的测试记录。
2. 分别通过默认 CLI 搜索、SessionStart、profile-summary sources、preferences、lessons、current-state lookup、MCP 搜索和 REST 搜索读取相关内容。
3. 比较各入口结果与未抑制对照记录，并检查源记录仍存在。

**预期结果：** 每个规定的默认读取入口均排除活动抑制策略命中的内容；对照记录在满足原有读取条件时仍可见；抑制不删除源记录。Cursor 不作为 SessionStart 注入测试宿主。

迁移理由（模型建议）：原文明确指出一个扫描入口没有应用用户黑名单。可迁移条件是共享排除策略接入多个读取入口时发生遗漏；这里只验证 remem 已规定的抑制入口，不复制 ATS 扫描功能。

- 来源：[career-ops-hq/career-ops — bug: scan-ats-full.mjs does not respect data/blacklist.md](https://github.com/career-ops-hq/career-ops/issues/1911)
  原文证据：\`scan-ats-full.mjs\` does not apply the user-owned company blacklist from \`data/blacklist.md\`.

## 抑制审计

### TC003 默认隐藏与显式审计能够读取同一源记录

对应需求：R4；状态：未执行。

前置条件：测试记忆已被活动抑制策略命中，且普通搜索条件能够匹配它。；保留该记忆的 ID、内容和抑制策略信息作为对照。

1. 执行普通搜索，再以相同条件添加 --include-suppressed 搜索。
2. 执行 remem why 查看该记忆的抑制状态和匹配策略。
3. 解除抑制后再次执行普通搜索，并比较源记录身份与内容。

**预期结果：** 普通搜索隐藏该记忆，显式审计搜索能够找回它；why 报告当前抑制状态及匹配策略；解除抑制后记录恢复默认可见性，源记录身份和内容未因抑制而被删除或替换。

迁移理由（模型建议）：黑名单未被某入口应用的直接证据支持检查过滤策略的一致性。本条将默认过滤与 PRD 自身规定的审计绕过配对验证；不把提炼结果中有关其他产品审计参数的描述当成原文已证实事实。

- 来源：[career-ops-hq/career-ops — bug: scan-ats-full.mjs does not respect data/blacklist.md](https://github.com/career-ops-hq/career-ops/issues/1911)
  原文证据：\`scan-ats-full.mjs\` does not apply the user-owned company blacklist from \`data/blacklist.md\`.

## 精确恢复

### TC004 多条失败范围并存时只恢复指定 ID

对应需求：R5；状态：未执行。

前置条件：准备多个可重试的失败 extraction range，记录各自 ID、关联任务和状态。；使目标范围既不是最旧记录，也不是列表中的第一条记录。；选择普通非隔离范围，避免将隔离确认流程混入本条。

1. 对目标 ID 执行 list-extraction-ranges --id &lt;目标ID&gt; --json。
2. 仅对该 ID 执行 retry-extraction-ranges 的 dry-run，再执行实际重试。
3. 再次查询目标及其他范围，核对关联 replay task。
4. 另以不存在的 ID 请求重试，检查其他范围是否发生变化。

**预期结果：** 预览、重试和查询始终指向指定范围及其关联任务，其他范围不被替代选中；不存在的 ID 不回退到相邻范围。若目标达到 replayed 终态，精确查询仍返回该范围及关联任务。

迁移理由（模型建议）：原文证据仅确认回滚结果变成 v1.3.0，而用户此前为 v1.7.0，不能据此认定具体排序根因。可迁移的是多恢复候选下恢复对象错误的风险；remem 的验收依据是显式 ID 契约，不是其他产品的最近备份选择规则。

- 来源：[career-ops-hq/career-ops — update-system.mjs rollback selects oldest backup branch, not most recent](https://github.com/career-ops-hq/career-ops/issues/733)
  原文证据：System files end up at v1.3.0 even though the user was on v1.7.0.

## 归档隔离恢复

### TC005 归档隔离恢复失败或中断后不遗留普通队列可领取任务

对应需求：R5；状态：未执行。

前置条件：准备一个已归档且已隔离的 extraction range，保存范围及任务初始状态。；没有其他 worker 持有 singleton。；具备分别模拟部分处理、处理失败、超时和中断的条件。

1. 使用目标精确 ID、--acknowledge-quarantine 和 --include-archived 完成 dry-run。
2. 使用相同 ID、两项确认和显式 --profile 执行 PRD 规定的 worker 恢复命令。
3. 分别注入部分处理、失败、超时和中断，每个变体使用独立夹具。
4. 查询同一 ID 的范围与任务状态，再启动普通 worker 检查是否领取该目标。

**预期结果：** 各异常变体均将目标保留或返回归档隔离状态，不使其暴露给普通 daemon 队列；精确查询仍能关联范围、任务状态及有界错误证据，其他范围不受影响。

迁移理由（模型建议）：原文涉及回滚对原先不存在路径的失败处理。迁移到 remem 的是部分执行后新增状态可能未被恢复流程收回的边界；数据库队列中的具体验收结果来自 PRD，此类迁移不证明二者具有相同根因。

- 来源：[career-ops-hq/career-ops — update-system rollback() should delete paths absent from backup branch](https://github.com/career-ops-hq/career-ops/issues/466)
  原文证据：\`update-system.mjs\` \`rollback()\` currently swallows checkout failures when a path was absent from the backup branch.

## JSON 输出

### TC006 所有列明的 JSON 命令在终端、管道及重定向中保持单对象输出

对应需求：R7；状态：未执行。

前置条件：按 PRD 的 Scriptable JSON output 表建立命令清单，为每个命令准备满足参数及状态要求的隔离夹具。；变更类命令使用独立数据，避免相互影响。；能够分别完整捕获 stdout 和 stderr。

1. 逐项执行清单中的 --json 命令，分别覆盖终端、管道和文件重定向。
2. 对完整 stdout 直接进行 JSON 解析，不预先裁剪横幅、日志或前后文本。
3. 检查解析结果为单个对象，并核对该命令在 PRD 表中列明的顶层字段。

**预期结果：** 各次成功调用的完整 stdout 均可解析为且仅为一个 JSON 对象，包含规定的顶层字段，没有人类提示、初始化横幅或进度文本混入。

迁移理由（模型建议）：原文直接说明 --json 的 stdout 混入横幅导致消费者解析失败。该触发条件与 remem 的脚本输出契约直接相关，但不要求 remem 使用 dotenv 或实现网页消费者。

- 来源：[career-ops-hq/career-ops — scan.mjs: dotenv v17 banner contaminates --json stdout, breaking JSON consumers](https://github.com/career-ops-hq/career-ops/issues/1906)
  原文证据：In \`--json\` mode the banner lands on the same stdout channel that is supposed to carry a single JSON object, so any consumer parsing that stdout fails.
### TC007 空结果及诊断型成功响应不混入人类提示

对应需求：R7；状态：未执行。

前置条件：准备正常可打开的测试数据库。；准备无匹配搜索词、不存在的记忆 ID、空 review inbox，以及能产生 skipped 条目的 user backfill 夹具。

1. 分别执行 search --json、show &lt;不存在ID&gt; --json、user review inbox --json 和 user backfill --json。
2. 完整捕获 stdout，直接解析并检查命令对应的稳定字段。
3. 检查空结果、found 状态或跳过原因是否表达在 JSON 字段中。

**预期结果：** 每项响应只输出一个 JSON 对象；空搜索和空 inbox 通过结果字段表达，show 使用 found 表达未找到，backfill 在规定字段中表达跳过原因，不额外向 stdout 打印说明文字。

迁移理由（模型建议）：同一 stdout 通道混入非 JSON 文本的证据可迁移到容易打印提示的空结果和诊断分支；具体结果字段以 remem PRD 为准。

- 来源：[career-ops-hq/career-ops — scan.mjs: dotenv v17 banner contaminates --json stdout, breaking JSON consumers](https://github.com/career-ops-hq/career-ops/issues/1906)
  原文证据：In \`--json\` mode the banner lands on the same stdout channel that is supposed to carry a single JSON object, so any consumer parsing that stdout fails.

## REST 认证

### TC008 Authorization 头缺失或错误时不能读取受保护接口

对应需求：R8；状态：未执行。

前置条件：本机测试 API 已启动，使用隔离环境中的测试令牌。；测试客户端能记录请求头是否存在，但不输出令牌内容。；选用 PRD 已明确的 health、status 和 search 接口。

1. 携带正确的 Authorization: Bearer 测试令牌请求三个接口，建立可访问对照。
2. 分别省略 Authorization、发送空 Bearer 值及发送错误测试令牌。
3. 比较响应状态和内容，确认未认证请求没有获得受保护数据。

**预期结果：** 正确 Bearer 令牌允许访问；缺失、空值及错误令牌均被明确拒绝，不返回受保护的状态或记忆数据。具体拒绝状态码不在本草稿中额外指定。

迁移理由（模型建议）：原文仅证实接收端未收到 Authorization 头，未证实根因。迁移的是认证头在请求链路中缺失的条件，用于验证 remem 服务端认证边界，不要求 remem 提供 n8n 凭据节点。

- 来源：[n8n-io/n8n — "Bearer Auth" Generic Authentication on the HTTP Request node does not work](https://github.com/n8n-io/n8n/issues/15261)
  原文证据：Observe incoming request in webhook.site does not contain an Authorization header at all.

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：仅覆盖 Cursor 协调安装的补偿恢复边界。Claude/Codex 跨会话注入与 Stop 总结、首次安装与自动发现、Claude repair、Cursor 手动 observe/summarize、平台跳过和 doctor 能力提示尚未充分覆盖。744546094 的原文是 NuGet 配置警告；4686806393 的引文仅描述空 shell、保留标题和缺少恢复记录，不能单凭提炼结果推导 remem 的自动更新或终端恢复要求，也不足以支撑跨会话记忆用例。
- R2：无充分相关原文证据，未生成案例。5038512351 仅泛述 Web research 配置体验不一致；4276056101 的证据是 push 完成前显示图标，均不能支撑项目隔离、中英文分词与同义词、有限图扩展、topic\_key 去重或排序正确性的历史触发条件。
- R3：无充分相关原文证据，未生成案例。5040170145 只说明其他产品缺少 memory HTTP 端点，5038512351 只描述 Web research 体验；不能支撑上下文预算、来源与脱敏审计、投毒拦截、高风险弃答、本地嵌入、固定检索策略、plan\_hash 或实际发出内容的审计重封装测试。
- R4：已有案例覆盖多入口默认抑制及显式审计，但反馈事件默认不改变排序、策略变更后的并发读取一致性等未充分覆盖。5186509797 的鼠标修饰键证据与记忆治理不相关，不能用来补齐缺口。
- R5：已有案例覆盖恢复对象身份及失败后的隔离状态，但 singleton 竞争拒写、缺失确认参数、--id 与批量过滤参数冲突、普通隔离重试限制及完整原子状态转换尚未充分覆盖。两条历史证据来自文件回滚，不能视为数据库并发或隔离机制的直接故障证据。
- R6：未生成案例。4370092094 的证据描述编辑后替换回合并重新运行，不涉及只读归档的快照分页；不能向 remem 引入 /edit、/undo 或历史截断功能。精确会话隔离、完整内容、排序与并发追加分页、非法/过期/错配游标、空元组、写锁下只读及旧模式迁移诊断均缺少相关历史证据。
- R7：案例覆盖列明命令的成功输出、空结果及诊断型成功响应；启动失败、数据库错误和参数错误时的退出码、stderr 与 JSON 行为未充分覆盖。PRD 未统一规定所有失败路径的 JSON envelope，不能自行指定失败必须返回何种对象。
- R8：仅覆盖 Bearer 认证头缺失和错误。SQLCipher 静态加密、数据目录及密钥/令牌权限、仅绑定 127.0.0.1、SQLite 调优约束和明文残留诊断缺少相关历史证据；3052592385 不能证明这些安全边界存在问题。
- 待确认：编译偏好规则明确提到 GH-671 尚未关闭，精确的全局所有者过滤和完整资格矩阵仍由 \#813 承担；本轮可验收的过滤规则和资格边界是什么？
- 待确认：安全控制台功能要求已发布的 v0.6.6 及精确能力/端点映射，原文未提供已发布证据；本轮被测版本是否满足条件？不能仅凭 unreleased 源码清单将这些功能认定为已发布要求。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
