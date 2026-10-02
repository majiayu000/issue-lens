# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是从同类产品历史问题迁移的测试建议，不是目标产品的已确认缺陷。

产品形态：cli；语料：16054 条；本次选入：12 条；测试建议：5 条。

来源只含 issue 标题与正文；没有读取关联 PR 补丁或评论。根因与适用性仍需人工复核。

## 需求与检索范围

- **R1 凭据加密与 Agent 隔离**：- Credentials are stored envelope-encrypted (AES-256-GCM, binary AAD binding   vault/credential/version/purpose) and decrypted only after capability,   action, and audit checks pass — once per request, zeroized after use. - The agent wire protocol has no secret-read operation and no way to choose   origin, method, path, auth headers, or redirects.
  检索词：credential, encryption, permission, isolation；选入候选 2 条。
- **R2 固定请求的网络限制与响应防泄漏**：The production transport rejects all non-public address ranges, including \`198.18.0.0/15\`. On systems where a TUN proxy returns that range as fake DNS answers, domain-based Actions fail closed until the host supplies real DNS; Rekey does not silently allow the fake-IP range or honor proxy environment variables.
  检索词：ssrf, dns, proxy, redaction；选入候选 2 条。
- **R3 密码与恢复密钥管理**：The recovery key can unlock the running broker, satisfy an explicit Admin step-up with \`--recovery\`, or verify an offline backup restore. With the broker unlocked, \`rekey password change\` atomically replaces the password wrapper; add \`--recovery\` when the current password is lost. \`rekey recovery rotate\` requires the current password, replaces the recovery wrapper, and displays the new recovery key once. Neither operation rotates the VRK or Credential data.
  检索词：recovery, restore, rotation, atomicity；选入候选 2 条。
- **R4 签名策略、会话撤销与工作负载令牌防重放**：The JWT is consumed once and replay denial persists across restart and any restore whose backup already contains the consumption record. A new-version policy activation revokes workload-minted sessions; an exact same-bundle retry preserves them.
  检索词：signature, replay, revocation, session；选入候选 2 条。
- **R5 审批授权精确绑定与有效期限制**：The grant is bound to the challenge, session, principal, exact Action/resource, canonical parameters, determining rule, policy version/digest, validity window, and use limit. Rekey provides no hosted remote approval service, notification UI, human directory, private-key custody, or approval survival across lock/restart.
  检索词：approval, authorization, expiration, binding；选入候选 1 条。
- **R6 锁定状态下的脱敏审计与安全导出**：List results use a stable sequence snapshot and bounded pages. Export creates a new mode-0600 JSONL file and never overwrites or follows a symlink. Audit output omits secrets, bodies, headers, capability tokens, resource IDs, and parameter hashes. It is sensitive operational metadata, not an encrypted backup. Local retention is append-only for the vault lifetime; SIEM, WORM, legal hold, remote delivery, configurable retention, and audit deletion are not implemented.
  检索词：audit, pagination, symlink, redaction；选入候选 1 条。
- **R7 CLI 自动化秘密输入通道**：For explicit automation, proof-only commands use \`--password-stdin\`; \`rekey password change --stdin-secrets\`, \`rekey credential add\`, and \`rekey credential rotate\` read the step-up proof on line 1 and the new secret on line 2. Add \`--recovery\` when that proof is the recovery key. Secrets are never accepted as argument values or environment variables.
  检索词：stdin, credential, argument, environment；选入候选 1 条。
- **R8 限定 Vault 动态凭据执行与租约撤销**：This archive also supports one closed one-shot Vault dynamic source. Each execution performs one \`GET /v1/MOUNT/creds/ROLE\`, uses one selected string in the fixed Action, and withholds the Action response until \`POST /v1/sys/leases/revoke\` succeeds for the exact lease with \`sync: true\`:
  检索词：lease, revocation, cleanup, response；选入候选 1 条。

## Agent 凭据隔离

### TC001 仅持 capability 的 Agent 执行 Action 时无法读取所用凭据

对应需求：R1；状态：未执行。

前置条件：在待确认版本支持的 macOS 或 Linux 环境使用隔离测试 vault，采用默认 G1 范围。；Admin 已保存唯一可识别的虚构凭据，注册固定 HTTPS Action，并完成策略及 capability 配置。；受控公网 HTTPS 上游可验证认证是否正确，但响应不回显凭据；Agent 仅使用 agent.sock。

1. 通过 Agent CLI 使用 capability 执行固定 Action，不向 Agent 提供真实凭据值。
2. 检查 Agent 可见的请求字段、正常响应及执行输出。
3. 通过 agent.sock 尝试提交凭据读取请求，检查返回结果。
4. 让受控上游返回不含凭据的错误，再检查 Agent 输出、broker 日志和审计记录。

**预期结果：** 合法执行由上游确认认证成功，Agent 无需提供或看到凭据；凭据读取请求被拒绝且不返回秘密。正常及失败路径的 Agent 输出、日志和审计记录均不包含测试凭据。

迁移理由（模型建议）：原文证据描述 secret 作为可编辑参数时对工作流编辑者可见。迁移的是执行配置暴露秘密这一条件，用于验证 Rekey 的 Admin 存储与 Agent 使用隔离；不引入 HMAC 节点，也不据此断言 Rekey 存在泄漏。

- 来源：[n8n-io/n8n — Crypto node does not support secret as a credential](https://github.com/n8n-io/n8n/issues/16035)
  原文证据：The built in crypto node insecurely requires the parameter 'secret' and does not allow us to use a credential for it. This allows anyone with edit permission on the workflow to see the secret value.

## Fake DNS 与代理边界

### TC002 固定 Action 域名解析为 fake-IP 时拒绝，恢复真实公网 DNS 后可执行

对应需求：R2；状态：未执行。

前置条件：固定 Action、策略及 capability 均有效，使用受控公网 HTTPS 上游。；测试环境可将该 Action 的精确主机名解析为 198.18.0.0/15 内地址或真实公网地址。；可观测 DNS 查询、上游请求以及测试代理收到的连接。

1. 让该主机名仅返回 fake-IP 地址，确认实际 DNS 应答后执行 Action。
2. 在 broker 和调用 CLI 的启动环境中设置指向受控代理的 HTTP\_PROXY、HTTPS\_PROXY、ALL\_PROXY，重复执行。
3. 仅将该主机名的 DNS 恢复为真实公网地址，确认应答后再次执行同一 Action。

**预期结果：** fake-IP 两轮均拒绝执行，不向受限地址发送 Action 请求，也不通过环境变量指定的代理绕过筛选；恢复真实公网 DNS 后，在其余条件有效时上游收到固定请求并返回预设响应。

迁移理由（模型建议）：原文证据仅确认 fakeip 代理用户无法使用请求工具；具体检查实现属于提炼判断。借用 fake-IP DNS 这一触发条件，预期依据 Rekey 明确的拒绝策略制定，不迁移其他产品的代理放行需求。

- 来源：[Hmbown/Codewhale — fetch\_url blocks all requests when DNS resolves to private IPs (fakeip proxy incompatible)](https://github.com/Hmbown/Codewhale/issues/1071)
  原文证据：Users behind fakeip proxies cannot use \`fetch\_url\` at all.

## 网络拒绝路径验证

### TC003 区分受限地址拒绝与 DNS 无结果，防止相同失败结果掩盖漏测

对应需求：R2；状态：未执行。

前置条件：在支持的 macOS 或 Linux 测试环境使用有效的固定 Action 和授权配置。；可控 DNS 能记录查询并分别返回指定地址或空结果；网络观测可确认连接目的地址。；使用独立测试主机名或隔离运行，避免前一次解析结果影响下一轮。

1. 分别让 Action 主机名解析为 127.0.0.1、::1、私网地址及 198.18.0.0/15 内地址，逐轮执行。
2. 每轮确认解析设施确实被调用并交付指定应答，同时检查是否出现向该地址的连接。
3. 另设 DNS 空结果轮次，执行相同请求。
4. 增加真实公网地址对照轮次，确认测试设施没有使所有请求无条件失败。

**预期结果：** 受限地址轮次在确实取得对应 DNS 应答后被拒绝，且不向这些地址发送请求；空结果轮次同样不能发出 Action 请求，但记录能够与受限地址轮次区分。公网对照在其他条件有效时成功。不能仅以相同失败文本认定各路径已覆盖。

迁移理由（模型建议）：原文证据明确指出相同判定来自不同路径，预期的回环拒绝分支未实际执行。迁移的是拒绝测试可能误通过的条件；不假设 Rekey 使用 Node.js 模块、相同 DNS 缓存或 Windows 解析机制。

- 来源：[career-ops-hq/career-ops — bug(tests): the SSRF DNS mock stubs dnsModule.default but liveness-browser calls the namespace — test passes by accident and costs 12s per run](https://github.com/career-ops-hq/career-ops/issues/2386)
  原文证据：Same verdict, completely different code path, and the loopback-rejection branch the test was written to cover is never actually exercised.

## 秘密输入参数解析

### TC004 秘密输入选项拼错时不得转为位置参数并造成凭据变更

对应需求：R7；状态：未执行。

前置条件：隔离 vault 已解锁，保存一个使用虚构旧凭据的固定 Action。；准备有效 Admin proof 和虚构新凭据，均仅通过 stdin 提供。；记录变更前的凭据版本及固定 Action 的认证结果。

1. 对 password change 使用拼错的 --stdin-secret，按预定两行输入 proof 与新密码。
2. 对一个支持 --password-stdin 的 proof-only 命令使用拼错的 --password-stdni。
3. 检查退出状态、错误输出及密码或凭据状态，再使用正确选项进行对照操作。

**预期结果：** 拼错选项的调用明确失败，不显示操作成功，不将选项或 stdin 内容误当成业务数据执行变更，且不输出 proof 或新秘密。原密码和凭据仍有效；正确选项对照按对应命令契约处理 stdin。具体退出码和错误格式沿用目标 CLI 契约。

迁移理由（模型建议）：原文证据描述未知选项被忽略或作为位置参数处理，导致操作看似成功。该触发条件可直接迁移到依赖精确秘密输入选项的 CLI；不复制来源脚本的选项集合或指定其退出码。

- 来源：[career-ops-hq/career-ops — add-entry.mjs has no --help and silently ignores mistyped flags](https://github.com/career-ops-hq/career-ops/issues/2798)
  原文证据：Everything else in \`process.argv.slice(2)\` is treated as a positional argument, so a typo like \`node add-entry.mjs --sumary\` does not warn: it is silently ignored or read as data, and the run looks like it worked.

## 秘密输入数据边界

### TC005 两行 stdin 中以连字符开头的秘密不得被当成 CLI 选项

对应需求：R7；状态：未执行。

前置条件：隔离 vault 已解锁，具备有效 Admin proof。；准备不含换行、以 -- 开头的虚构新密码或凭据，并使用正确的 stdin 输入方式。；固定 HTTPS 测试 Action 可验证凭据是否按原值注入。

1. 向 credential add 的 stdin 第 1 行写入 proof，第 2 行写入虚构凭据。
2. 使用新增凭据配置固定 Action 并执行，由受控上游核对认证值。
3. 使用 credential rotate 重复上述输入边界测试。
4. 使用 password change --stdin-secrets 提交 proof 和以 -- 开头的新密码，随后锁定并用新密码解锁。
5. 检查各次标准输出、错误输出、日志和审计记录。

**预期结果：** 第 1 行仅用于 step-up，第 2 行作为秘密数据完整处理，不被解释为选项。新增及轮换后的凭据可用于预设认证，新密码可解锁；可见输出、日志和审计记录不泄漏输入秘密。

迁移理由（模型建议）：原文证据支持参数与数据混淆这一风险。此处构造其在 Rekey 两行 stdin 协议中的边界对照，预期来自 PRD；不声称历史案例已经证明 stdin 中存在此故障。

- 来源：[career-ops-hq/career-ops — add-entry.mjs has no --help and silently ignores mistyped flags](https://github.com/career-ops-hq/career-ops/issues/2798)
  原文证据：Everything else in \`process.argv.slice(2)\` is treated as a positional argument, so a typo like \`node add-entry.mjs --sumary\` does not warn: it is silently ignored or read as data, and the run looks like it worked.

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：现有案例仅覆盖部分秘密可见性。AES-256-GCM 与 AAD 绑定、检查通过后才解密、每请求解密次数、使用后清零、双 socket 权限隔离及固定请求字段防篡改，缺少直接相关历史证据。2727647285 的原文仅报告 OAuth 401，不能支持这些测试。默认 G1 不扩展到同用户 ptrace、内存或文件系统攻击。
- R2：已覆盖 fake-IP 和部分 DNS 拒绝路径，但未穷尽全部非公网地址、混合 DNS 应答及解析变化。响应大小限制、响应头过滤、raw/base64/base64url/percent-encoded 秘密回显扫描和重定向限制也无充分相关历史证据。不能把其他产品的 Windows DNS 环境列为 Rekey 支持平台。
- R3：未生成历史驱动案例。5045284631 的证据是 TUI 状态栏截断，4370093846 的证据是已有检查点未展示；均不足以迁移到密码 wrapper 原子替换、恢复密钥解锁与轮换、离线恢复及 VRK/凭据数据不变性。测试版本尚未明确，不能混用 alpha.2 格式 9 与源码格式 10 的备份，更不能提出原地升级兼容要求。
- R4：未生成案例。5418816013 涉及模型协议 thought\_signature 缺失，4952152023 涉及终端历史重放性能，均不支持策略签名或 JWT 防重放测试。信任根不可变、连续策略版本、解锁后重验、锁定/重启撤销、JWT 消费记录跨重启和含记录备份恢复，以及新版本撤销与同包重试保留会话，均待补充相关证据。源码专属 JWKS 是否纳入也待目标版本明确。
- R5：未生成案例。4556858835 的原文只建议保留移动端冒烟验证，没有证明审批绑定、重试或有效期的具体故障条件；不能将提炼出的 HTTP 路由场景视为原文证据。challenge、session、principal、Action/resource、规范参数、规则、策略版本/摘要、有效期和使用次数绑定，以及锁定/重启失效均未覆盖；不引入移动端、远程审批服务或通知 UI。
- R6：R1、R7 仅附带检查部分秘密不进入审计，不能替代本主题覆盖。5224906687 的证据仅说明已有 MCP 配置发现功能，与审计安全导出无直接关系。锁定读取、稳定序列快照、有界分页、完整字段脱敏、新建 mode-0600 文件、拒绝覆盖和符号链接、生命周期内仅追加均缺少充分相关案例；不引入配置迁移或审计删除功能。
- R7：已覆盖选项拼错及两行输入的数据边界；proof-only 输入、缺行/提前 EOF、错误 proof、--recovery、通过参数或环境变量提交秘密的拒绝行为，以及策略专用 --step-up-stdin 尚未充分覆盖。现有证据不能证明这些故障，未据此扩展案例。
- R8：未生成案例。5238725556 的原文是并行套件中恢复回合 ID 断言偶发失败，未提供 Vault 租约或撤销证据，不能依据提炼中的 lease\_id 推断相关性。单次获取、选定字符串注入、精确 lease 的 sync:true 撤销、撤销成功前扣留响应、失败处理及 5–300 秒边界均未覆盖；不要求租约续期、后台注册表或进程/主机崩溃后清理。
- R1：跨主题执行范围待确定：本草稿未执行。尚未指定 alpha.2 CLI 或当前源码 CLI，也未提供完整系统版本与架构矩阵；案例应在确认后的受支持 macOS/Linux 组合落地，不包含 source-only macOS UI、默认 G2 或跨版本迁移验收。
- 待确认：测试目标是已发布的 alpha.2 CLI，还是当前开发源码 CLI？正文区分存储格式 9 与 10，并明确后者拒绝旧状态和备份、没有迁移；不能将两者合并为升级兼容要求。源码专属的 JWKS、Keycloak、MCP 和本地审批工具也需据此确定是否纳入。
- 待确认：正文未完整列出 CLI 平台支持矩阵，仅提供链接与 macOS/Linux 安装通过的描述；具体支持的系统版本和架构待明确。Linux agent-run 仅适用于所述 Linux 拓扑，不能扩展为 macOS 或默认 G2 要求。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
