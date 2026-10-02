# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是从同类产品历史问题迁移的测试建议，不是目标产品的已确认缺陷。

产品形态：desktop；语料：14730 条；本次选入：12 条；测试建议：10 条。

来源只含 issue 标题与正文；没有读取关联 PR 补丁或评论。根因与适用性仍需人工复核。

## 需求与检索范围

- **R1 多服务额度展示：统一显示剩余额度，隐藏周详情仍参与最紧张窗口判断**：All quota numbers, rings, and bars consistently display remaining quota. Hiding weekly detail does not remove a weekly limit from headline selection. Low remaining quota retains warning and critical colors.
  检索词：remaining quota, quota window selection, weekly limit, warning colors；选入候选 1 条。
- **R2 服务切换与账户可见性：最多三个收藏，支持搜索与连接状态；Antigravity 额度暂不纳入**：Provider switcher: overview, up to three saved favorites, and an All picker with search and connection/usage status. The picker follows account visibility settings; Antigravity quota integration remains pending.
  检索词：provider switcher, saved favorites, account visibility, connection status；选入候选 4 条。
- **R3 托盘与桌面工作区生命周期：默认仅托盘，关闭工作区继续监控，退出则结束应用**：QuotaBar starts as a menu bar app. Click a tray icon for the quota popover. A resizable desktop workspace (Overview, Quota, Usage, History, Sources, and Settings) is optional: open it from the tray menu. It does not open on launch. Closing the workspace keeps tray monitoring running; Quit exits the application.
  检索词：system tray, desktop workspace, close to tray, application quit；选入候选 3 条。
- **R4 后台轮询与凭据安全：退避重试、Claude OAuth 只读、Grok 委托官方 CLI 续期**：- Background polling: refreshes every 60 seconds, backs off to 5 minutes on 429, and backs off to 1 hour on Claude auth failures. - Read-only Claude OAuth: reads Claude Code credentials from the correct source, but never refreshes or writes OAuth tokens. - Grok auth: checks \`~/.grok/auth.json\` on each polling cycle. When an expired credential has a refresh token, runs the installed official \`grok models\` command to let Grok renew and save its own credentials, then rereads them before requesting quota. This does not start a conversation. The helper has a 20-second timeout; unsuccessful automatic renewal retries after 5 minutes, while manual refresh can retry immediately. QuotaBar never writes tokens itself or logs CLI output. If renewal remains unavailable, open \`grok\` and sign in only if prompted. - Hidden-window polling: disables macOS webview throttling so menubar mode keeps working.
  检索词：background polling, rate limit backoff, read-only OAuth, credential renewal；选入候选 1 条。
- **R5 界面缩放与中英语言切换：双窗口同步、偏好持久化、保持额度数据与轮询**：Settings → Display → Interface size offers \*\*100%\*\*, \*\*125%\*\*, and \*\*150%\*\*. It scales text and controls in both windows and is remembered across restarts. The tray resizes and stays anchored to its icon; content scrolls when screen space is limited.  Settings → Display → Language offers \*\*Follow system\*\*, \*\*简体中文\*\*, and \*\*English\*\*. Both the menu bar panel and desktop workspace update immediately and share the saved preference. Chinese system locales use Simplified Chinese; other system locales use English. Quota data, current navigation and provider polling survive language changes.
  检索词：interface scaling, language switching, preference persistence, tray anchoring；选入候选 3 条。
- **R6 本地用量分析与导出：统一筛选报告、明确缺失数据和定价、导出排除会话标题与路径**：Local analytics use one filtered ccstats report for summaries, projects, sessions, daily/hourly history, activity, and period comparisons. Missing source data and incomplete pricing are shown explicitly. API-equivalent estimates are not subscription bills. Session titles come from existing source metadata or local manual names, with no model summarization. JSON/SVG summary exports omit session titles and paths.
  检索词：local usage analytics, missing pricing, API-equivalent cost, summary export privacy；选入候选 0 条。
- **R7 周 token 容量估算：仅 Astra 与 GPT-5.6 Sol，本地与社区来源切换不影响官方额度**：Weekly token capacity shows only \*\*Astra\*\* and \*\*GPT-5.6 Sol\*\*. It defaults to the local estimate when available. Click the source badge to switch between local and community values; the badge flips horizontally and respects reduced motion. Switching does not refetch usage or change the official quota percentage.
  检索词：weekly token capacity, local estimate, community reference, quota percentage；选入候选 0 条。
- **R8 额度阈值与奖励提醒：80%、95%、100%、未使用奖励重置及奖励到期**：Notifications: 80%, 95%, 100%, unused bonus reset, and bonus-expiry alerts.
  检索词：quota threshold notification, bonus reset, bonus expiry；选入候选 0 条。

## 额度展示

### TC001 免费与付费 Codex 登录状态下均按实际响应展示剩余额度

对应需求：R1；状态：未执行。

前置条件：分别准备免费和付费 Codex 登录环境，逐个环境测试，不要求 QuotaBar 支持同服务多账户管理。；为两个环境提供可核对的有效额度响应，包含不同的已用比例及重置时间。

1. 在免费账户环境启动 QuotaBar，刷新并查看概览、Codex 详情和托盘。
2. 在付费账户环境重复操作。
3. 分别将界面数值与该环境的响应对照。

**预期结果：** 响应提供的额度和重置时间可见；额度数字、环和条均表达剩余量。Codex 托盘优先采用 secondary\_window，缺失时采用 primary\_window，并将已用比例转换为剩余比例；不因账户免费而遗漏已有数据。

迁移理由（模型建议）：原文证据明确报告免费 Codex 账户缺少剩余额度及重置时间。迁移账户类型这一触发条件，验证 QuotaBar 对有效响应的展示；不推定原产品根因，也不新增多账户功能。

- 来源：[farion1231/cc-switch — Codex free accounts do not show remaining quota or refresh time in CC Switch](https://github.com/farion1231/cc-switch/issues/3651)
  原文证据：For Codex free accounts, CC Switch does not show the remaining quota or the refresh/reset time.

## 连接与用量状态

### TC002 Windows 服务状态在设置、选择器和额度详情中一致

对应需求：R2；状态：未执行。

前置条件：使用 Windows 桌面环境，已启用 Codex 可见性。；准备有效登录及有效额度响应，并能模拟随后发生的认证失效。

1. 通过 Check connection 检查有效登录，查看设置、All 选择器及 Codex 详情。
2. 使认证失效并执行连接检查，等待检查完成。
3. 再次查看上述入口。

**预期结果：** 成功检查后，各入口对连接状态的表达一致，额度详情显示对应响应。认证失效后不得继续表达当前额度获取成功；保留的旧读数带过期标记，已检测服务仍可访问并进行重新检查。

迁移理由（模型建议）：原文证据明确描述 Windows 设置显示连接成功而实际能力不可用。迁移跨界面状态不一致的条件到连接检查和额度读取，不引入聊天技能或假定相同实现根因。

- 来源：[tinyhumansai/openhuman — Fix Windows tool sync mismatch: connected in UI but unavailable in chat skills](https://github.com/tinyhumansai/openhuman/issues/749)
  原文证据：On Windows, channel/tool connection state appears successful in settings UI, but in chat the agent reports integrations as unavailable or not connected.
### TC003 已连接服务的自动刷新与手动刷新均产生可见结果

对应需求：R2；状态：未执行。

前置条件：某个受支持的额度服务已连接，已有有效额度快照。；可控制额度响应，且当前没有认证失败或限流退避。

1. 改变服务响应中的额度值，等待下一次正常轮询。
2. 再次改变响应值，执行手动刷新。
3. 使额度请求失败，分别观察自动刷新及手动刷新完成后的界面。

**预期结果：** 正常轮询和手动刷新均显示各自的新额度；请求失败时不将旧读数冒充新结果，旧读数保留时带过期标记，用量状态反映当前不可用情况。连接成功本身不被当作用量获取成功。

迁移理由（模型建议）：原文证据只确认自动及手动同步均不工作，未证明认证或实现根因。迁移自动、手动两条数据更新路径的对照检查到额度刷新，不增加第三方同步功能。

- 来源：[readest/readest — Hardcover sync fails completely in v0.11.12 despite successful API key authentication](https://github.com/readest/readest/issues/4792)
  原文证据：However, sync never happens automatically, and manual sync also doesn't work at all.

## 窗口生命周期

### TC004 Windows 默认托盘启动，关闭工作区后仍持续监控

对应需求：R3；状态：未执行。

前置条件：使用 Windows 桌面环境，应用未运行。；至少启用一个托盘图标，某个服务可返回有效额度。

1. 启动应用，观察是否出现桌面工作区。
2. 从托盘菜单打开工作区，再点击工作区关闭按钮。
3. 改变额度响应，等待至少一个正常轮询周期。
4. 点击托盘查看额度，再从托盘菜单打开工作区。

**预期结果：** 启动时只提供托盘入口，不自动打开工作区；关闭工作区后应用进程和托盘仍在，额度继续更新；托盘面板及重新打开的工作区可正常使用。

迁移理由（模型建议）：两条证据均是托盘驻留相关功能诉求，其中一条明确提出 Windows 关闭应用不应完全退出。QuotaBar 已明确承诺该行为，因此迁移关闭窗口这一生命周期触发条件，不引入最小化开关或快捷键。

- 来源：[tinyhumansai/openhuman — Minimize to system tray when closing the Windows app](https://github.com/tinyhumansai/openhuman/issues/1503)
  原文证据：Would be nice if closing the app on Windows minimized it to the system tray instead of fully exiting.
- 来源：[TriliumNext/Trilium — (Feature request) Minimize/close to tray icon](https://github.com/TriliumNext/Trilium/issues/3743)
  原文证据：While Trilium can display a tray icon, it cannot be used "persistently".
### TC005 关闭工作区后使用 Quit 完整结束应用

对应需求：R3；状态：未执行。

前置条件：使用 Windows 桌面环境，工作区已关闭，托盘监控仍在运行。；可观察应用进程、托盘图标及额度请求记录。

1. 从托盘入口执行 Quit。
2. 观察应用进程和托盘图标。
3. 继续观察超过一个正常轮询周期。

**预期结果：** 应用进程退出，全部 QuotaBar 托盘图标消失，退出后不再发起额度轮询。

迁移理由（模型建议）：原文证据讨论关闭与完全退出的行为差异。迁移该边界并依据 QuotaBar 的明确要求检查 Quit，避免关闭到托盘与真正退出混淆；不是将功能请求当作已证实故障。

- 来源：[tinyhumansai/openhuman — Minimize to system tray when closing the Windows app](https://github.com/tinyhumansai/openhuman/issues/1503)
  原文证据：Would be nice if closing the app on Windows minimized it to the system tray instead of fully exiting.

## 托盘交互

### TC006 Windows 鼠标与触控板均可通过托盘进入额度面板及工作区

对应需求：R3；状态：未执行。

前置条件：使用带鼠标及触控板的 Windows 环境。；应用仅在托盘运行，至少一个服务图标可见。

1. 分别使用鼠标和触控板点击服务托盘图标，检查额度面板。
2. 通过产品实际提供的托盘菜单入口打开工作区。
3. 关闭工作区后重复一次。

**预期结果：** 两种输入设备均能打开额度面板，并可经托盘菜单打开工作区；没有因托盘点击不可达而失去应用入口。测试不要求左键直接打开原生菜单，也不要求新增点击模式设置。

迁移理由（模型建议）：原文证据明确指出 Windows 托盘菜单依赖右键后再左键选择的操作路径。迁移平台及输入方式这一交互条件，验证 QuotaBar 承诺的入口可达性，不照搬源产品的左键菜单功能请求。

- 来源：[tauri-apps/tauri — \[feat\] Allow Windows system tray menu open on mouse/trackpad left click](https://github.com/tauri-apps/tauri/issues/7719)
  原文证据：On Windows, if I want to access (show) system tray menu, I need to click the right mouse/trackpad click (show menu) then left click to select menu item.

## 轮询退避

### TC007 持续 429 时按五分钟退避并保留过期标记

对应需求：R4；状态：未执行。

前置条件：某个额度服务已有成功快照，正常轮询间隔为 60 秒。；测试环境可连续返回 429、恢复成功响应，并记录请求时间及控制时间推进。

1. 先观察正常轮询，再令下一次请求返回 429。
2. 在随后五分钟内观察该服务请求记录及缓存展示。
3. 五分钟后继续返回 429，观察下一个退避周期。
4. 恢复成功响应，观察下一次到期请求及后续正常轮询。

**预期结果：** 每次 429 后，该服务自动轮询等待五分钟，不立即循环重试，也不继续每 60 秒请求；缓存读数明确标记过期且不产生用量建议。成功后显示新额度并恢复正常轮询。

迁移理由（模型建议）：原文引文仅直接证明出现 31,328 条错误事件，没有直接证明 429 或缺少退避是根因。结合 QuotaBar 明确的 429 退避要求，迁移重复失败放大的风险场景；429 来自 PRD，不把提炼中的根因判断当作事实，也不要求接入 Sentry。

- 来源：[tinyhumansai/openhuman — Embedding API 429 floods Sentry with 31K events — no rate limit backoff](https://github.com/tinyhumansai/openhuman/issues/2898)
  原文证据：This generates 31,328 Sentry error events — the single noisiest issue in the project.

## 语言入口与布局

### TC008 三档缩放和受限空间下语言选项仍可访问

对应需求：R5；状态：未执行。

前置条件：在 macOS、Windows、Linux 桌面环境分别执行。；可打开托盘面板和桌面工作区，并可缩小工作区或使用可用空间有限的屏幕。

1. 依次设置 100%、125%、150% 界面大小。
2. 在两种窗口的设置入口打开 Language 选择控件。
3. 在受限空间下滚动内容，逐项访问 Follow system、简体中文、English。
4. 关闭并重新打开语言选择控件。

**预期结果：** 两种窗口的文字和控件随缩放更新；三个语言选项均可见或可滚动到达并可选择，无不可访问的裁切或遮挡。托盘面板调整大小后保持锚定图标，空间不足时内容可滚动。

迁移理由（模型建议）：原文证据只说明语言菜单不能正确弹出，未给出窗口尺寸或平台原因。将 QuotaBar 明确支持的缩放和受限空间作为测试变体，检查同类入口可达性，不断言历史问题由缩放引起。

- 来源：[toeverything/AFFiNE — The language switching menu does not pop up correctly](https://github.com/toeverything/AFFiNE/issues/4362)
  原文证据：The language switching menu does not pop up correctly

## 语言切换

### TC009 反复选择中英文后双窗口立即同步并保存偏好

对应需求：R5；状态：未执行。

前置条件：托盘面板及工作区可用，已有有效额度及持续轮询。；记录两种窗口当前导航位置和当前额度。

1. 在一个窗口将语言切为简体中文，查看另一个窗口。
2. 在另一个窗口切为 English，再次打开语言选项检查当前选择。
3. 反复打开、关闭选择控件并切换中英文，观察额度、导航和轮询。
4. 设置 125% 或 150% 缩放后正常退出并重启。

**预期结果：** 显式选择中英文后，两种窗口立即使用同一语言，当前选项与显示一致；额度数据、当前导航及轮询保持有效。重启后语言与缩放偏好恢复。

迁移理由（模型建议）：从语言菜单无法正确弹出的证据迁移选择入口及重复交互检查，并以 QuotaBar 的同步、持久化要求定义结果；这些扩展检查不是历史 issue 已证实的故障表现。

- 来源：[toeverything/AFFiNE — The language switching menu does not pop up correctly](https://github.com/toeverything/AFFiNE/issues/4362)
  原文证据：The language switching menu does not pop up correctly

## 语言选择状态

### TC010 语言选中项不会被其他选项的悬停状态混淆

对应需求：R5；状态：未执行。

前置条件：语言设置为 English，选择控件处于可操作状态。；分别使用 100%、125%、150% 缩放。

1. 打开语言选择控件，将指针移到简体中文但不选择。
2. 移开指针后核对当前语言及选中项。
3. 选择简体中文，再悬停 English。
4. 在两种窗口中核对选择状态和实际界面语言。

**预期结果：** 悬停不改变已保存语言，当前选中项始终可辨认；实际选择后选中状态和两种窗口语言一致。三个现有选项的名称无影响辨认的重叠或裁切。

迁移理由（模型建议）：原文证据明确指出选中行与悬停行背景非常相似。迁移语言选择状态混淆的交互条件，仅检查 QuotaBar 的三个选项，不扩展为长语言列表或指定视觉实现。

- 来源：[nexu-io/open-design — Improve language switcher UI in Settings for clearer selection and smoother browsing](https://github.com/nexu-io/open-design/issues/628)
  原文证据：Selected and hovered rows use very similar background treatments.

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：相关证据仅覆盖 Codex 账户类型下的额度展示风险；未充分覆盖最紧张窗口排序、隐藏周详情后仍参与排序、低剩余额度颜色、Claude 各窗口、Cursor 回退规则、Grok 共享池及响应缺字段的展示契约。不能由免费账户缺显示的证据推定这些机制也存在问题。
- R2：现有案例覆盖连接状态与实际用量读取的一致性，未充分覆盖最多三个收藏、收藏持久化、搜索、账户可见性设置及 Antigravity 仅显示可用状态。消息渠道静默失败的引文缺少具体触发条件，WebSocket ACK 提案涉及目标未声明的同步机制，均未据此新增案例。
- R3：托盘生命周期与输入方式的直接相关证据主要针对 Windows；macOS、Linux 的默认启动、关闭、退出行为尚未充分覆盖。各服务独立托盘、至少保留一个入口、工作区各页面及尺寸调整也缺少对应历史触发证据；未将源产品的最小化设置扩展为目标要求。
- R4：仅形成持续 429 的退避方案，且历史原文引文只证实错误事件数量，未直接证实其重试机制。Claude 各平台凭据来源、OAuth 只读、认证失败一小时退避、读取失败等待手动复查、手动操作仍受限流期限约束，以及 macOS 隐藏窗口持续轮询均未充分覆盖。认证失败自动重试与读取失败仅手动复查的适用边界仍需澄清。
- R4：没有相关历史原文证据支持 Grok 续期专门案例：每轮读取凭据、委托官方 CLI、续期后重读、20 秒超时、失败后五分钟自动重试、手动立即重试、不启动对话、不自行写令牌及不记录 CLI 输出均未覆盖，不能从错误事件洪泛推导这些认证行为。
- R5：案例覆盖语言入口、显式中英文切换及相关缩放变体；Follow system 对中文及其他系统区域的映射、系统语言变化后的行为、完整文本和控件缩放、全部屏幕位置的托盘锚定仍未充分覆盖。项目树排除模式导致空树的证据与本要求无直接关联，未迁移为偏好或语言测试。
- R6：未提供真正相关的历史证据，未生成案例。统一筛选报告、缺失源数据与定价提示、API 等价估值说明、会话标题来源及 JSON/SVG 排除标题与路径均存在覆盖缺口；文件树扫描问题不能证明本地分析或导出具有相同触发条件。
- R7：未提供真正相关的历史证据，未生成案例。仅展示 Astra 与 GPT-5.6 Sol、本地和社区来源切换、不重新请求用量、不改变官方额度、减少动态效果、估算公式及不可用回退均未覆盖。
- R8：未提供相关历史证据，未生成案例。80%、95%、100% 阈值及奖励重置、到期提醒均未覆盖；还需明确通知运行时是否已交付，以及阈值采用已用还是剩余比例。静态通知或桌面小组件预览不作为已实现功能的验收依据。
- 待确认：Features 列出通知功能，但 Demo Proof 又称桌面小组件和通知视觉仅为静态设计预览，直到运行时实现发布。当前通知的实际验收范围是什么？桌面小组件不应仅凭该预览描述纳入功能要求。
- 待确认：Claude 认证失败后退避一小时，与后文“failed reads wait for a manual recheck”之间的适用边界不明确：哪些失败会自动重试，哪些必须手动复查？
- 待确认：通知的 80%、95%、100% 指已用比例还是剩余比例？全文要求额度数字统一显示剩余量，但未明确通知触发阈值的口径。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
