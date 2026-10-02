# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是依据 PRD 和同类产品历史问题生成的测试建议，不是目标产品的已确认缺陷。

产品形态：desktop；语料：14730 条；本次选入：12 条；测试建议：12 条。

基础用例来自 PRD，历史启发用例附 issue 来源。PR 证据按来源单独标注；未采集评论。

已有覆盖只指所提供测试文件中的源码断言，未执行测试；未检出不等于全仓库无覆盖。

## 需求与检索范围

- **R1 离线安装、固定运行时与自动启动**：2. Install and open DSH Desk. The pinned Harness runtime starts automatically. 3. Choose a model provider in the official Harness onboarding dialog and send your first task.  No system Node.js installation, npm setup, port selection, or terminal command is required.
  组合检索：runtime AND missing OR offline AND startup AND failure OR bundled AND version AND mismatch；选入候选 3 条。
- **R2 私有状态隔离与进程管理边界**：- isolates state in a private \`DSH\_HOME\` instead of modifying an existing CLI setup; - waits for a real HTTP health check on the launch-token loopback URL; - grants the remote Harness page no Tauri IPC, shell, or filesystem capability; - constrains navigation to the exact runtime origin and opens external links in the system browser; - supervises only the process group it started;
  组合检索：process AND kill OR state AND isolation AND overwrite OR process group AND unrelated；选入候选 4 条。
- **R3 启动健康检查与严格本地地址验证**：- waits for a real HTTP health check on the launch-token loopback URL;
  组合检索：health AND timeout OR loopback AND token AND invalid OR HTTP AND readiness AND failure；选入候选 1 条。
- **R4 运行时页面权限隔离与导航约束**：- grants the remote Harness page no Tauri IPC, shell, or filesystem capability; - constrains navigation to the exact runtime origin and opens external links in the system browser;
  组合检索：navigation AND escape OR IPC AND unauthorized OR external AND browser AND failure；选入候选 1 条。
- **R5 插件安装前审查与可信来源边界**：- exact package, resolved version, source, and integrity; - lifecycle scripts and declared file/network/command/credential needs; - compatibility with the pinned Desktop and Harness versions; - disable, removal, and profile restoration boundaries.  Catalog failure never falls back to an unreviewed global search. The Plugins window can open the community registry at \[plugin.dshdesk.com\](https://plugin.dshdesk.com/); copied \`dsh plugin add\` commands are parsed into the same review flow, and that site is not the trusted catalog.
  组合检索：plugin AND integrity OR catalog AND failure AND fallback OR command AND parse AND bypass；选入候选 1 条。
- **R6 插件生命周期一致性与恢复边界**：- disable, removal, and profile restoration boundaries.
  组合检索：restore AND overwrite OR plugin AND remove AND failure OR plugin AND update AND parity；选入候选 1 条。
- **R7 签名更新与失败恢复**：\| Failed update recovery \| User-managed \| Project-dependent \| Signed updater contract and explicit recovery path \|
  组合检索：update AND failure OR signature AND invalid OR recovery AND interrupted；选入候选 0 条。
- **R8 每日上游兼容性检测且不自动替换用户运行时**：A scheduled workflow also installs the newest npm candidate in an isolated CI workspace. It reports drift without silently changing the runtime on user machines.
  组合检索：runtime AND drift OR compatibility AND regression OR update AND silent AND replacement；选入候选 1 条。

## 潜在遗漏（所给文件中未检出）

### TC001 无系统 Node.js 的离线安装、固定运行时与首次任务

对应需求：R1；分类：安装与启动；状态：未执行。

增量价值（模型判断）：新增真实安装包、断网、无系统运行时和首次任务验证；所给 T1–T3 未发现同等触发与断言。

前置条件：分别标记验收构建：alpha.13 对应 Harness 0.1.0-rc.6；alpha.14 对应 Harness 0.1.5-rc.2，不混用结果。；准备 macOS Apple Silicon、macOS Intel、Windows x64、Linux x64 干净环境；Linux 分别准备 AppImage 和 deb。；未安装系统 Node.js/npm，安装包已下载；安装和首次启动期间断网。

1. 通过图形界面安装并打开应用，不执行终端命令或选择端口。
2. 观察自动启动，核对实际运行的随包 Node 24、Harness 版本及可执行文件位置。
3. 退出后再次离线启动。
4. 恢复网络，在官方 onboarding 中配置测试提供商并发送首次任务。

**预期结果：** 离线安装和本地启动不要求下载运行时或安装系统 Node.js/npm；实际运行时与该构建声明一致；再次启动可用；联网配置后首次任务获得响应。记录耗时，不以尚未定义的 60 秒阈值判定。

迁移理由（模型建议）：优先验证 PRD 基础契约。历史报告及相关 PR 描述提示必需依赖遗漏的风险；补丁中的测试只检查 Python 安装参数和标记，不能证明目标安装包完整。只迁移依赖完整性触发条件，不引入 spaCy、NLP 或首次启动在线配置依赖的设计。

- 来源：[tinyhumansai/openhuman — bug: spaCy runtime missing 'click' module on Windows — NLP extraction broken](https://github.com/tinyhumansai/openhuman/issues/4687)
  原文证据：The managed spaCy runtime fails on Windows with \`ModuleNotFoundError: No module named 'click'\`, causing all NLP/entity extraction to fall back and the memory tree wiki structure to degrade.
  关联 PR：[fix(react-ui): surface layered pipeline status in Data Sync (GH-4690)](https://github.com/tinyhumansai/openhuman/pull/5113)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(runtime\_python\_server): pin click in bundled spaCy venv (Windows)](https://github.com/tinyhumansai/openhuman/pull/4816)；已合并，交叉引用不等于确认修复。
### TC002 桌面私有 DSH\_HOME 不改写既有 CLI 状态

对应需求：R2；分类：状态隔离；状态：未执行。

增量价值（模型判断）：T3 仅为测试 CLI 注入临时 DSH\_HOME，没有验证桌面目录选择或既有 CLI 状态不变。

前置条件：支持平台上已有独立 Harness CLI 配置和会话，保存文件清单与内容摘要。；桌面尚未初始化；使用测试配置和虚构凭据。

1. 启动桌面，完成 onboarding、创建会话并修改设置。
2. 核对桌面实际使用的 DSH\_HOME 与 CLI 状态目录不同。
3. 退出并重启，检查桌面状态。
4. 比较既有 CLI 文件与基线。

**预期结果：** 桌面状态写入私有 DSH\_HOME，重启后保留；既有 CLI 配置和会话未被改写。

迁移理由（模型建议）：直接覆盖私有状态契约，不依赖历史案例。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC003 精确 origin 导航与外部浏览器分流

对应需求：R4；分类：导航安全；状态：未执行。

增量价值（模型判断）：所给目标测试文件未发现精确 origin 或实际导航分流断言；其他产品的主机匹配测试不能代替目标覆盖。

前置条件：Harness 已就绪，记录本次运行时协议、主机和端口。；准备同 origin 路径链接及不同协议、主机、端口的无害 HTTP(S) 链接、重定向和新窗口入口。

1. 点击同 origin 内部链接。
2. 分别点击协议、主机或端口不同的链接。
3. 触发到外部地址的重定向和新窗口请求。
4. 检查运行时 webview 与系统浏览器实际承载的页面。

**预期结果：** 同 origin 页面留在运行时 webview；外部 HTTP(S) 链接进入系统浏览器，外部内容不能借直接导航、重定向或新窗口进入运行时 webview；不以仅主机名相同判定内部地址。

迁移理由（模型建议）：该来源是功能请求，只借用导航分流条件。相关 PR 的 Slack OAuth 主机扩展与目标精确 origin 要求不同，不迁移其允许列表、SSO 或媒体权限。

- 来源：[tinyhumansai/openhuman — Webview: Slack full end-to-end parity with the native app](https://github.com/tinyhumansai/openhuman/issues/1016)
  原文证据：While Slack is a CDP-migrated provider (Network MITM + IDB + DOM snapshot scanner), there are gaps versus the native app experience: Huddle popup whitelisting needs verification under all edge cases, and end-to-end coverage of all Slack features has not been formally validated.
  关联 PR：[fix(webview/slack): first-load + Google auth (\#1036)](https://github.com/tinyhumansai/openhuman/pull/1249)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(webview-accounts): retry data-dir purge so CEF handle race doesn't leak cookies (\#1076)](https://github.com/tinyhumansai/openhuman/pull/1081)；已合并，交叉引用不等于确认修复。
  关联 PR：[fix(webview/slack): media perms + deep-link isolation (\#1074)](https://github.com/tinyhumansai/openhuman/pull/1080)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。
### TC004 每日隔离检查候选并报告漂移，不改变用户固定运行时

对应需求：R8；分类：上游兼容性；状态：未执行。

增量价值（模型判断）：所给 T1–T3 未发现每日调度、候选隔离或用户运行时不变的同等覆盖。

前置条件：准备隔离 CI 工作区及不同于固定版本的不兼容候选。；保存用户运行时版本、文件摘要及固定版本基线。；可读取每日调度配置和受控执行产物。

1. 核对每日调度配置。
2. 受控触发同一流程，分别检查固定版本与最新候选。
3. 观察候选不兼容时的公开报告及平台、版本标识。
4. 重新启动用户应用，比较运行时版本和文件摘要。

**预期结果：** 每日调度配置与受控执行证据明确区分；候选只在隔离工作区安装；报告区分固定版本与候选结果；候选检测不静默替换用户运行时。

迁移理由（模型建议）：来源是依赖锁定请求，相关补丁展示版本固定但没有每日检测断言；仅借用上游版本变化的触发条件，调度、隔离和报告要求来自 PRD。

- 来源：[janhq/jan — feat: lock all of the dependencies](https://github.com/janhq/jan/issues/6541)
  原文证据：Currently, our build relies on dependencies that are not fully locked.
  关联 PR：[fix: lock all of the dependencies](https://github.com/janhq/jan/pull/6561)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC005 插件包路径不能越过目标声明的安装范围

对应需求：R5；分类：插件文件边界；状态：未执行。

增量价值（模型判断）：新增目标实际包格式下的目录外无写入和既有插件不变断言；所给目标测试未发现同等覆盖。

前置条件：仅使用目标实际支持的包格式，在隔离临时目录测试。；准备含合法条目及规范化后越界条目的无害包；保存目录外文件和既有插件基线。；执行前确认安装写入边界，不假定目标采用 NuGet 或 ZIP。

1. 通过正常审查流程尝试安装越界包。
2. 观察失败结果，核对实际写入位置、目录外文件和失败残留。
3. 检查既有插件未被覆盖。
4. 安装仅含合法路径的对照包。

**预期结果：** 越界条目不能通过安装解包写入或覆盖允许范围外的文件；失败可观察，既有插件不被误改；合法对照包可正常安装。准确写入范围需以目标契约确认。

迁移理由（模型建议）：历史材料报告路径穿越，相关补丁展示规范化路径检查；其测试断言安装失败，但包内容未提供且没有目录外无写入断言。只迁移不可信路径输入，不将报告根因视为目标事实，也不把来源、完整性审查等同于路径安全。

- 来源：[DevToys-app/DevToys — Critical Path Traversal (Zip Slip) Vulnerability in DevToys Extension Installation.](https://github.com/DevToys-app/DevToys/issues/1641)
  原文证据：A working proof-of-concept has been developed demonstrating: - Successful extraction of files outside the plugin directory - Ability to write to Documents folder - Bypass of existing security checks
  关联 PR：[Updated extensions manager to handle CWE-22 &amp; CWE-23](https://github.com/DevToys-app/DevToys/pull/1643)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。

## 补充边界

### TC006 真实 HTTP 探测携带启动令牌且只接受严格 loopback 地址

对应需求：R3；分类：启动就绪；状态：未执行。

增量价值（模型判断）：新增真实 HTTP 请求、等待顺序和网络失败验证；现有测试仅检查请求目标与状态行。

前置条件：准备可控制就绪输出、HTTP 响应和请求记录的本地运行时夹具。；使用虚构启动令牌；可模拟连接拒绝、401、403、200 和持续无响应。

1. 输出合法就绪行，暂不启动 HTTP 服务，观察桌面是否等待。
2. 启动要求本次令牌的服务，依次返回 401、403 和 200，核对请求目标及页面加载时机。
3. 分别输出 0.0.0.0、LAN 地址及带伪造前缀的就绪行，观察是否被拒绝。
4. 保持服务无响应，观察启动失败反馈。

**预期结果：** 日志或端口监听不等于就绪；探测请求包含本次启动令牌，401/403 不被接受；合法地址的 HTTP 就绪响应后才加载 Harness。非法地址不被加载；持续无响应不被显示为启动成功，具体超时标准待补充。

迁移理由（模型建议）：历史报告涉及非 loopback 模式的认证探测失败，相关 PR 改用免认证端点；目标仍须遵守带启动令牌的 loopback 契约，不能照搬端点或引入 LAN、远程 API、WebSocket 功能。引用关系本身不证明 PR 修复了该 issue。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/dsh-desk/src-tauri/src/runtime\_supervisor\_tests.rs:33
  源码引文：let url = Url::parse("http://127.0.0.1:43210/?token=launch-token").unwrap();     assert\_eq!(http\_request\_target(&amp;url), "/?token=launch-token");     assert!(http\_status\_is\_ready(b"HTTP/1.1 302 Found\\r\\n"));     assert!(http\_status\_is\_ready(b"HTTP/1.1 200 OK\\r\\n"));     assert!(!http\_status\_is\_ready(b"HTTP/1.1 401 Unauthorized\\r\\n"));     assert!(!http\_status\_is\_ready(b"HTTP/1.1 403 Forbidden\\r\\n"));；覆盖令牌请求目标及状态判断，没有实际连接服务器或验证桌面等待过程。
- 来源：[debpalash/VoiceStudio — Realtime events WebSocket never opens in LAN-share/remote mode (health probe drops auth → 401)](https://github.com/debpalash/VoiceStudio/issues/450)
  原文证据：\`res.ok\` is false → \`throw\` → \`.catch\` → \`scheduleReconnect()\` loops forever → \`openWebSocket()\` is never reached → the WebSocket never opens.
  关联 PR：[fix(realtime): probe auth-exempt /health, not gated /model/status](https://github.com/debpalash/VoiceStudio/pull/451)；已合并，交叉引用不等于确认修复。
### TC007 运行时页面无法调用桌面 IPC、shell 或文件能力

对应需求：R4；分类：权限隔离；状态：未执行。

增量价值（模型判断）：新增实际远程页面调用和副作用断言；已有脚本只静态排除 updater 权限。

前置条件：在实际远程 Harness webview 中注入受控测试脚本。；准备无害测试命令、临时标记文件及副作用记录。

1. 从运行时页面尝试调用 Tauri IPC，包括文件读写、shell 和 updater 命令。
2. 观察调用返回或能力拒绝。
3. 检查文件读取结果、文件内容、命令记录和更新状态。

**预期结果：** 调用不可用或被拒绝；页面未获得文件内容，文件未改写，命令未执行，更新未启动。

迁移理由（模型建议）：直接覆盖 PRD 权限边界；导航约束不能单独证明 IPC 隔离。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/dsh-desk/scripts/test-updater-contract.mjs:76
  源码引文：assert(     permissions.every((permission) =&gt; {       const identifier = typeof permission === "string" ? permission : permission?.identifier;       return typeof identifier !== "string" \|\| !identifier.startsWith("updater:");     }),     \`${name} must not expose updater commands to a WebView\`,   );；验证 capability 权限标识，不验证实际远程页面，也不覆盖全部 IPC、shell 和文件能力。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC008 安装前审查完整信息并保持审查对象与安装对象一致

对应需求：R5；分类：插件审查；状态：未执行。

增量价值（模型判断）：新增实际审查展示、确认前无副作用和安装对象一致性。

前置条件：准备目标支持的测试插件，提供精确版本、来源、完整性、生命周期脚本及文件、网络、命令、凭据需求声明。；准备与固定 Desktop 或 Harness 不兼容的候选；可记录安装写入和脚本执行。

1. 从 Plugins 进入审查，核对全部信息及禁用、移除、profile 恢复边界。
2. 取消审查，检查安装副作用。
3. 审查不兼容候选，核对兼容性结论对应本次固定版本。
4. 重新审查兼容候选并确认安装，比较实际安装对象与审查信息。

**预期结果：** 确认前展示全部承诺信息；取消不执行安装或生命周期脚本；不兼容候选不显示为兼容；安装的包、版本、来源和完整性与确认时一致。不兼容候选是否可强制安装需另行明确。

迁移理由（模型建议）：PRD 基础审查契约不应因缺少历史 issue 而遗漏。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/dsh-desk/scripts/test-plugin-catalog.mjs:32
  源码引文：assert(entry.source === \`${entry.package}@${entry.version}\`, \`${entry.id} must pin an exact source\`);   assert(entry.version === harnessVersion, \`${entry.id} must match the pinned Harness family\`);   assert(\["available", "bundled"\].includes(entry.status), \`${entry.id} has an invalid status\`);   assert(entry.trust?.reviewedAt &amp;&amp; entry.trust?.evidence?.length &gt; 0, \`${entry.id} lacks trust evidence\`);   assert(entry.capabilities?.length &gt; 0, \`${entry.id} lacks a capability summary\`);；只验证目录元数据，未触发审查展示、安装确认或实际完整性核对。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC009 目录失败不回退全局搜索，复制命令统一进入审查

对应需求：R5；分类：插件来源边界；状态：未执行。

增量价值（模型判断）：新增目录故障、真实输入解析和执行边界；现有检查仅匹配源码标识。

前置条件：能模拟可信目录读取失败。；准备正常 dsh plugin add 文本和附带无害 shell 动作的文本。；可观察网络请求、审查窗口和命令副作用。

1. 使目录失败，打开 Plugins 并尝试查找插件。
2. 通过窗口打开社区 registry，观察承载位置与信任提示。
3. 粘贴正常安装命令，检查是否进入同一审查流程。
4. 粘贴附带 shell 动作的文本，检查拒绝或解析结果及副作用。

**预期结果：** 目录失败有反馈且不发起未审查的全局搜索；社区站点由系统浏览器打开，不被当作可信目录；可解析输入进入审查；文本不被直接作为 shell 执行，附带动作没有副作用。

迁移理由（模型建议）：直接覆盖目录故障与命令入口契约；所给历史材料没有支持这两个边界的相关案例。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/dsh-desk/scripts/test-plugin-catalog.mjs:75
  源码引文：assert(   sourceParser.includes("clipboardPluginSource") &amp;&amp;     sourceParser.includes("PLUGIN\_ADD\_PREFIX") &amp;&amp;     sourceParser.includes("parseAddOperand") &amp;&amp;     !sourceParser.includes("(?&lt;!") &amp;&amp;     !sourceParser.includes("(?&lt;="),   "plugin source parser must recognize copied install commands without lookbehind", );；未输入真实命令，也没有目录失败、审查跳转或 shell 副作用断言。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC010 禁用、移除与失败恢复保持 profile 和运行时一致

对应需求：R6；分类：插件生命周期；状态：未执行。

增量价值（模型判断）：新增实际禁用、移除、恢复一致性和期间写入；现有测试只判断结果标志是否要求重启。

前置条件：安装可观察生效状态的测试插件，保存 profile、关联文件和运行时基线。；准备在修改 profile 后失败的安装或更新夹具。；记录目标审查界面声明的恢复与文件保留边界。

1. 禁用插件，按支持方式重新启用，再移除，逐步比较状态与实际生效行为。
2. 重新建立基线，触发修改后的失败，观察恢复结果和运行时重启。
3. 在恢复期间修改一项无关设置，记录最终值及冲突反馈。
4. 模拟不可恢复结果，检查是否仍宣告恢复成功或重启脏 profile。

**预期结果：** 禁用、移除后插件不再生效，界面与 profile、运行时一致；宣告恢复成功时实际状态符合声明边界；不可恢复结果明确反馈，不显示成功恢复。并发设置保留或覆盖须按补充政策验收，当前不预设全部保留。

迁移理由（模型建议）：历史提炼未确定根因，只借用恢复涉及关联状态及期间写入的条件。相关 PR 正文可支持这类边界，但恢复测试补丁缺失或截断，不能据此认定没有测试；不引入 SQLite、WebDAV 或同步功能。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/dsh-desk/src-tauri/src/runtime\_supervisor\_tests.rs:133
  源码引文：fn successful\_rollback\_still\_restarts\_the\_restored\_profile() {     assert!(should\_restart\_after\_plugin(         true,         &amp;Ok(plugin\_result(false, true, false)),     )); }；人为构造回滚标志，没有执行恢复或检查恢复后的 profile、文件和运行时。
- 来源：[farion1231/cc-switch — \[Bug\] Backup and sync follow-up audit finds fidelity and atomicity gaps](https://github.com/farion1231/cc-switch/issues/6129)
  原文证据：The current paths can lose SQLite metadata/value fidelity, reject a valid empty export, mix database and Skills snapshots from different moments, overwrite device-local cursors/writes, allow restore operations to overlap, and leave managed live files/process caches stale after a successful database replacement.
  关联 PR：[fix(sync): harden sync and restore consistency](https://github.com/farion1231/cc-switch/pull/6147)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(backup): preserve SQL fidelity and recovery safety](https://github.com/farion1231/cc-switch/pull/6146)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC011 签名更新接受合法载荷并拒绝篡改，中断后提供恢复路径

对应需求：R7；分类：更新与恢复；状态：未执行。

增量价值（模型判断）：新增实际签名载荷、安装与中断恢复；静态公钥格式检查不等于签名验证。

前置条件：隔离更新通道准备有效签名包、篡改包、错误签名包和可中断传输。；记录应用版本、Harness 版本与私有状态。；Windows alpha 安装器可无 Authenticode；独立验收 updater 载荷签名。

1. 安装有效签名更新，检查版本和运行时启动。
2. 恢复基线，分别尝试篡改包和错误签名包。
3. 恢复基线，分别在下载和安装交接阶段中断。
4. 重新打开应用或按实际恢复指引操作，记录最终版本与状态。

**预期结果：** 有效签名更新可完成；错误签名或篡改载荷不被安装；中断后有可观察的失败状态及明确恢复指引。具体恢复版本、数据保留和操作步骤需补充契约，不预设自动回滚。

迁移理由（模型建议）：没有提供 R7 历史来源，仍优先覆盖签名更新与失败恢复要求。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/dsh-desk/scripts/test-updater-contract.mjs:66
  源码引文：assert(publicKeyBytes.length === 42, "Updater public key payload must be 42 bytes"); assert(   publicKeyBytes\[0\] === 0x45 &amp;&amp; \[0x44, 0x64\].includes(publicKeyBytes\[1\]),   "Updater public key uses an unsupported minisign algorithm", );；验证公钥格式，没有输入更新载荷或触发失败恢复。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC012 退出与重启回收本实例进程组并保留外部进程

对应需求：R2；分类：进程生命周期；状态：未执行。

增量价值（模型判断）：新增真实进程组清理和外部进程存活验证；已有测试只防止重启后复用旧退出确认。

前置条件：各支持平台准备带 PID、端口和心跳记录的受控运行时及后代。；独立启动 CLI 服务和同名无关进程。；夹具可让直接子进程先退出而后代继续存活。

1. 由桌面启动运行时，分别触发正常退出和父进程先退出后的清理。
2. 重新启动并触发目标已有的运行时重启流程。
3. 检查旧组后代、端口和心跳；检查新实例与外部进程。
4. 退出新实例，核对最终资源释放。

**预期结果：** 清理完成后本实例拥有的后代终止、心跳停止、端口释放；重启后新实例可用；独立 CLI 和同名无关进程持续存活。仅握手或请求成功不能代替实际清理结果。

迁移理由（模型建议）：借用后代遗留、释放句柄不等于终止及按名称误杀的历史触发条件。相关 PR 测试分别检查其他产品的任务重试或拥有的子进程，不是 DSH Desk 覆盖；不引入任务重试、Ollama 或广泛启动清理功能。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/dsh-desk/src-tauri/src/runtime\_supervisor\_tests.rs:202
  源码引文：handle         .restart()         .expect("restart must queue while the supervisor channel is open");     assert\_eq!(         handle.shutdown\_blocking\_with\_timeout(Duration::ZERO),         Err("runtime supervisor did not accept shutdown before the deadline".to\_string()),         "a queued restart must not let app quit skip the process-tree handshake"     );；触发排队重启和退出握手，没有启动真实进程或断言后代终止、外部进程存活。
- 来源：[nexu-io/open-design — \[Bug\]: same-run retry leaks the failed attempt's process group (orphaned CLI descendants accumulate)](https://github.com/nexu-io/open-design/issues/5462)
  原文证据：The retry succeeds; the run finishes \`succeeded\`. 3. The grandchild from the failed attempt is \*\*still alive\*\* — \`ps\` shows \`PPID=1\` (re-parented) and its heartbeat file keeps growing.
  关联 PR：[fix(daemon): reap the failed attempt's process group on same-run retry](https://github.com/nexu-io/open-design/pull/5463)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
- 来源：[tinyhumansai/openhuman — Bind spawned Ollama daemon lifecycle to openhuman process](https://github.com/tinyhumansai/openhuman/issues/1622)
  原文证据：End users see a stray \`ollama.exe\` in Task Manager after closing the app
  关联 PR：[test(e2e): expand e2e coverage for 12 missing high-priority flows](https://github.com/tinyhumansai/openhuman/pull/2512)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[feat(local\_ai): bind owned ollama serve lifecycle to openhuman (\#1622)](https://github.com/tinyhumansai/openhuman/pull/1638)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
- 来源：[tinyhumansai/openhuman — Windows: scoped-safe startup reap of wedged stale process (follow-up to \#3605)](https://github.com/tinyhumansai/openhuman/issues/3900)
  原文证据：An active Claude MCP client or a manually started core CLI would be terminated on every desktop startup, mid-workflow.
  关联 PR：[fix(startup-recovery): scope Windows pre-CEF reap to the wedged GUI instance (\#3900)](https://github.com/tinyhumansai/openhuman/pull/4644)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(desktop): macOS/Linux pre-CEF stale-lock reap + installer pre-install kill (\#4395)](https://github.com/tinyhumansai/openhuman/pull/4405)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(tauri): identify foreign process on core port + consent-gated force-quit (\#3331)](https://github.com/tinyhumansai/openhuman/pull/3946)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：验收版本未确定；alpha.13 与 alpha.14 必须分别标记。60 秒缺少计时条件和阈值；最低系统版本、Linux 系统依赖及缺损安装包的错误反馈未定义。所给测试未证明官方 UI 未修改或首次任务端到端覆盖。
- R2：强制终止桌面后的遗留进程处理、更新派生新桌面实例的所有权交接、清理超时与私有目录不可写的结果仍未充分覆盖。不能自行要求清理所有同名进程；T1 的握手及期限断言不证明真实资源回收。
- R3：缺少探测超时、重试及错误反馈标准。T1 接受 302 状态行，但未提供 Location 处理和重定向目的地验证证据；跨 origin 健康重定向与导航约束的衔接仍需补充。
- R4：非 HTTP 协议、下载链接及系统浏览器打开失败的处理未定义；未提供实际运行时 webview 的完整能力配置。现有静态 updater 权限检查只覆盖局部，不能证明全部 IPC 隔离。
- R5：尚未充分覆盖完整性不匹配、审查后包内容变化及生命周期脚本执行失败；缺少相应拒绝政策、不兼容候选安装政策和明确文件写入范围。实际包格式未提供，路径用例须按目标格式落实。
- R6：禁用、移除、恢复的文件保留与并发写入覆盖规则未完整提供；add/why/update/remove 与原 CLI 的完整行为对照尚未展开。历史 PR 的恢复测试补丁缺失或截断，只能说明证据不足，不能判定其没有回归测试。
- R7：明确恢复路径的入口、操作、恢复版本及数据保留标准仍待补充。macOS 发布包的 Developer ID、notarization、stapling，以及各平台真实签名更新仍需产物验证；T2 是静态契约脚本，Windows alpha 不应统一要求 Authenticode。
- R8：未提供实际每日工作流与报告，无法确认调度执行和公开产物。每次 push/PR 的 TypeScript、Rust、真实启动、离线运行时、插件 parity、onboarding 和 updater 完整矩阵未充分展开；macOS Intel 支持明确，但其常规兼容性验证要求待澄清。所有覆盖判断仅限本次提供的测试与补丁，未执行测试，未检查整个仓库。
- 待确认：测试对象是已发布的 v0.1.0-alpha.13（Harness 0.1.0-rc.6），还是仓库固定的 0.1.0-alpha.14（Harness 0.1.5-rc.2）？原文明确区分两者，不能混用验收版本。
- 待确认：“60 seconds”明确只是产品目标，尚非基准结论；是否需要设定可验收的计时起止点、机器条件及阈值？
- 待确认：支持范围为 macOS Apple Silicon 与 Intel、Windows x64、Linux x64；兼容性测试列表只明确包含 macOS arm64，macOS Intel 的验证要求需澄清。Windows alpha 明确允许无 Authenticode，不能将安装器 Authenticode 签名设为统一必过条件。
- 待确认：原文仅承诺明确的更新失败恢复路径和插件恢复边界，未给出恢复步骤、数据保留范围及失败时的结果；需补充这些验收标准。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
