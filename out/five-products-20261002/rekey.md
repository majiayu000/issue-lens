# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是依据 PRD 和同类产品历史问题生成的测试建议，不是目标产品的已确认缺陷。

产品形态：cli；语料：16054 条；本次选入：8 条；测试建议：12 条。

基础用例来自 PRD，历史启发用例附 issue 来源。PR 证据按来源单独标注；未采集评论。

已有覆盖只指所提供测试文件中的源码断言，未执行测试；未检出不等于全仓库无覆盖。

## 需求与检索范围

- **R1 凭证隔离、加密存储与安全输入**：Credentials never appear &gt; in agent-facing APIs, process arguments, environment variables, logs, or audit &gt; records. Same-user \`ptrace\`, process memory, and filesystem access are out of &gt; G1.
  组合检索：secret AND leak OR stdin AND password OR encryption AND zeroization；选入候选 3 条。
- **R2 固定 Action 执行、网络限制与响应防泄露**：- The agent wire protocol has no secret-read operation and no way to choose   origin, method, path, auth headers, or redirects. - Responses are size-bounded, header-filtered, and scanned for reflected   secrets (raw, base64, base64url, percent-encoded) before the agent sees them.
  组合检索：response AND leak OR DNS AND private OR redirect AND authorization；选入候选 3 条。
- **R3 恢复密钥与密码变更的原子性及存储版本边界**：The recovery key can unlock the running broker, satisfy an explicit Admin step-up with \`--recovery\`, or verify an offline backup restore. With the broker unlocked, \`rekey password change\` atomically replaces the password wrapper; add \`--recovery\` when the current password is lost. \`rekey recovery rotate\` requires the current password, replaces the recovery wrapper, and displays the new recovery key once. Neither operation rotates the VRK or Credential data.
  组合检索：password AND failure OR recovery AND rotation OR backup AND version AND reject；选入候选 1 条。
- **R4 锁定状态下的脱敏审计、稳定分页与安全导出**：List results use a stable sequence snapshot and bounded pages. Export creates a new mode-0600 JSONL file and never overwrites or follows a symlink. Audit output omits secrets, bodies, headers, capability tokens, resource IDs, and parameter hashes.
  组合检索：pagination AND duplicate OR export AND symlink OR audit AND locked AND secret；选入候选 0 条。
- **R5 签名策略与有界会话的验证、撤销及身份令牌防重放**：The JWT is consumed once and replay denial persists across restart and any restore whose backup already contains the consumption record. A new-version policy activation revokes workload-minted sessions; an exact same-bundle retry preserves them.
  组合检索：token AND replay OR policy AND signature AND version OR session AND restart AND revoke；选入候选 0 条。
- **R6 外部审批授权必须绑定确切请求并受有效期和次数限制**：The grant is bound to the challenge, session, principal, exact Action/resource, canonical parameters, determining rule, policy version/digest, validity window, and use limit. Rekey provides no hosted remote approval service, notification UI, human directory, private-key custody, or approval survival across lock/restart.
  组合检索：approval AND replay OR grant AND parameters AND mismatch OR challenge AND expired；选入候选 1 条。
- **R7 封闭连接器的固定资源、单次读取与动态租约撤销**：This archive also supports one closed one-shot Vault dynamic source. Each execution performs one \`GET /v1/MOUNT/creds/ROLE\`, uses one selected string in the fixed Action, and withholds the Action response until \`POST /v1/sys/leases/revoke\` succeeds for the exact lease with \`sync: true\`:
  组合检索：lease AND revoke OR version AND secret AND retry OR repository AND limit；选入候选 0 条。
- **R8 Linux Agent 启动器的默认拒绝出站与平台限制**：Linux \`rekey agent-run\` (\`linux-netns-v1\`) is a separate deny-by-default IP egress launcher. It requires bubblewrap, a disjoint \`--agent-socket\`, and does not make macOS or general G2:
  组合检索：network AND deny OR socket AND isolation OR bubblewrap AND missing；选入候选 0 条。

## 潜在遗漏（所给文件中未检出）

### TC001 按目标二进制拒绝旧状态及备份，保留原数据

对应需求：R3；分类：存储版本；状态：未执行。

增量价值（模型判断）：所给文件未发现旧格式或非空 v1 的实际触发及断言；T4 的格式 10 同格式恢复、损坏布局拒绝不能替代版本边界。

前置条件：执行前确定 alpha.2/格式 9 或开发源码/格式 10；结论分别记录。；准备由相应历史二进制创建的旧状态和备份、非空 v1 状态目录及同格式备份，并保存内容快照。

1. 开发格式 10 二进制尝试打开旧格式状态及恢复旧格式备份；若选择 alpha.2，只验证其明确不支持的 alpha.1 原地升级。
2. 尝试初始化或打开非空 v1 状态目录。
3. 使用目标二进制创建的同格式备份及正确 proof 完成恢复对照，比较被拒绝输入的内容。

**预期结果：** 目标版本明确不支持的旧状态、备份或 legacy 目录被拒绝，不迁移、不回填，原数据不变；同格式有效备份可恢复。不得将格式 10 源码结果作为 alpha.2 兼容证据。

迁移理由（模型建议）：覆盖 PRD 的破坏性版本边界；alpha.2 对旧备份的具体规则未明确，不从源码格式 10 要求外推。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC002 签名策略生命周期及会话有界撤销

对应需求：R5；分类：策略与 capability；状态：未执行。

增量价值（模型判断）：所给 T1–T4 未发现实际策略签名、版本、封印及会话 TTL/次数撤销的同等触发和断言。

前置条件：使用外部 Ed25519 签名器，broker 不持有签名私钥。；准备合法连续版本、错误签名、跳版本和其他信任根的策略包；创建短 TTL、小 max-uses 会话。

1. 安装信任根、激活合法策略；尝试替换根及激活错误签名或非连续版本。
2. 在 TTL 和次数内执行成功对照，再分别验证到期和次数耗尽。
3. 分别锁定及重启 broker，尝试使用旧 capability；成功解锁后检查持久策略重新验证和加载。
4. 在隔离副本篡改持久策略签名或生命周期封印，检查解锁后的授权行为。

**预期结果：** 只接受合法签名和连续版本，信任根不可替换。会话超时或耗尽后拒绝；锁定、重启撤销旧会话。策略只在成功解锁并重新验证后加载，篡改状态不能取得执行授权。

迁移理由（模型建议）：来自 PRD 的基础授权契约，不增加签名私钥托管或远程签名功能。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC003 确切请求绑定、有效期和次数限制

对应需求：R6；分类：外部审批；状态：未执行。

增量价值（模型判断）：所给 Rekey 测试文件未发现 challenge/grant 的请求绑定、有效期和使用次数断言；新增实际授权门控验证。

前置条件：策略包含 require-approval 规则，并明确一份或两份 grant 要求。；外部 approver 签署独立 challenge 的 grant；可控制时间并观察上游请求计数。

1. 为原 typed request 准备 challenge，使用有效 grant 执行成功对照。
2. 用独立 challenge 逐项改变 session、principal、Action/resource、规范参数、determining rule 或策略版本/摘要，尝试复用不匹配 grant。
3. 提交缺失、格式错误、过期或次数耗尽的 grant；双 grant 规则只提供一份。
4. 分别锁定和重启后尝试使用原授权；对执行失败进行重试，验证不能超出已签署的授权范围和次数。

**预期结果：** 只有满足全部绑定、有效期和次数要求的请求能触达上游。不匹配、缺失或失效授权拒绝；锁定、重启后旧 challenge/grant 不能继续授权。失败不得被解释为额外批准。

迁移理由（模型建议）：迁移一次性审批不能被陈旧决定或不匹配重试扩大授权的条件。其他产品的持久审批恢复不属于 Rekey；所给关联补丁截断，不能据此认定它没有回归测试。

- 来源：[Hmbown/Codewhale — v0.9.8: make one-shot approval outcomes durable and fail-closed](https://github.com/Hmbown/Codewhale/issues/5360)
  原文证据：A resumed session cannot reconstruct the exact ask/outcome pair from its own durable record.
  关联 PR：[fix(tui): persist approval outcomes before execution](https://github.com/Hmbown/Codewhale/pull/5491)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC004 固定版本 KV 单次读取与动态租约撤销门控

对应需求：R7；分类：封闭 Vault 来源；状态：未执行。

增量价值（模型判断）：所给文件未发现 Vault 来源请求次数、固定版本、租约时长或撤销后释放响应的实际断言。

前置条件：使用公开 HTTPS Vault fixture 和固定 Action；不启用私网例外。；KV profile 固定 mount、path、非零版本和字符串 key；动态 profile 固定 mount、role 和选定字段。；可记录来源读取、Action 与 revoke 请求顺序，控制 lease 时长及撤销结果。

1. 执行 KV Action，核对指定版本只读取一次；让来源返回错误或非字符串值，检查无自动重试且不执行目标 Action。
2. 执行动态 Action，核对单次 GET、选定值注入和 exact lease 的 sync:true revoke。
3. 延迟及拒绝 revoke，观察 Agent 响应；再执行撤销成功的独立对照。
4. 检查 lease 时长 5、300 秒接受，区间外拒绝；让来源 token 或解析值反射到响应中。

**预期结果：** KV 不查询 latest、不重试，只使用固定版本的指定字符串。动态执行只获取一次；撤销确切 lease 成功前不释放 Action 响应，撤销失败不报告成功。只接受 5–300 秒租约且不续租；source token 和解析值不暴露给 Agent。

迁移理由（模型建议）：覆盖封闭来源契约；不扩展为通用 Vault、后台租约管理或进程/主机崩溃后的清理保证。

- 来源：PRD 基础用例，没有历史 issue 支撑。

## 补充边界

### TC005 stdin 输入、敏感输出及双 socket 权限隔离

对应需求：R1；分类：凭证隔离与安全输入；状态：未执行。

增量价值（模型判断）：补充凭证添加与轮换的进程边界、双 socket 越权请求及诊断出口检查；已有源码的进程检查主要用于密码变更和恢复轮换。

前置条件：记录目标二进制版本；使用 macOS/Linux 临时环境、虚构密码和凭证，仅验证 CLI 与默认 G1 范围。；配置权限分离的 admin.sock 和 agent.sock；测试输入通过 stdin 传递，不导出为环境变量。

1. 通过 stdin 添加并轮换凭证，第一行提供 step-up proof，第二行提供新秘密；检查 CLI、broker 的参数、环境、标准输出、错误输出及日志。
2. 经 agent.sock 尝试凭证读取和 Admin 修改请求，检查返回数据和审计。
3. 不给有效 stdin proof，验证调用不能通过环境变量获得密码或凭证，也不报告修改成功。
4. 检查合法凭证列表及可用诊断输出，特别检查名称不包含 token、password、key 的敏感字段。

**预期结果：** 合法 stdin 操作完成；Agent 通道不能读取凭证或执行 Admin 修改。密码、凭证和恢复 proof 不进入参数、环境、Agent 输出、日志或审计；输入失败不报告成功。初始化和恢复轮换允许的 Admin 一次性恢复密钥展示单独识别。

迁移理由（模型建议）：借用敏感字段命名导致输出遗漏、替代入口绕过权限限制的触发条件。4718244766 的关联 PR 未合并，只能作为拟议回归思路；4655347640 不用于要求防御 G1 排除的同用户直接文件读取。历史提炼不是 Rekey 根因证据。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-cli/tests/cli\_blackbox.rs:83
  源码引文：    let process = Command::new("ps")         .args(\["-eww", "-o", "command=", "-p", &amp;child.id().to\_string()\])         .output()         .expect("inspect process boundary");     assert!(process.status.success(), "cannot inspect CLI process");     for canary in secret\_canaries {         assert!(             !process                 .stdout                 .windows(canary.len())                 .any(\|part\| part == canary.as\_bytes()),             "secret appeared in CLI argv or environment"         );     }；实际检查子进程参数和环境中的哨兵；调用点用于密码变更和恢复轮换，不等于覆盖全部凭证入口或 socket 权限。
- 来源：[Panniantong/Agent-Reach — \[SECURITY\] \`Config.to\_dict()\` leaks \`twitter\_ct0\` in plaintext — masking logic misses CSRF token key name](https://github.com/Panniantong/Agent-Reach/issues/412)
  原文证据：- \`twitter\_ct0\` → contains none of the above substrings → \*\*returned in plaintext\*\* ❌
  关联 PR：[fix(config): mask twitter ct0 in config output](https://github.com/Panniantong/Agent-Reach/pull/417)；未合并，交叉引用不等于确认修复。
- 来源：[rtk-ai/rtk — Security: rtk native content-reading subcommands (read/grep/diff/log/smart) bypass .env read restrictions](https://github.com/rtk-ai/rtk/issues/2428)
  原文证据：The deny rule targets \`Read\`/\`cat\`/\`grep\`; \`rtk read .env\` matches none of them.
  关联 PR：[feat(claude): disclose AI authorship in posts and share credential-read denials](https://github.com/irisTa56/dotfiles/pull/205)；已合并，交叉引用不等于确认修复。
  关联 PR：[fix(cmds): block .env reads in native content subcommands (\#2428)](https://github.com/rtk-ai/rtk/pull/2429)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC006 合法固定请求及 Agent 越权字段拒绝

对应需求：R2；分类：固定 Action；状态：未执行。

增量价值（模型判断）：补充真实 CLI 到 HTTPS 上游的合法固定配置对照；已有源码覆盖模拟传输下的拒绝路径。

前置条件：注册固定 HTTPS Action，明确方法、路径、认证头、额外头白名单和请求大小限制。；创建有效 capability；受控上游记录实际请求。

1. 通过 CLI 执行合法请求，核对实际目标、方法、路径和认证头。
2. 经 Agent IPC 加入 origin、method、path、authorization、redirect 等字段。
3. 提交认证头覆盖、非白名单头、CRLF 头值及超过 Action 限制的请求体。

**预期结果：** 合法请求遵循管理员固定配置。未知元数据返回 INVALID\_FRAME；非法头和 Action 请求体超限返回 REQUEST\_DENIED，均不触达上游；CLI 不报告成功。

迁移理由（模型建议）：直接覆盖 PRD 基础契约，Agent 没有任意 URL、方法或认证配置能力。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-broker/tests/adversarial\_http.rs:47
  源码引文：    meta\["authorization"\] = serde\_json::json!("Bearer attacker-token");     meta\["redirect"\] = serde\_json::json!(true);      let response = execute\_with\_meta(&amp;broker, meta, b"{}").await;     assert\_eq!(response.err\_code(), "INVALID\_FRAME");     assert!(broker.fake.take\_requests().is\_empty());；明确触发未知授权及重定向字段并断言拒绝、模拟上游未调用；未核验真实合法请求的固定配置。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC007 实际连接筛查、fake DNS 与重定向失败关闭

对应需求：R2；分类：生产网络限制；状态：未执行。

增量价值（模型判断）：新增真实 DNS、实际连接、fake-IP、代理环境和重定向验证；现有模拟错误映射不证明生产传输筛查有效。

前置条件：使用生产传输、受控 DNS 和 HTTPS 上游，不用 FakeTransport 替代地址筛查。；管理员固定 Action 域名；测试设施可观察实际连接和代理请求，非公共目标位于隔离环境。

1. 将固定域名分别解析到回环、私网、链路本地、IPv6 回环及 IPv4 映射非公共地址，设置公共地址成功对照。
2. 使预检与连接阶段的 DNS 回答不同，检查是否可能实际连接到未经验证的非公共地址。
3. 将 DNS 回答设为 198.18.0.0/15，分别在未设置和设置 HTTP/HTTPS 代理环境变量时执行；再仅为该主机恢复真实公共 DNS 后重试。
4. 让公共上游返回重定向，观察是否请求重定向目标。

**预期结果：** 非公共地址和重定向被阻止，被拒绝目标无请求。fake DNS 下失败关闭，代理环境变量不改变限制；恢复真实公共 DNS 后合法请求可完成。网络阻断保留 UPSTREAM\_FAILED 错误契约，不报告成功。

迁移理由（模型建议）：迁移域名解析到非公共地址和代理 fake DNS 的条件；二次解析差异是待验证边界。交叉引用和发行记录不证明所给 PR 修复了原 issue；其他产品的代理放行功能不适用于 Rekey。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-broker/tests/adversarial\_http.rs:129
  源码引文：    broker         .fake         .push\_response(Err(UpstreamError::Blocked("private-address")));     let meta = common::execute\_meta(&amp;token, &amp;action\_id, version);     let response = execute\_with\_meta(&amp;broker, meta, b"{}").await;     assert\_eq!(response.err\_code(), "UPSTREAM\_FAILED");；仅注入已发生的阻断错误并检查映射，没有触发 DNS 或实际连接。
- 来源：[career-ops-hq/career-ops — providers: no fetch validates the resolved IP — a public hostname can point at a private address (DNS rebinding)](https://github.com/career-ops-hq/career-ops/issues/3096)
  原文证据：A hostname with an A record pointing at \`127.0.0.1\`, \`169.254.169.254\` or another private range gets connected to by native \`fetch()\`; \`redirect:'error'\` blocks redirect-based hops but not a direct malicious record.
  关联 PR：[feat(providers): OCC Mundial — Mexico's dominant job board](https://github.com/career-ops-hq/career-ops/pull/3748)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(providers): radancy stops trusting totalResults, cache-busts JSON, retries every fetch](https://github.com/career-ops-hq/career-ops/pull/3839)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[chore: release main](https://github.com/career-ops-hq/career-ops/pull/3117)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。
- 来源：[Hmbown/Codewhale — fetch\_url blocks all requests when DNS resolves to private IPs (fakeip proxy incompatible)](https://github.com/Hmbown/Codewhale/issues/1071)
  原文证据：Users behind fakeip proxies cannot use \`fetch\_url\` at all.
  关联 PR：[fix(fetch\_url): add allow\_private\_ip\_hosts to skip DNS-resolved IP check](https://github.com/Hmbown/Codewhale/pull/1162)；未合并，交叉引用不等于确认修复。
  关联 PR：[fix(fetch\_url): add proxy DNS opt-in](https://github.com/Hmbown/Codewhale/pull/1103)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC008 编码反射封堵、响应头过滤与真实流式大小限制

对应需求：R2；分类：响应安全；状态：未执行。

增量价值（模型判断）：新增能区分编码的哨兵及真实分块响应的累计大小和跨块扫描边界；现有源码已覆盖多种模拟响应反射。

前置条件：固定 Action 使用虚构凭证，包含适合区分 base64 与 base64url 的字节。；受控 HTTPS 上游可生成响应体、响应头和分块响应；明确 response\_max\_bytes。

1. 返回干净合法响应及非白名单头，验证成功对照和头过滤。
2. 在响应体和白名单头中分别反射原文、base64、base64url、完整及选择性 percent 编码凭证。
3. 返回恰好达到上限及超过上限的响应，包含分块跨边界的响应和秘密反射。

**预期结果：** 干净且大小合法的响应可见，非白名单头被移除。秘密反射返回 RESPONSE\_SECURITY\_VIOLATION，Agent 看不到泄露内容；真实超限返回 RESPONSE\_TOO\_LARGE，不释放超限内容。

迁移理由（模型建议）：由 PRD 的响应扫描和大小限制直接导出；不借用网络 issue 证明反射泄密。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-broker/tests/reflected\_secret.rs:91
  源码引文：    let body = SECRET         .iter()         .flat\_map(\|byte\| format!("%{byte:02x}").into\_bytes())         .collect();     assert\_eq!(         run\_with\_reflection(body).await,         "RESPONSE\_SECURITY\_VIOLATION"     );；构造完整 percent 编码并断言安全拒绝；没有实际流式传输触发。
- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-broker/tests/adversarial\_http.rs:136
  源码引文：    broker         .fake         .push\_response(Err(UpstreamError::ResponseTooLarge));     let meta = common::execute\_meta(&amp;token, &amp;action\_id, version);     let response = execute\_with\_meta(&amp;broker, meta, b"{}").await;     assert\_eq!(response.err\_code(), "RESPONSE\_TOO\_LARGE");；检查注入超限错误后的映射，不等于读取真实响应并实施上限。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC009 包装替换成功及失败原子性

对应需求：R3；分类：密码与恢复；状态：未执行。

增量价值（模型判断）：新增错误 proof、提交前失败及内部数据不变性验证；已有 CLI 源码主要覆盖成功替换后的旧、新材料行为。

前置条件：已解锁含虚构凭证的 vault，保存当前密码和恢复密钥。；隔离环境可在包装提交前注入写入或事务失败；预先记录 VRK 标识或可验证的不变性证据、凭证密文和可用 Action。

1. 以错误当前密码尝试密码变更和恢复轮换，检查退出状态及持久状态。
2. 使用正确 proof，在包装事务提交前注入失败；移除故障并重启，检查原材料仍能解锁。
3. 正常变更密码并轮换恢复密钥，验证旧材料拒绝、新材料可用且新恢复密钥只显示一次。
4. 使用新恢复密钥完成丢失密码后的密码替换，并执行原 Action；比较 VRK 和凭证数据。

**预期结果：** 认证失败或提交前失败不报告成功，原包装仍完整可用。正常提交后旧材料失效，新材料有效；恢复轮换要求当前密码。新恢复密钥只展示一次，VRK 与 Credential 数据未轮换，原 Action 保持可用。

迁移理由（模型建议）：只迁移认证失败后部分修改及错误完成提示的故障条件。所给补丁将 shell 切换移到卸载之前，但裸 exit 不能作为正确非零退出码的依据；Rekey 仍按自己的错误契约验收。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-cli/tests/cli\_blackbox.rs:568
  源码引文：    let output = run(         &amp;rekey\_bin(),         &amp;\["--state-dir", state, "unlock", "--password-stdin"\],         Some(&amp;format!("{PASSWORD}\\n")),     );     assert\_eq!(output.status, 3, "stderr: {}", output.stderr);     let output = run(         &amp;rekey\_bin(),         &amp;\["--state-dir", state, "unlock", "--password-stdin"\],         Some(&amp;format!("{NEW\_PASSWORD}\\n")),     );     assert\_eq!(output.status, 0, "{}", output.stderr);；验证成功变更后旧密码拒绝、新密码成功；没有注入包装替换失败，也没有直接断言 VRK 不变。
- 来源：[ohmyzsh/ohmyzsh — Uninstalling ohmyzsh: must abort on invalid password](https://github.com/ohmyzsh/ohmyzsh/issues/6581)
  原文证据：Because of this, the uninstall was only partially successful, however the switch back to original shell failed.
  关联 PR：[Fix: abort uninstall when unable to change shell](https://github.com/ohmyzsh/ohmyzsh/pull/10357)；已合并，交叉引用不等于确认修复。
### TC010 锁定可读、并发追加下稳定分页与安全导出

对应需求：R4；分类：审计；状态：未执行。

增量价值（模型判断）：新增分页期间并发追加及完整集合核对、body/header 哨兵和非空导出目标保留；已有源码覆盖静态快照序号约束及安全导出的一部分。

前置条件：存在多页审计事件，独立操作可持续追加事件；测试请求含虚构 body、header、凭证和 capability 哨兵。；准备新导出路径、已有非空文件和指向非空文件的符号链接。

1. 获取第一页及快照序号，在读取后续页期间追加事件；固定快照完整遍历并核对预先记录的事件集合。
2. 锁定 broker 后继续查询和导出，检查页面上限及敏感字段。
3. 导出到新路径，检查 JSONL 与权限；对已有文件和符号链接重复导出并比较内容。

**预期结果：** 锁定状态可读脱敏审计。固定快照无重复、无遗漏，新增事件不混入旧快照，页面有界。输出不含秘密、body、header、capability、resource ID 或参数哈希；新文件为 0600 JSONL，已有文件及链接目标保持不变，拒绝时不报告导出成功。

迁移理由（模型建议）：直接验证基础契约，缺少历史来源不影响需求优先级。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-cli/tests/cli\_blackbox.rs:354
  源码引文：    assert\_eq!(continued\_page\["snapshot\_max\_sequence"\], snapshot);     assert!(         continued\_page\["events"\]             .as\_array()             .unwrap()             .iter()             .all(\|event\| {                 event\["sequence"\].as\_u64().unwrap() &lt; before                     &amp;&amp; event\["sequence"\].as\_u64().unwrap() &lt;= snapshot             })     );；检查续页属于原快照；没有在分页期间追加事件，也未核对完整集合的重复和遗漏。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC011 JWT 精确映射、防重放及策略更新撤销

对应需求：R5；分类：工作负载身份；状态：未执行。

增量价值（模型判断）：新增 JWT 验签、身份映射、重启和策略激活端到端边界；已有恢复测试直接操作消费摘要。

前置条件：使用静态 Ed25519 或 RS256 公钥与精确身份映射，不默认纳入源码独有 JWKS。；准备合法、错误签名及映射不匹配 JWT；备份在合法 JWT 已消费后创建，格式匹配目标二进制。

1. 经 agent.sock 使用合法 JWT 铸造有界会话，不提供 Admin step-up；错误签名和不匹配身份作为拒绝对照。
2. 重复提交已消费 JWT；重启并解锁后重复提交；恢复含消费记录的备份后再提交。
3. 以另一个合法 JWT 铸造会话，重试完全相同策略包后执行，再激活合法新版本后执行。

**预期结果：** 仅有效签名和精确身份匹配可铸造有界会话。已消费 JWT 在运行中、重启及包含消费记录的备份恢复后均拒绝；同包重试保留会话，新版本激活撤销工作负载会话。

迁移理由（模型建议）：直接覆盖身份契约；不要求恢复消费前备份仍保留未来消费记录。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-vault/tests/backup\_restore.rs:127
  源码引文：    let replay = handle         .consume\_workload\_token\_before(             \[0x5a; 32\],             4\_102\_444\_800\_000,             AuditDraft {                 request\_id: None,                 session\_id: None,                 action\_id: None,                 action\_version: None,                 credential\_id: None,                 credential\_version: None,                 authorization: None,                 approval: None,                 event\_type: event\_type::SESSION\_CREATED,                 outcome: outcome::SUCCESS,                 reason\_code: "workload-attested".to\_owned(),                 upstream\_status: None,                 latency\_ms: None,             },             None,         )         .await         .unwrap\_err();     assert!(matches!(replay, AuthorityError::WorkloadIdentityInvalid));；恢复后重复消费相同摘要并断言拒绝；不提交实际 JWT，也不验证身份映射或策略变更。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC012 默认拒绝出站与启动前置条件失败关闭

对应需求：R8；分类：Linux Agent 启动器；状态：未执行。

增量价值（模型判断）：新增有效拓扑中的实际网络、后代隔离及缺失依赖验证；已有源码只覆盖默认共址 socket 拒绝。

前置条件：仅在支持该 launcher 的 Linux 目标版本验证 linux-netns-v1，准备 bubblewrap 和独立 agent socket。；子进程及后代可写启动标记、尝试网络和 IPC；另备缺失 bubblewrap 环境及默认共址 socket 配置。

1. 以有效独立 socket 启动子进程，尝试未经允许的 IP 出站，并执行合法 Agent IPC 对照。
2. 让子进程及后代尝试访问 Admin socket，检查可见性和权限。
3. 在默认共址 socket 和缺失 bubblewrap 条件下分别启动，检查退出状态及启动标记。

**预期结果：** 有效 Linux 拓扑阻止未经允许的 IP 出站，Agent IPC 可用且不取得 Admin 权限。共址 socket 或缺失 bubblewrap 时不执行子命令、不退回普通启动；已给出的默认共址配置保持退出码 2。结论仅适用于该 Linux 参考拓扑。

迁移理由（模型建议）：来自 PRD 的 Linux 专用启动器契约，不要求 macOS launcher 或通用 G2。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rekey/crates/rekey-cli/tests/cli\_blackbox.rs:811
  源码引文：            "agent-run",             "--",             "/bin/echo",             "blocked",         \],         None,     );     assert\_eq!(output.status, 2, "stderr: {}", output.stderr);     assert!(         output.stderr.contains("disjoint")             \|\| output.stderr.contains("INVALID\_INPUT")             \|\| output.stderr.contains("invalid launch plan"),         "stderr: {}",         output.stderr     );     assert!(!output.stdout.contains("blocked"));；未提供独立 socket，断言退出 2 且子命令未输出标记；没有建立有效 namespace 或触发出站连接。
- 来源：PRD 基础用例，没有历史 issue 支撑。

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：本方案是待执行草稿，coverage 仅比较本次提供的 T1–T4 源码，不代表整个仓库，也不表示测试已运行。尚缺 AES-256-GCM 与二进制 AAD 的 vault/credential/version/purpose 绑定、授权及审计检查后才解密、每请求解密一次和使用后清零的直接验证；明文哨兵检查不足以证明这些内部契约。
- R1：尚未完整覆盖隐藏交互密码提示、全部凭证类型和诊断出口。未导出 shell 变量与包含密码/恢复密钥的 proof 的边界仍未澄清，本草稿以直接 stdin 输入规避该歧义。macOS Admin UI 不纳入 CLI 范围，其人工认证后的 reveal/copy 不作为 Agent 泄密。
- R2：尚缺全部 IPv4/IPv6 非公共范围、混合 DNS 回答、超时及并发资源限制矩阵；编码反射尚未覆盖每种连接器生成值。现有方案优先验证代表性生产传输边界。
- R3：目标二进制尚未确定，alpha.2 格式 9 与源码格式 10 必须分别验收；alpha.2 旧备份接受规则未明确。尚缺独立的离线恢复密钥验收、错误 proof、哈希不匹配、后续凭证损坏及恢复中断用例；T4 已有其中若干实际断言，不能把它们视为缺失或已执行。提交后确认丢失的故障结果尚未由 PRD 明确，不应一律要求旧密码仍有效。
- R4：尚缺导出中断、磁盘错误、过滤交集精确性、分页异常参数及 vault 生命周期内 append-only 验证。不增加未实现的审计删除、配置保留期、远程投递、SIEM、WORM 或法律保全要求。
- R5：尚缺并发使用次数竞争、全部 OIDC/SPIFFE/Kubernetes/CI-cloud 身份映射和 Ed25519/RS256 验签边界，以及策略封印详细篡改矩阵。源码独有 GitHub JWKS 需明确选择开发版本后另行规划；失败授权是否消耗次数应按目标版本实际契约确认。
- R6：尚缺双 grant 独立性、并发消耗次数、规范参数等价与不等价矩阵，以及执行失败对使用次数的精确定义。不规划跨锁定/重启审批恢复、托管审批、通知 UI 或私钥托管；本地签名、pending/get 工具仅在开发源码范围明确后补充。
- R7：尚缺 GitHub App 的 1–16 精确仓库边界、有界 issue 创建、typed rotation、Admin 转发签名仓库 delta、只读有界重试及其 lease 生命周期。Vault 来源尚缺 Action 失败后的撤销处理和更完整的 revoke 故障矩阵；fixture 验证不等于公开动态租约实测，崩溃后清理不在承诺范围。源码独有 Keycloak、MCP 和 IO-free SDK 投影不自动纳入 alpha.2 CLI 要求。
- R8：尚缺 Linux 依赖版本、显式允许出站规则及 launcher 生命周期清理验收；需确认目标二进制是否包含该 launcher。macOS 不执行 Linux 隔离用例，参考拓扑结果不得提升为默认 G1 产品的通用 G2 保证。
- 待确认：本次 CLI 测试针对已发布 alpha.2（存储格式 9），还是开发源码（格式 10）？原文同时描述两者；源码独有的 JWKS、Keycloak exchange、MCP 和本地审批签名工具不能直接作为 alpha.2 要求。
- 待确认：“Credentials never appear in ... process arguments, environment variables”与示例通过 STEP\_UP\_PROOF、CAPABILITY\_FROM\_SECURE\_STORAGE 等 shell 变量传值之间，需明确普通未导出的 shell 变量是否允许，以及 step-up proof 包含密码或恢复密钥时的适用边界。
- 待确认：当前输入指定 cli；源码独有的 macOS 14+ Admin UI 是否明确排除在本次测试范围外？其人工认证后显示、复制凭证的能力不应被误判为 Agent API 可读取凭证。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
