# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是从同类产品历史问题迁移的测试建议，不是目标产品的已确认缺陷。

产品形态：desktop；语料：14730 条；本次选入：12 条；测试建议：7 条。

来源只含 issue 标题与正文；没有读取关联 PR 补丁或评论。根因与适用性仍需人工复核。

## 需求与检索范围

- **R1 安装后自动启动固定运行时，无需系统 Node.js 或终端配置，并通过官方引导完成首个任务**：2. Install and open DSH Desk. The pinned Harness runtime starts automatically. 3. Choose a model provider in the official Harness onboarding dialog and send your first task.  No system Node.js installation, npm setup, port selection, or terminal command is required.
  检索词：startup, dependency, onboarding, offline；选入候选 2 条。
- **R2 使用私有状态目录，不修改已有 CLI 配置**：- isolates state in a private \`DSH\_HOME\` instead of modifying an existing CLI setup;
  检索词：isolation, configuration, overwrite；选入候选 2 条。
- **R3 启动就绪以携带启动令牌的回环地址 HTTP 健康检查为准**：- waits for a real HTTP health check on the launch-token loopback URL;
  检索词：readiness, loopback, token, timeout；选入候选 2 条。
- **R4 远程页面无桌面权限，应用内导航限定运行时来源，外链交给系统浏览器**：- grants the remote Harness page no Tauri IPC, shell, or filesystem capability; - constrains navigation to the exact runtime origin and opens external links in the system browser;
  检索词：permission, origin, navigation, sandbox；选入候选 2 条。
- **R5 进程监管仅作用于应用自行启动的进程组**：- supervises only the process group it started;
  检索词：process, termination, ownership, cleanup；选入候选 1 条。
- **R6 插件安装前展示信任与兼容性信息，明确恢复边界；目录失败不得降级到未审查搜索**：Open \`DSH Desk → Plugins…\` to inspect a plugin before installation:  - exact package, resolved version, source, and integrity; - lifecycle scripts and declared file/network/command/credential needs; - compatibility with the pinned Desktop and Harness versions; - disable, removal, and profile restoration boundaries.  Catalog failure never falls back to an unreviewed global search. The Plugins window can open the community registry at \[plugin.dshdesk.com\](https://plugin.dshdesk.com/); copied \`dsh plugin add\` commands are parsed into the same review flow, and that site is not the trusted catalog.
  检索词：integrity, credential, fallback, restore；选入候选 1 条。
- **R7 更新须具备签名契约与明确的失败恢复路径**：\| Failed update recovery \| User-managed \| Project-dependent \| Signed updater contract and explicit recovery path \|
  检索词：update, signature, failure, recovery；选入候选 1 条。
- **R8 每日检查固定版本及最新上游候选版本，报告偏移而不静默替换用户运行时**：- checks the pinned version and the newest upstream candidate every day;
  检索词：compatibility, regression, version, drift；选入候选 1 条。

## 启动就绪

### TC001 HTTP 延迟就绪时不提前进入运行时页面

对应需求：R3；状态：未执行。

前置条件：明确待验收的 Desktop 与 Harness 版本组合，使用随包 Node 24。；分别在 macOS Apple Silicon、macOS Intel、Windows x64、Linux x64 准备测试环境。；可通过测试夹具延迟当前启动令牌回环地址的 HTTP 健康响应，并记录健康响应与页面加载顺序。

1. 启动应用，使运行时进程已存在、端口已监听，但健康检查暂不成功。
2. 观察应用是否进入运行时页面。
3. 恢复有效的 HTTP 健康响应，观察应用是否继续加载官方页面。

**预期结果：** 进程存在或端口监听不足以触发就绪；有效 HTTP 健康检查成功后，应用继续加载官方页面，不持续停留在等待状态。

迁移理由（模型建议）：原文证据描述服务就绪未被正确识别、持续等待的现象。可迁移的是就绪检测与实际服务状态不一致的触发条件；不复用 Node 17 环境，也不推断历史问题根因。

- 来源：[microsoft/playwright — \[BUG\] WebServer does not work on Node.js 17+](https://github.com/microsoft/playwright/issues/10346)
  原文证据：If the user is using the Webserver in Node.js 17 it does not detect its readiness accordingly and ends up in an infinite timeout.
### TC002 健康检查持续失败时不得误报就绪

对应需求：R3；状态：未执行。

前置条件：使用已明确的验收版本及其随包运行时。；在支持平台上准备可分别返回 HTTP 失败响应、断开连接和不响应的健康检查夹具。；记录本次观察时长；PRD 尚未规定启动超时阈值。

1. 分别注入三种健康检查失败条件，每次从新的启动过程开始。
2. 记录健康检查结果、应用显示状态及运行时页面是否加载。

**预期结果：** 观察期间，应用不将失败或未收到响应的健康检查视为成功，不基于端口监听或进程存在宣告就绪。超时期限与失败提示的具体验收标准暂不判定。

迁移理由（模型建议）：历史证据支持关注就绪检测持续等待这一现象，可据此检查失败状态是否被错误推进；证据与 PRD 均不足以指定目标产品必须采用的超时值或重试策略。

- 来源：[microsoft/playwright — \[BUG\] WebServer does not work on Node.js 17+](https://github.com/microsoft/playwright/issues/10346)
  原文证据：If the user is using the Webserver in Node.js 17 it does not detect its readiness accordingly and ends up in an infinite timeout.

## 启动地址与令牌

### TC003 就绪探测使用本次启动令牌而非无令牌或旧令牌地址

对应需求：R3；状态：未执行。

前置条件：使用已明确的验收版本，在支持平台上记录健康探测请求，令牌仅使用测试值。；测试夹具能区分本次启动令牌、旧令牌、错误令牌和缺失令牌的请求。；夹具可令非当前令牌地址返回成功，同时令当前令牌地址暂不就绪。

1. 启动应用并检查健康探测实际使用的地址与令牌。
2. 保持当前令牌地址未就绪，观察其他令牌地址的成功响应是否导致应用继续加载。
3. 使当前令牌地址返回有效健康响应，再观察应用状态。

**预期结果：** 健康探测使用本次启动令牌对应的回环地址；其他令牌地址的成功响应不替代本次启动的健康检查。当前地址健康检查成功后才进入运行时页面。

迁移理由（模型建议）：原文证据报告其他机器可无认证调用 RPC。这里仅迁移缺失或错误认证上下文的边界条件，验证 PRD 明确的启动令牌就绪契约，不据此宣称目标产品存在认证漏洞或要求全部 Harness RPC 采用同一认证方式。

- 来源：[tinyhumansai/openhuman — Security: Unauthenticated RPC when OPENHUMAN\_CORE\_HOST=0.0.0.0 without OPENHUMAN\_CORE\_TOKEN](https://github.com/tinyhumansai/openhuman/issues/1919)
  原文证据：From another machine on the network, call any RPC endpoint — it succeeds without auth

## 回环网络边界

### TC004 启动地址保持回环访问边界

对应需求：R3；状态：未执行。

前置条件：在支持平台运行已明确的验收版本。；隔离测试网络内另有一台测试主机。；可记录实际监听地址和健康检查目标；探测仅针对无副作用的健康接口。

1. 正常启动应用，记录运行时监听地址与健康检查目标。
2. 从本机通过本次启动的回环地址访问健康接口。
3. 从另一测试主机通过运行应用主机的局域网地址访问同一端口。

**预期结果：** 健康检查目标及运行时监听保持回环边界；本机有效健康检查可成功，局域网主机不能通过该端口访问运行时。不能仅凭防火墙阻断结果替代监听地址核验。

迁移理由（模型建议）：原文证据明确涉及另一台网络主机成功访问接口，适合迁移为网络暴露边界测试。目标产品测试使用桌面发行版，不引入该历史产品的 Docker 或配置变量。

- 来源：[tinyhumansai/openhuman — Security: Unauthenticated RPC when OPENHUMAN\_CORE\_HOST=0.0.0.0 without OPENHUMAN\_CORE\_TOKEN](https://github.com/tinyhumansai/openhuman/issues/1919)
  原文证据：From another machine on the network, call any RPC endpoint — it succeeds without auth

## 页面权限隔离

### TC005 可执行脚本的跨源子框架不能借父窗口取得桌面能力

对应需求：R4；状态：未执行。

前置条件：在支持平台使用已明确的验收版本及真实应用 WebView 权限配置。；通过测试夹具在运行时页面加载受控跨源子框架，允许子框架执行脚本。；准备无敏感内容的测试文件和可观察的无副作用命令探针。

1. 从运行时页面脚本尝试调用 Tauri IPC、桌面 shell 与桌面文件访问接口。
2. 从子框架实际执行的脚本通过 window.parent 尝试读取父页面对象并调用上述接口。
3. 检查接口返回、测试文件变化和命令探针记录。

**预期结果：** 运行时页面及跨源子框架均不能获得桌面 IPC、shell 或文件系统能力；测试文件不被这些调用读取或修改，命令探针不执行。不得把 Harness 自身工具能力与桌面宿主能力混为一谈。

迁移理由（模型建议）：原文证据是添加 allow-scripts 后，作者观察到子框架可借 window.parent 导航到父窗口。该观察适合触发父子页面权限边界检查，但不证明其可读取父对象或获得宿主权限，更不要求目标产品引入 Electron 配置。

- 来源：[electron/electron — iframe origin wonkiness](https://github.com/electron/electron/issues/193)
  原文证据：But, as soon as I added the \`allow-scripts\` directive I found that JS did allow the inner frame to navigate out to Atom using \`window.parent\`.

## 进程监管

### TC006 正常退出只清理应用拥有的运行时进程组

对应需求：R5；状态：未执行。

前置条件：在支持平台使用已明确的验收版本。；预先启动独立 CLI 和无关 Node 测试进程，持续记录其存活与响应。；启动 DSH Desk 后记录其创建的运行时进程组及所有权信息。

1. 使应用自有运行时保持活动，同时确认独立 CLI 和无关进程正常响应。
2. 通过应用正常退出入口退出。
3. 检查自有运行时进程组及预先启动进程的存活状态。

**预期结果：** 正常退出触发的运行时清理仅作用于应用启动的进程组；该组完成退出，独立 CLI 和无关 Node 进程继续响应。记录清理耗时，不擅自设置 PRD 未定义的性能阈值。

迁移理由（模型建议）：原文证据报告退出后相关后台进程继续运行。迁移退出时仍有后台进程活动的条件，同时结合目标 PRD 检查清理对象的所有权，不套用历史产品的 CEF 进程结构。

- 来源：[tinyhumansai/openhuman — Fix OpenHuman process management for clean shutdowns and no orphaned background processes](https://github.com/tinyhumansai/openhuman/issues/1060)
  原文证据：Even after quitting/killing the OpenHuman app, OpenHuman-related processes continue running in the background and cannot be easily killed.
### TC007 主进程异常终止后再次启动不得误杀外部进程

对应需求：R5；状态：未执行。

前置条件：在支持平台使用已明确的验收版本，并记录应用自有运行时进程组。；同时运行独立 CLI 和无关 Node 测试进程。；使用隔离测试环境，允许模拟桌面主进程异常终止。

1. 异常终止桌面主进程，记录原运行时进程组是否残留。
2. 再次启动应用，记录启动和可能发生的恢复清理行为。
3. 检查独立 CLI 和无关进程是否持续响应，核对被清理进程的所有权。

**预期结果：** 异常终止及再次启动过程中，任何应用监管或恢复清理均不作用于外部进程组，独立 CLI 和无关进程继续响应。残留进程是否必须自动回收及回收期限留待补充标准。

迁移理由（模型建议）：原文证据同时提到 quitting/killing 后的后台残留，支持迁移异常终止触发条件；本条仅对 PRD 明确的监管所有权边界给出验收结果，不推定存在未声明的崩溃恢复机制。

- 来源：[tinyhumansai/openhuman — Fix OpenHuman process management for clean shutdowns and no orphaned background processes](https://github.com/tinyhumansai/openhuman/issues/1060)
  原文证据：Even after quitting/killing the OpenHuman app, OpenHuman-related processes continue running in the background and cannot be easily killed.

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：缺少与成品安装、随包固定 Node/Harness、无系统 Node/npm/终端配置及官方引导首个任务直接相关的历史证据。2798019308 的证据是构建时抓取依赖失败，不能据此要求离线源码构建；5367222388 的证据是缩放设置出现较晚，目标 PRD 未要求缩放设置。未据此生成案例。验收版本组合、macOS Intel 验收证据及“60 seconds”的计时条件仍待明确；随包运行时离线可用不等于模型任务可离线执行。
- R2：私有 DSH\_HOME 的路径选择、状态写入隔离和已有 CLI 配置不被修改均未覆盖。4569856876 仅说明单 MCP 服务限制，1931172328 仅请求脚本上下文隔离，都不是文件状态目录或配置覆盖的故障证据。
- R3：已有案例覆盖 HTTP 就绪、启动令牌与回环边界，但健康响应的具体成功判据、启动超时、错误提示及恢复操作未定义，不能充分验收持续未就绪场景。1054665493 未提供根因证据，不能假定是 IPv4/IPv6 解析问题；相关地址变体仍缺针对性证据。
- R4：已有案例覆盖页面和跨源子框架的桌面权限边界，但精确来源导航约束、重定向、新窗口及外链交给系统浏览器的完整路径缺少相应历史证据。4427792323 的 evidence\_quote 仅证实 iframe 空白或错误，未证实存储异常根因，也未证明目标官方页面具有相同触发条件，故未复制其存储或预览功能测试。
- R5：正常退出和异常终止后的所有权边界已有案例；卡住进程的升级终止策略、强制结束后的自动回收、残留进程恢复期限及各平台进程组实现的验收标准仍未明确。不能将历史问题的残留现象直接转化为目标产品承诺的全部恢复行为。
- R6：插件包名、解析版本、来源、完整性、生命周期脚本、能力声明、版本兼容性、禁用与移除、配置恢复边界、目录失败不降级及复制命令进入同一审查流程均缺少相关历史证据。4372016334 的证据仅说明媒体生成需要显式 API key，不能支持插件信任或目录回退案例；插件恢复边界的具体验收标准亦未提供。
- R7：更新载荷签名验证、更新失败与明确恢复路径均未覆盖。5111200670 的证据描述 HTML 预览内容陈旧或空白，与软件更新签名及恢复无直接关联。还需补充恢复步骤和成功判据；Windows alpha 安装包允许未签名，不能据此认定更新载荷可免签名。
- R8：每日调度、固定版本与最新候选检查、隔离工作区、偏移报告及不静默替换用户运行时均缺少相关历史证据。5016074417 涉及特定 ACP 桥接的完成语义，所给 PRD 未说明目标兼容性检查涉及该适配器，不能扩展为 Kiro 或 ACP 功能测试。
- 待确认：验收对象是仓库中的 0.1.0-alpha.14 / Harness 0.1.5-rc.2，还是已发布的 0.1.0-alpha.13 / Harness 0.1.0-rc.6？原文区分了两者，旧发布组合不应自动成为新要求。
- 待确认：macOS Intel 已列为支持的下载平台，但每次推送和 PR 的测试列表仅列 macOS arm64、Windows x64、Linux x64；Intel 的验收证据与覆盖要求是什么？
- 待确认：“60 seconds”明确只是产品目标，尚非基准结论；计时起止点、机器与网络条件、通过标准尚未定义。
- 待确认：更新失败的具体恢复步骤，以及插件禁用、移除、配置恢复的实际边界未在所给正文展开，需补充验收标准。Windows 安装包未签名是明确允许的 alpha 状态，不应与更新载荷签名要求混同。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
