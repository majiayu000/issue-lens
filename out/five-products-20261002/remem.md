# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是依据 PRD 和同类产品历史问题生成的测试建议，不是目标产品的已确认缺陷。

产品形态：cli；语料：16054 条；本次选入：5 条；测试建议：12 条。

基础用例来自 PRD，历史启发用例附 issue 来源。PR 证据按来源单独标注；未采集评论。

已有覆盖只指所提供测试文件中的源码断言，未执行测试；未检出不等于全仓库无覆盖。

## 需求与检索范围

- **R1 Cursor 安装仅限 macOS/Linux：校验配置、保留外部条目并补偿回滚；不启用自动捕获、会话初始化或修复**：\`--target cursor\` (macOS/Linux) manages only the user-level \`~/.cursor/hooks.json\` and \`~/.cursor/mcp.json\`: it registers the remem MCP server, strictly validates both files, and preserves foreign entries semantically for the validated snapshot (coordinated updates use staged apply with compensating rollback, not a cross-file atomic transaction, and edits landing between the final comparison and the rename can still be lost). Install contract v1 registers no Cursor hook entries — automatic Cursor memory is not enabled — and \`session-init\` is not supported on Cursor. \`--target auto\` includes Cursor only when a Cursor config is detected on macOS/Linux; Windows is skipped with a diagnostic because no hook command renderer is approved there, and \`--repair\` does not cover Cursor. Before downgrading remem, run \`remem uninstall --target cursor\` with the current version first.
  组合检索：config AND rollback OR install AND unsupported OR config AND concurrent AND overwrite；选入候选 2 条。
- **R2 实验性上下文包阻止投毒影响检索，高风险请求仅使用可信用户记忆；固定版本、预算与本地嵌入策略**：- The experimental MCP \`context\_bundle\` tool compiles a versioned, budgeted,   source-attributed SessionStart context bundle with a complete selection/drop   audit, including redacted poisoning-gate drops and canonical memory, session,   and preference preselection reasons. Poisoned session/workstream text is   rejected before it can steer implicit retrieval. High-risk requests return   only user-authored trusted memories and abstain when none survive. It requires   \`schema\_version: 1\`; its foreground query embeddings are local-only, ambient   reranking is disabled, retrieval weights are fixed to the bundle v1 policy   instead of ambient overrides, and the effective local embedding   provider/model/dimensions are fingerprinted into \`plan\_hash\`. The shape is   intentionally not yet a stable API commitment.
  组合检索：context AND poisoning OR retrieval AND untrusted AND abstain OR embedding AND local AND override；选入候选 0 条。
- **R3 当前真相诊断只读且不输出声明文本，统一查询快照；历史截点不可重建时警告退出**：The diagnostic summarizes current results, surfaced conflicts and abstentions, supersedes links, non-current or dangling claim references, and the explicit stored-status to lifecycle mapping. It does not print claim text and never migrates or writes the database. \`--project\` accepts an exact stored project key; otherwise \`--cwd\` (or the current directory) is normalized to the project key. \`--subject\` accepts an exact memory topic key, a bare user-claim key, or its explicit \`type:key\` form. Warnings exit with status 1, including in quiet mode. The selector also scopes lifecycle counts; object kinds without a matching subject identity are omitted from a subject-focused report. When \`--as-of-epoch\` is omitted, the report samples one effective epoch, returns it as \`as\_of\_epoch\`, and uses it for every projection and diagnostic query in the same read snapshot. Every explicit historical cutoff is reported as unreconstructable and exits with a warning until versioned lifecycle history can prove in-place status changes.
  组合检索：snapshot AND inconsistent OR diagnostic AND write OR historical AND warning AND exit；选入候选 1 条。
- **R4 捕获流水线按会话合并提取任务，重试保持事件身份；投影失败原子回滚以防重复**：The capture pipeline starts with an append-only ledger: \`captured\_events\` stores raw hook/session evidence, \`event\_blobs\` keeps large payloads out of prompt-sized rows, and \`extraction\_tasks\` coalesces work by host/project/session instead of creating one LLM job per tool call. Curated memory remains the promoted output of this pipeline, not the raw event itself. Compatibility \`events\` projections share the canonical captured-event identity: a hook retry reuses the same projection, while a projection failure rolls back the capture and extraction task together so replay cannot create duplicates.
  组合检索：retry AND duplicate OR projection AND failure AND rollback OR queue AND backlog AND coalescing；选入候选 1 条。
- **R5 用户资料 Markdown 导出默认保护敏感及失效声明，拒绝覆盖文件；审计需明确启用相应门控**：\`remem user profile export --format markdown\` writes a derived, read-only snapshot of the user profile remem would use. Without \`--output\` it prints to stdout; with \`--output profile.md\` it creates a new file and refuses to overwrite existing content. The snapshot names the SQLite database as the source of truth, includes owner/project metadata, active summary provenance, source ids, and active default-eligible claims. Default output excludes suppressed, deleted, expired, future, personal, sensitive, and restricted claims. Use \`--include-suppressed\`, \`--include-sensitive\`, \`--include-inactive\`, \`--include-deleted\`, and \`--include-manual-summaries\` only for explicit audit; audit rows are labeled with exclusion reasons and text remains redacted unless all applicable audit gates are enabled.
  组合检索：export AND overwrite OR export AND sensitive AND leak OR audit AND redaction AND bypass；选入候选 0 条。
- **R6 原始消息按精确会话完整读取，游标绑定快照与选择条件，防止并发追加造成重复、遗漏或串会话**：\`remem raw sessions\` groups rows by source root, project, and session ID, and reports total, user, and assistant message counts; it can include the first N user-message samples per session. \`remem raw messages\` reads one exact \`(source\_root, project, session\_id)\` tuple without truncating stored content. It orders rows by \`(created\_at\_epoch ASC, id ASC)\`, defaults to 500 rows per page, and returns an opaque \`next\_cursor\` when \`has\_more\` is true. The first page freezes a maximum row ID; subsequent pages bind the cursor to the same selectors and snapshot, so concurrent appends do not create duplicates, omissions, or cross-session mixing. Invalid, stale, or selector-mismatched cursors fail explicitly; a missing tuple returns a successful empty envelope. \`raw search\`, \`raw sessions\`, \`raw messages\`, and \`raw reconcile\` open the current schema read-only, so a writer lock does not trigger migration contention and stale schemas fail with a migration diagnostic.
  组合检索：pagination AND duplicate OR cursor AND invalid OR snapshot AND concurrent AND missing；选入候选 0 条。
- **R7 安全 Web 接口提供可审计的幂等审核及精确归档恢复，不提供永久删除；客户端须校验发布与能力映射**：Source version \`0.6.6\` implements the GH-880 safe console API: candidate detail/evidence and idempotent safe review, five independently gated safe read resources, and recoverable memory archive/restore. Installed clients must wait for a published \`v0.6.6\` release and require the exact capability/endpoint-map bundle; the staged \`unreleased\` source manifest is not release evidence.
  组合检索：review AND duplicate OR restore AND stale OR capability AND endpoint AND mismatch；选入候选 0 条。
- **R8 明文残留诊断按内容只读扫描，禁止跟随符号链接及 Windows 重解析点；不完整检查不得报正常**：The \`Plaintext residue\` check in \`remem doctor\` recursively inspects regular files throughout the managed \`REMEM\_DATA\_DIR\` tree by content, including custom backup outputs with arbitrary names or no extension. It never follows symlinks and, on Windows, rejects every filesystem reparse point before recursive descent. A file shorter than the SQLite header inside the managed \`backups/\` subtree is reported as an incomplete inspection; unrelated short operational files elsewhere are ignored unless their names identify them as database artifacts. Configured key and live-database sidecar paths retain their existing exclusions. A strictly validated internal Hugging Face cache snapshot pointer is omitted because its same-repository blob is a regular file that the tree scan inspects independently; any other artifact symlink makes the inspection incomplete. The check is read-only and never deletes data. When it finds a plaintext copy while the live database is confirmed encrypted, it reports \`Fail\` and \`remem doctor\` exits with code 2. If the live database is plaintext or its encryption state cannot be confirmed, the finding is \`Warn\`. An entry or candidate file that cannot be inspected because of an I/O error is reported and prevents the check from reporting \`Ok\`.
  组合检索：symlink AND scan OR inspection AND error OR plaintext AND encrypted AND exit；选入候选 1 条。

## 潜在遗漏（所给文件中未检出）

### TC001 Cursor 安装保留外部条目，并遵守 v1 能力限制

对应需求：R1；分类：安装与平台边界；状态：未执行。

增量价值（模型判断）：所给 remem 测试未发现 Cursor 配置保留、重复安装、自动检测及能力限制的同等覆盖；新增这些实际配置行为检查。

前置条件：macOS/Linux 隔离用户目录已有合法 hooks.json 和 mcp.json，包含第三方 hook、MCP 服务及合法扩展字段；保存解析后语义快照。；另备有、无 Cursor 配置的 macOS/Linux 自动检测夹具，以及 Windows 自动检测夹具。

1. 执行 remem install --target cursor，比较两个用户级配置文件与快照，然后重复安装。
2. 运行 remem doctor，检查 Cursor 状态及能力提示。
3. 分别在有、无 Cursor 配置的 macOS/Linux 环境执行 --target auto；在 Windows 环境执行 --target auto。
4. 在隔离环境执行安装 repair 路径，比较 Cursor 配置变化。

**预期结果：** 显式 Cursor 安装注册 remem MCP，第三方条目语义保留，重复安装不产生重复注册；不新增 remem Cursor hook，不启用自动捕获或 session-init。install 和 doctor 均输出 session-init: not supported on cursor。auto 仅在 macOS/Linux 检测到 Cursor 配置时纳入 Cursor；Windows 跳过 Cursor并给出诊断。repair 不修复 Cursor 配置。

迁移理由（模型建议）：迁移注册或重建配置时丢失既有设置的触发条件，不引入 OpenHands 的模式快照功能。该来源是功能请求；其配置保留 PR 未合并，只能作为提案材料。提供的模式切换测试断言模型恢复或 MCP 整体替换，不等于 remem Cursor 安装的外部条目保留测试。T4 仅测试 npm 二进制安装辅助逻辑。

- 来源：[OpenHands/OpenHands — ACP settings: preserve LLM/condenser/MCP config across OpenHands ↔ ACP toggles](https://github.com/OpenHands/OpenHands/issues/14370)
  原文证据：\*\*The LLM dropdown is empty. Condenser is back to default. MCP servers are gone.\*\* User must re-enter everything.
  关联 PR：[fix(settings): stop one member's agent settings reconfiguring the org](https://github.com/OpenHands/enterprise/pull/241)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[feat: preserve LLM/condenser/MCP config across OH ↔ ACP kind toggles](https://github.com/OpenHands/OpenHands/pull/14453)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[feat(acp): minimal generic ACP agent UI](https://github.com/OpenHands/OpenHands/pull/14401)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。
### TC002 双文件严格校验失败拒写，阶段应用失败补偿恢复

对应需求：R1；分类：安装失败恢复；状态：未执行。

增量价值（模型判断）：新增双文件预校验、部分应用后的补偿恢复及恢复后重试检查；提供的 remem 文件未发现同等断言。

前置条件：使用 macOS/Linux 隔离目录，保存 hooks.json、mcp.json 的内容和存在性。；准备分别使其中一个文件不符合严格校验的夹具，以及两个文件均合法的夹具。；具备阶段应用故障注入能力；本用例保证补偿操作本身可以完成。

1. 分别使用非法 hooks.json、非法 mcp.json 执行 Cursor 安装，比较两个文件。
2. 恢复合法配置，在一个文件已应用修改后，对后续文件应用注入写入或重命名失败。
3. 检查错误结果和两个文件的恢复状态。
4. 解除故障并重新安装，检查最终 MCP 注册与第三方配置。

**预期结果：** 任一配置校验失败时不应用配置变更并报告错误。阶段应用失败后，通过补偿恢复安装前两个文件的内容和存在性；解除故障后重试不会继承半成品配置。验收不要求跨文件原子事务，也不要求消除 PRD 明示的最终比较至 rename 间并发覆盖窗口。

迁移理由（模型建议）：迁移配置激活收尾失败后保持先前有效状态的故障边界，不复制设备登录功能。issue 提炼未确定根因；PR 正文关于悬空凭据指针的说明属于来源产品的解释，不能成为 Cursor 双文件失败的根因。所给交叉引用不证明修复关系，截断补丁也不能证明缺少回归测试。

- 来源：[Hmbown/Codewhale — v0.9.4: xAI device login cannot activate the persisted provider configuration](https://github.com/Hmbown/Codewhale/issues/5032)
  原文证据：Interactive xAI device login completes its authorization phase but fails while finalizing the provider change.
  关联 PR：[release: Codewhale v0.9.4 release train](https://github.com/Hmbown/Codewhale/pull/5135)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[\[WIP\] Fix xAI device login not activating persisted provider configuration](https://github.com/Hmbown/Codewhale/pull/5111)；未合并，交叉引用不等于确认修复。
  关联 PR：[release: Codewhale v0.9.4 source candidate](https://github.com/Hmbown/Codewhale/pull/5044)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC003 投毒文本在隐式检索前被拒绝，高风险请求无可信记忆时弃答

对应需求：R2；分类：上下文安全；状态：未执行。

增量价值（模型判断）：新增检索前投毒阻断、可信来源筛选及无可信证据时弃答的可观察检查。

前置条件：隔离存储中含合格的用户撰写可信记忆、外部来源记忆及其他不可信记忆。；准备含独有诱导检索词的投毒 session 和 workstream 文本。；可观察隐式检索输入及 selection/drop 审计；使用符合产品判定条件的高风险请求夹具。

1. 以 schema\_version: 1 请求 context\_bundle，保存无投毒文本时的检索输入。
2. 分别加入投毒 session 和 workstream 文本，再次请求并检查检索输入及丢弃审计。
3. 发起高风险请求，核对每条返回记忆的作者与信任属性。
4. 移除所有合格可信用户记忆后，重复高风险请求。

**预期结果：** 投毒文本在影响隐式检索前被拒绝，诱导词不进入隐式检索输入；审计记录投毒门控丢弃原因且不泄露被拒绝文本。高风险请求只返回合格的用户撰写可信记忆；没有合格记忆时弃答，不以外部或不可信记忆补足结果。

迁移理由（模型建议）：直接覆盖 PRD 的基础安全契约，无须历史 issue。T2 使用预先给定的 context 测试 Codex stdout 包装、ANSI 清除和空输出，并未触发检索或信任门控。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC004 上下文包版本、预算、本地嵌入及固定策略不受环境覆盖

对应需求：R2；分类：上下文策略与预算；状态：未执行。

增量价值（模型判断）：新增环境策略隔离、预算淘汰完整审计及本地嵌入指纹检查。

前置条件：准备足够触发预算淘汰的候选记忆及受支持的明确预算。；设置与 bundle v1 不同的环境检索权重和 reranker；可记录本地与远端 provider 调用。；准备至少两组受支持且有效的本地嵌入配置，保持其余请求和数据一致。

1. 分别提交缺失 schema\_version、非 1 版本及 schema\_version: 1 的请求。
2. 在有效请求下改变环境权重和 reranker，检查生效策略与调用记录。
3. 核对输出预算、来源归属以及全部候选的选中或丢弃审计。
4. 更换本地 embedding provider、model 或 dimensions，比较 plan\_hash。

**预期结果：** 缺失或非 1 schema\_version 的请求被明确拒绝。有效请求仅使用本地前台查询嵌入，环境 reranker 不运行，检索权重遵循 bundle v1。输出遵守指定预算，每条选中内容可追溯来源，选中和丢弃均有规范原因。本地嵌入配置指纹进入 plan\_hash，配置变化反映在哈希中；不把实验性响应形状作为永久稳定 API 验收。

迁移理由（模型建议）：版本、预算和检索策略是 PRD 明确要求。提供的 T2 渲染测试不观察嵌入调用、权重、候选选择或 plan\_hash。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC005 CurrentTruth 诊断统一快照、不写库且历史截点警告退出

对应需求：R3；分类：只读真相诊断；状态：未执行。

增量价值（模型判断）：新增诊断只读证据、跨查询一致性、文本不披露及 quiet 模式历史警告退出检查。

前置条件：当前 schema 数据库包含合成声明文本标记、冲突、弃答、supersedes 及悬空引用。；可记录数据库写入、有效 epoch，并在诊断子查询之间提交受控并发修改。；另备旧 schema 数据库副本。

1. 执行 remem doctor truth --cwd . --json，记录 as\_of\_epoch、各子查询读取状态及诊断结果。
2. 在子查询之间提交并发修改，核对报告是否仍来自同一读取快照。
3. 检查 stdout、stderr 无声明文本标记，检查无写入或迁移。
4. 使用明确早于当前时间的 --as-of-epoch，分别运行普通和 quiet 模式，记录警告与退出状态。
5. 对旧 schema 副本运行诊断，检查副本未被迁移。

**预期结果：** 无显式截点时只采样一个 as\_of\_epoch，全部投影与诊断查询使用该 epoch 和同一读取快照。报告呈现适用的冲突、弃答及引用诊断，但不输出声明文本，不写库、不迁移。显式历史截点报告不可重建并以状态 1 退出，quiet 模式也以状态 1 退出。旧 schema 副本不被诊断升级。

迁移理由（模型建议）：仅迁移诊断或就绪检查读取路径意外产生持久化修改的风险，不引入来源产品的凭据授权功能。统一快照和历史退出语义来自 PRD。所给 PR 的配置写入、凭据回滚及 dotenv 测试触发条件不同，不能证明 remem truth 诊断已有覆盖。

- 来源：[Hmbown/Codewhale — v0.9.1: require explicit consent before reading or rewriting other CLIs' credentials](https://github.com/Hmbown/Codewhale/issues/4507)
  原文证据：Codewhale can discover \`~/.codex/auth.json\` without a user first choosing credential import, and the Codex path can refresh an expired token and write the refreshed credential back to the Codex CLI file.
  关联 PR：[security(auth): require consent for external CLI credentials](https://github.com/Hmbown/Codewhale/pull/4524)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(security): contain workspace dotenv authority](https://github.com/Hmbown/Codewhale/pull/4521)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(auth): isolate xAI device login from Tokio](https://github.com/Hmbown/Codewhale/pull/4505)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC006 会话任务合并、重试身份复用及投影失败共同回滚

对应需求：R4；分类：捕获事务与重试；状态：未执行。

增量价值（模型判断）：新增捕获、兼容投影与提取任务的事务一致性，以及重放后的身份唯一性检查。

前置条件：隔离数据库可检查 captured\_events、events、event\_blobs 和 extraction\_tasks。；准备同一 host/project/session 的多个不同事件、同一事件的 hook 重试输入及超过内联阈值的大载荷。；可在兼容 events 投影写入时注入失败；保存失败前相关行的快照。

1. 连续捕获同会话多个事件及大载荷，检查账本、blob 和提取任务组织。
2. 重复提交同一 hook 事件，比较规范事件与兼容投影的身份和数量。
3. 捕获一个新事件并注入投影失败，比较相关表与失败前快照。
4. 解除故障后重放该事件，核对最终事件、投影及提取任务。

**预期结果：** 原始证据进入追加账本，大载荷进入 event\_blobs；提取工作按 host/project/session 合并，不为每次工具调用创建独立 LLM 作业，原始事件不直接成为 curated memory。hook 重试复用规范事件与兼容投影身份。投影失败时，该次捕获及提取任务新增或更新共同回滚，既有状态保持；重放成功后无重复事件或投影。

迁移理由（模型建议）：迁移失败回滚残留污染重试的触发条件，不复制 Git 更新流程，也不把文件回滚原因当作数据库事务根因。来源 PR 的新增断言主要检查 Git staging 代码形状或更新确认，不验证该残留回滚场景。T1 夹具虽调用捕获接口，但没有合并、重试或失败回滚断言。

- 来源：[career-ops-hq/career-ops — update-system.mjs apply: false-positive SAFETY VIOLATION on pre-existing dirty user file + incomplete directory rollback](https://github.com/career-ops-hq/career-ops/issues/2015)
  原文证据：After the abort, \`git status --short\` showed 4 new files staged under \`docs/\` that the "rollback" didn't remove, plus the unrelated pre-existing \`story-bank.md\` diff, exactly as it was before \`apply\` ran.
  关联 PR：[fix(update-system): force-add explicitly named system files in addPaths](https://github.com/career-ops-hq/career-ops/pull/1997)；未合并，交叉引用不等于确认修复。
  关联 PR：[feat(updater): require confirmation before installation](https://github.com/career-ops-hq/career-ops/pull/2866)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[chore: release main](https://github.com/career-ops-hq/career-ops/pull/2091)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。
### TC007 默认导出保护声明，审计满足全部适用门控才展示文本

对应需求：R5；分类：用户资料导出；状态：未执行。

增量价值（模型判断）：新增默认声明筛选、多门控脱敏、来源信息及既有输出文件保护检查。

前置条件：准备默认合格声明，以及 suppressed、deleted、expired、future、personal、sensitive、restricted 声明和手工摘要。；准备同时受抑制与敏感门控约束的声明，各项使用不同的合成文本标记。；准备不存在的输出路径及含哨兵内容的既有文件；保存数据库状态。

1. 执行默认 Markdown stdout 导出，再导出到新文件。
2. 核对 SQLite 真相来源说明、owner/project 元数据、活动摘要 provenance 和 source ids。
3. 对多门控声明分别启用单个适用审计标志，再启用全部适用标志，比较审计标签与文本。
4. 尝试导出到既有文件，比较文件内容及数据库状态。

**预期结果：** 默认快照排除规定的敏感、受限及失效声明，仅包含默认合格内容和相应来源信息。审计行带排除原因，未满足全部适用门控时文本保持脱敏；满足全部适用门控后可按明确审计请求展示。新文件可创建，既有文件拒绝覆盖且内容保持不变；导出不修改数据库。

迁移理由（模型建议）：直接覆盖 PRD 导出基础契约。T1 的安全 Web 资源投影测试不是 Markdown 用户资料导出测试，不能据此认定导出筛选或审计门控已有覆盖。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC008 非法游标明确失败，缺失会话为空且读取不迁移

对应需求：R6；分类：原始读取错误契约；状态：未执行。

增量价值（模型判断）：新增 raw 运行时游标错误、成功空结果、写锁下不迁移及旧 schema 只读拒绝边界。

前置条件：准备有效 raw messages 游标、损坏游标及依据实际失效规则构造的陈旧游标。；准备不存在的精确三元组、持有写锁的当前 schema 数据库和旧 schema 副本。；可观察数据库写入；raw reconcile 请求同时提供合法时间上下界。

1. 分别提交损坏和陈旧游标；另用有效游标逐项改变 source\_root、project 或 session\_id。
2. 查询不存在的完整三元组，记录 JSON envelope 和退出状态。
3. 持有写锁时运行合法 raw search、raw sessions、raw messages 和 raw reconcile 读取。
4. 对旧 schema 副本运行这些读取，比较 schema 及数据。

**预期结果：** 损坏、陈旧及选择条件不匹配的游标明确失败，不回退到首屏或其他会话。不存在的三元组返回成功的空消息 envelope。当前 schema 读取不写库或发起迁移，不因写锁触发迁移争用。旧 schema 返回迁移诊断且不修改副本；不将只读承诺扩大为所有锁条件下都必须立即成功。

迁移理由（模型建议）：直接覆盖 PRD 的运行时错误与只读契约。T3 只解析游标字符串；T1 对 Web workstreams/events 游标的错误断言不等同于 raw CLI 游标校验。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC009 任意文件名明文副本按内容检出，并按 live 加密状态分级

对应需求：R8；分类：明文残留诊断；状态：未执行。

增量价值（模型判断）：新增任意文件名内容识别、加密状态分级、Fail 退出码及扫描只读检查。

前置条件：准备 live 已确认加密且可读、live 明文、live 加密状态无法确认三类隔离环境。；在管理目录的嵌套路径放置有效 SQLite 明文副本，包含任意文件名和无扩展名文件。；保存文件内容、存在性及数据库状态，避免其他故障干扰加密环境的退出码判定。

1. 在 live 已确认加密的环境运行 remem doctor，记录残留项、检查状态及退出码。
2. 在 live 明文和加密状态无法确认的环境重复检查。
3. 比较所有夹具的运行前后内容、存在性及数据库状态。

**预期结果：** 管理目录内明文副本按内容被识别，不依赖扩展名。live 已确认加密时 Plaintext residue 为 Fail，doctor 退出码为 2；live 明文或加密状态不能确认时该发现为 Warn。诊断不删除、移动或修改任何副本及数据库。

迁移理由（模型建议）：直接覆盖 PRD 的内容扫描、加密状态分支及只读错误契约；不从来源产品故障推断 remem 已存在泄露。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC010 异常链接、短备份及 I/O 错误不得静默报正常

对应需求：R8；分类：扫描完整性与平台边界；状态：未执行。

增量价值（模型判断）：新增不可检查对象的显式诊断、禁止链接目标访问、短文件分类及 Windows 递归边界。

前置条件：管理目录中准备外部目录符号链接、悬空 artifact 链接，以及可记录访问的外部哨兵。；准备 backups 内短于 SQLite header 的文件、其他位置的短普通文件及数据库命名短文件。；可注入枚举或读取 I/O 错误；Windows 准备目录重解析点并记录其目标访问。

1. 分别启用各链接、短文件及 I/O 故障夹具并运行 doctor。
2. 检查 Plaintext residue 详情、外部目标访问记录及文件状态。
3. 在 Windows 对重解析点运行递归扫描，核对是否在下降到目标前拒绝。

**预期结果：** 扫描不跟随符号链接，Windows 在递归下降前拒绝重解析点，外部目标不被读取。非获准 artifact 链接导致检查不完整；backups 内短文件报告不完整，其他位置无数据库命名的短普通文件可忽略，数据库命名短文件不能按无关文件静默忽略。I/O 错误被报告并阻止检查为 Ok；扫描不修改文件。

迁移理由（模型建议）：迁移悬空链接被静默跳过而掩盖检查缺口的触发条件，预期遵循 remem 禁止跟随链接的契约，不复制技能加载功能。相关 PR 的空 Git 文件清单探针验证另一种检查盲区，不是残留扫描测试；交叉引用也不足以证明该 PR 修复原 issue。

- 来源：[career-ops-hq/career-ops — v1.7.1 update ships broken /career-ops symlink (target .agents/ missing)](https://github.com/career-ops-hq/career-ops/issues/649)
  原文证据：After \`node update-system.mjs apply\` to v1.7.1, the \`/career-ops\` slash command stops working. Skill registry shows no \`career-ops\` entry.
  关联 PR：[feat(test): seed-fixture.mjs + era-appropriate install fixtures](https://github.com/career-ops-hq/career-ops/pull/2032)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(test): make the SYSTEM\_PATHS coverage guard actually run in CI](https://github.com/career-ops-hq/career-ops/pull/2240)；已合并，交叉引用不等于确认修复。
  关联 PR：[fix(update): use target updater manifest during apply](https://github.com/career-ops-hq/career-ops/pull/983)；已合并，交叉引用不等于确认修复。
  PR 关联扫描达到数量上限，结果可能不完整。

## 补充边界

### TC011 精确会话分页在并发追加下保持完整内容与冻结边界

对应需求：R6；分类：原始消息分页；状态：未执行。

增量价值（模型判断）：保留已有默认 limit 参数覆盖，新增真实消息查询、完整内容、时间与 ID 排序、精确元组隔离及并发追加快照边界。

前置条件：当前 schema 中目标精确三元组有 501 条消息，包含相同时间戳、不同角色及长内容。；其他 source\_root、project、session\_id 组合中存在相似消息。；可在两页之间向目标及其他元组追加消息，包括事件时间早于首屏消息的新行。

1. 使用完整三元组执行 remem raw messages --json，不指定 limit，保存首屏及 next\_cursor。
2. 追加上述消息，再以原选择条件和原游标读取后续页。
3. 合并旧快照各页，与首屏前目标元组的 501 条消息逐条比较。
4. 重新从首屏查询，检查新追加消息是否进入新快照。

**预期结果：** 首屏默认最多 500 条，按 created\_at\_epoch ASC、id ASC 排序，消息内容不截断。旧游标仅返回首次冻结最大行 ID 内的目标元组消息，原有 501 条无重复、遗漏或串会话；新追加行即使事件时间更早也不进入旧快照。新首屏可纳入已提交的追加行。

迁移理由（模型建议）：来自 PRD 的完整读取与快照契约。T3 已验证 Messages 默认 limit 参数为 500，但不执行数据库读取。T1 的安全 Web 资源游标测试使用不同资源和排序语义，不能充当 raw messages 并发分页覆盖。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/remem/src/cli/tests\_raw.rs:138
  源码引文：fn cli\_raw\_messages\_defaults\_to\_500\_and\_requires\_exact\_tuple() {     let cli = Cli::parse\_from(\[         "remem",         "raw",         "messages",         "--source-root",         "local",         "--project",         "/repo",         "--session-id",         "session-1",     \]);     match cli.command {         Commands::Raw {             action: RawAction::Messages { limit, .. },         } =&gt; assert\_eq!(limit, 500),         \_ =&gt; panic!("expected raw messages command"),     }；该唯一片段以省略 limit 的完整三元组解析 raw messages，并断言默认值为 500；没有读取消息、翻页或并发追加断言。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC012 条件验收发布能力、安全审核幂等性及当前精确归档恢复

对应需求：R7；分类：安全 Web 生命周期；状态：未执行。

增量价值（模型判断）：五类读资源映射已有断言，无须重复增加同等测试；新增发布证据门槛、其余必要能力映射、安全审核重复请求、Dream 过期确认及旧归档恢复拒绝。

前置条件：执行发布验收前须补充目标已发布 v0.6.6 或后续兼容发布的证据；当前输入不足以确认此门槛。；通过 CLI 启动隔离 localhost API，使用测试令牌、普通候选、Dream 隔离候选和活动记忆。；具备符合实际请求契约的版本信息、幂等请求身份、Dream 当前 pattern 与 provenance-token；准备过期确认和旧归档夹具。

1. 核对发布证据及 capabilities 的完整能力/端点映射；将 unreleased 清单和不匹配映射作为门槛负向材料。
2. 读取候选详情与证据，提交版本化安全审核，重复同一请求并比较状态和审计关联。
3. 对 Dream 候选分别提交缺失、过期及当前有效的 pattern/provenance 确认。
4. 归档并恢复当前精确 Web archive；再次归档后尝试使用旧归档身份恢复。
5. 检查 memory\_delete 和端点映射中是否暴露永久删除能力。

**预期结果：** 发布门槛只有在真实已发布版本与精确能力映射均满足时才可验收，unreleased 清单不算发布证据。重复安全审核不重复应用状态副作用，操作可审计。Dream 确认缺失或过期时拒绝应用；当前有效确认可进入正常审核流程。仅当前精确 Web archive 可恢复，旧身份不能恢复后续归档。memory\_delete=false，端点映射无 delete key。

迁移理由（模型建议）：直接覆盖 R7，使用 CLI 启动 API及协议检查，不扩展为独立 Web 客户端功能。T1 已断言五类读资源的能力映射，但不证明版本发布、完整控制台映射、审核幂等性或精确归档恢复。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/remem/src/api/tests/read\_resources.rs:47
  源码引文：let (\_, capabilities) = get\_json(&amp;app, "/api/v1/capabilities", &amp;token).await?;     for resource in \["observations", "sessions", "workstreams", "events", "tasks"\] {         assert\_eq!(capabilities\["features"\]\[resource\], true, "{resource}");         assert\_eq!(             capabilities\["endpoints"\]\[format!("{resource}\_list")\],             format!("/api/v1/{resource}")         );         assert\_eq!(             capabilities\["endpoints"\]\[format!("{resource}\_detail")\],             format!("/api/v1/{resource}/{{id}}")         );     }；实际读取 capabilities 并逐类断言五类读资源的 feature 与 list/detail 路径；未检查发布证据、审核端点、归档恢复或永久删除能力。
- 来源：PRD 基础用例，没有历史 issue 支撑。

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：尚未覆盖首次安装时两个文件存在性的全部组合、remem 名称碰撞、补偿操作自身失败、卸载后降级及完整 doctor drift/collision 状态。并发修改检测需补充具体阶段夹具；PRD 已声明最终比较至 rename 间编辑可能丢失，不能设为无条件并发保留或跨文件原子验收。来源 PR 的 TOML stale-writer 测试也不能证明 Cursor 双文件流程具备同等保障。
- R2：尚未穷举投毒类别、memory/session/preference 全部规范预选原因、预算临界值与降级组合。README 中关联的无载荷持久化审计、哈希验证、delta 完整项回退及 gate 持久化失败后重新封存尚未展开。T2 仅测试给定上下文的输出渲染，不能支持上述行为已有覆盖。
- R3：尚未覆盖 exact project 与 cwd 归一化、三种 subject 表达、subject 限定生命周期计数、无匹配身份的对象省略及全部 stored-status/supersedes 映射。相关 legacy\_unverified 的搜索可恢复与 CurrentTruth 默认排除亦未展开。提供的文件未发现 truth 诊断直接测试；不代表整个仓库没有测试。
- R4：尚未覆盖不同 host/project/session 的任务隔离、持续负载下合并、blob 存储失败及所有事务失败阶段。默认不安装 Codex 高频 Bash observe、显式环境变量启用旧 hook，以及 Cursor 手动 observe/summarize 的严格解析和 degraded 回退未展开。来源更新 PR 的源码模式检查没有验证数据库重试身份或回滚。
- R5：尚未穷举审计标志组合、personal/restricted 与其他状态交叉、手工摘要门控、owner/project 隔离及并发创建输出文件。用户声明审核、自动提升硬门控、backfill 只读预览与重复偏好消除、recall 与多读取面抑制一致性属于 README 关联主题，本轮优先用例未展开；现有 Web 脱敏测试不能替代这些用户资料流程。
- R6：尚未充分覆盖 raw sessions 的分组、角色计数及用户样本；陈旧游标的具体失效条件需补充实现契约或夹具证据。ingest 的逐次 occurrence 身份、增量幂等、缺失显式 root，以及 reconcile 的 UTC 时间边界、身份冲突、文件状态校验和仅聚合输出未展开。T3 是参数解析，T1 是其他 Web 资源分页，均不能证明 raw 数据读取已有完整覆盖。
- R7：缺少目标发布版本及发布证据，发布验收仍为条件方案。尚未覆盖五类读资源分别关闭时的独立门控、审核并发冲突和全部版本错误；T1 已提供鉴权、安全投影、游标、抑制与结构化错误断言，但不证明完整控制台生命周期。API localhost 绑定、令牌权限、health/status 缓存契约及全部 JSON 输出形状未展开。仅审查提供的材料，未执行测试，不能将源码能力或来源 PR 的通过声明作为本次验证结果。
- R8：尚未覆盖获准 Hugging Face snapshot pointer 的严格验证及独立 blob 扫描、key/live sidecar 排除项、各类 Windows 重解析点和 live 加密状态异常组合。README 其他安全主题中的目录/key/token 权限、SQLCipher 加密转换、SQLite 参数严格校验和崩溃持久性未展开。编译规则资格矩阵仍有明确未完成范围，另有 worker 限额、清理保留、pending 精确恢复、Dream backfill 及 procedure 导出保护等未纳入的命令主题；需另行确定验收范围并补充方案。本草稿不构成整份 README 覆盖认证，也不把截断或未提供源码视为没有测试。
- 待确认：摘录未提供目标发布版本。安全 Web 接口明确要求已发布 v0.6.6 及精确能力/端点映射；本轮是否包含该版本的验收，需确认，不能将 unreleased 源码清单视为已发布能力。
- 待确认：编译偏好规则明确说明全局所有者过滤及完整资格矩阵仍未完成；若纳入验收，需要补充当前已承诺的适用范围，不能把未完成工作当作现有要求。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
