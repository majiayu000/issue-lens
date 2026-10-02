# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是依据 PRD 和同类产品历史问题生成的测试建议，不是目标产品的已确认缺陷。

产品形态：desktop；语料：14730 条；本次选入：11 条；测试建议：12 条。

基础用例来自 PRD，历史启发用例附 issue 来源。PR 证据按来源单独标注；未采集评论。

已有覆盖只指所提供测试文件中的源码断言，未执行测试；未检出不等于全仓库无覆盖。

## 需求与检索范围

- **R1 额度展示与窗口选择：统一显示剩余额度，按各服务规则选择托盘值；隐藏周详情仍参与最紧张窗口判定**：- All quota numbers, rings, and bars consistently display remaining quota. Hiding weekly detail does not remove a weekly limit from headline selection. Low remaining quota retains warning and critical colors.
  组合检索：quota AND remaining OR window AND hidden OR percentage AND fallback；选入候选 2 条。
- **R2 服务切换与连接状态：最多三个收藏，支持搜索和账户可见性设置；连接失败仍可访问已检测服务，Antigravity 仅显示可用状态**：- Provider switcher: overview, up to three saved favorites, and an All picker with search and connection/usage status. The picker follows account visibility settings; Antigravity quota integration remains pending.
  组合检索：connection AND failure OR favorites AND limit OR search AND visibility；选入候选 2 条。
- **R3 托盘、工作区与设置：至少保留一个入口；工作区不随启动打开，关闭后继续监控，退出才结束应用；登录启动使用系统登录项**：QuotaBar starts as a menu bar app. Click a tray icon for the quota popover. A resizable desktop workspace (Overview, Quota, Usage, History, Sources, and Settings) is optional: open it from the tray menu. It does not open on launch. Closing the workspace keeps tray monitoring running; Quit exits the application.
  组合检索：tray AND hidden OR window AND close OR login AND startup；选入候选 1 条。
- **R4 语言与界面缩放：双窗口即时共享并持久保存语言和尺寸；切换语言保留数据、导航与轮询，有限屏幕空间支持滚动**：Settings → Display → Interface size offers \*\*100%\*\*, \*\*125%\*\*, and \*\*150%\*\*. It scales text and controls in both windows and is remembered across restarts. The tray resizes and stays anchored to its icon; content scrolls when screen space is limited.  Settings → Display → Language offers \*\*Follow system\*\*, \*\*简体中文\*\*, and \*\*English\*\*. Both the menu bar panel and desktop workspace update immediately and share the saved preference. Chinese system locales use Simplified Chinese; other system locales use English. Quota data, current navigation and provider polling survive language changes.
  组合检索：language AND restart OR scale AND scroll OR locale AND polling；选入候选 0 条。
- **R5 后台轮询与凭据处理：正常间隔及失败退避、隐藏窗口持续轮询；Claude OAuth 只读，Grok 委托官方 CLI 续期并遵守超时与重试限制**：- Grok auth: checks \`~/.grok/auth.json\` on each polling cycle. When an expired credential has a refresh token, runs the installed official \`grok models\` command to let Grok renew and save its own credentials, then rereads them before requesting quota. This does not start a conversation. The helper has a 20-second timeout; unsuccessful automatic renewal retries after 5 minutes, while manual refresh can retry immediately. QuotaBar never writes tokens itself or logs CLI output. If renewal remains unavailable, open \`grok\` and sign in only if prompted.
  组合检索：token AND expired OR polling AND 429 OR refresh AND timeout；选入候选 3 条。
- **R6 告警与过期数据：支持 80%、95%、100% 和奖励额度重置、到期通知；过期读数保持标记且不生成使用建议**：- High-usage tips explain remaining quota and reset timing; stale data does not produce usage advice.
  组合检索：stale AND warning OR notification AND threshold OR bonus AND expiry；选入候选 1 条。
- **R7 本地分析、费用与隐私：统一过滤报告和匹配缓存，明确缺失数据及未知价格；日志留在设备，价格下载失败回退，导出不含会话标题和路径**：Local analytics use one filtered ccstats report for summaries, projects, sessions, daily/hourly history, activity, and period comparisons. Missing source data and incomplete pricing are shown explicitly. API-equivalent estimates are not subscription bills. Session titles come from existing source metadata or local manual names, with no model summarization. JSON/SVG summary exports omit session titles and paths.
  组合检索：pricing AND missing OR cache AND failure OR export AND paths；选入候选 2 条。
- **R8 Codex 周容量与价值估算：仅展示 Astra 和 GPT-5.6 Sol，按当前周匹配记录换算；切换来源不重取数据或改变官方比例，缺失本地数据时明确回退，额度耗尽仍保留最后估值**：If local data or Astra pricing is unavailable, the panel uses the community view and disables the switch with an explicit unavailable label.  The two rows represent alternative uses of one quota and cannot be added. Other devices, cloud usage and workload changes can skew local estimates. Official remaining percentages stay provider-reported. The mixed-workload API-equivalent value and any local valuation errors remain in collapsed details.
  组合检索：estimate AND missing OR quota AND exhausted OR tokens AND cached AND conversion；选入候选 1 条。

## 潜在遗漏（所给文件中未检出）

### TC001 最后入口保护、工作区恢复及系统登录项

对应需求：R3；分类：桌面生命周期；状态：未执行。

增量价值（模型判断）：所给文件未发现同等生命周期覆盖；T4只断言可见性函数，未触发最后入口保护、窗口恢复或系统登录项。

前置条件：三个支持平台使用桌面构建；至少两个服务可更新额度；可查看各平台系统登录项和进程状态。

1. 启动应用，通过托盘打开工作区。
2. 逐个隐藏托盘，尝试隐藏最后一个入口。
3. 关闭工作区，等待正常轮询后从保留入口恢复。
4. 启用和关闭Launch at Login，分别检查系统登录项及重启后的设置。
5. 使用Quit退出。

**预期结果：** 启动不打开工作区；始终保留至少一个可操作入口。关闭工作区后监控持续，保留入口可恢复工作区。Launch at Login与系统登录项一致，不能仅靠本地存储呈现开启状态。Quit结束进程和监控。

迁移理由（模型建议）：借用关闭窗口后进程仍运行、恢复入口失效的生命周期条件；验证PRD指定的托盘入口，不新增Dock恢复要求。其他产品的纯恢复决策测试不能证明QuotaBar真实窗口恢复。

- 来源：[debpalash/VoiceStudio — \[macOS\] Closing the window leaves a dead Dock icon — Reopen isn't handled](https://github.com/debpalash/VoiceStudio/issues/1887)
  原文证据：Closing the main window with the red traffic light hides it but leaves the app process running with a live Dock icon — and clicking that Dock icon does nothing.
  关联 PR：[fix(desktop): handle Dock-icon reopen on macOS](https://github.com/debpalash/VoiceStudio/pull/1888)；已合并，交叉引用不等于确认修复。
### TC002 官方CLI续期后重读凭据及20秒超时

对应需求：R5；分类：Grok认证；状态：未执行。

增量价值（模型判断）：所给QuotaBar测试模拟getGrokInfo，未发现认证文件重读、CLI调用、20秒超时或五分钟续期退避的同等断言。

前置条件：合成过期Grok凭据含refresh token；官方CLI测试替身可成功更新、失败或超时；可观察参数、文件访问和日志。

1. 触发轮询，让CLI保存新凭据，检查随后额度请求使用的新凭据。
2. 下一轮前由提供方更换认证文件，检查重新读取。
3. 让续期失败及超过20秒，检查五分钟内、五分钟后自动续期和立即手动刷新。
4. 移除refresh token或CLI，检查恢复提示。

**预期结果：** 每轮检查认证文件；过期且有refresh token时委托官方grok models，不启动对话。成功后重读凭据再请求额度；助手在20秒超时，失败后的自动续期等待五分钟，手动刷新可立即重试。QuotaBar自身不写token、不记录CLI输出；续期不可用时提示打开grok，仅在提供方提示时登录。

迁移理由（模型建议）：迁移恢复时复用旧凭据和自动恢复不可用的边界，不复制Socket协议、重连次数或网页重定向方案。所给Socket测试有的仅断言凭据提供器至少调用一次，不能证明每次重试均获取新凭据，更不能证明Grok CLI续期。

- 来源：[tinyhumansai/openhuman — Socket reconnection fails with expired token after disconnect (237 events)](https://github.com/tinyhumansai/openhuman/issues/2892)
  原文证据：Users experience sustained socket outages that don't self-heal until app restart.
  关联 PR：[fix(socket): refresh token before reconnect, fast-fail on Invalid token (\#2892)](https://github.com/tinyhumansai/openhuman/pull/2905)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(socket): refresh session token on Invalid token rejection (TAURI-RUST-9C)](https://github.com/tinyhumansai/openhuman/pull/2896)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
- 来源：[toeverything/AFFiNE — Expired token handling](https://github.com/toeverything/AFFiNE/issues/932)
  原文证据：UI should let the user know if the refresh token is expired.
  关联 PR：[fix: on token invalidation it shall be redirected to home page](https://github.com/toeverything/AFFiNE/pull/1087)；已合并，交叉引用不等于确认修复。
  关联 PR：[feat: add \`MessageCenterHandler\`](https://github.com/toeverything/AFFiNE/pull/770)；已合并，交叉引用不等于确认修复。
### TC003 统一筛选报告、匹配缓存和安全导出

对应需求：R7；分类：本地分析与隐私；状态：未执行。

增量价值（模型判断）：所给文件未发现统一报告、匹配缓存、导出脱敏或日志网络边界的同等测试；费用请求竞态不等同于报告一致性。

前置条件：合成Claude、Codex、Cursor日志跨日期和项目，含可辨识会话标题、人工名称和路径；准备匹配及不匹配当前筛选的缓存。

1. 设置日期和项目筛选，核对汇总、项目、会话、日/小时历史、活动及周期比较。
2. 分别用匹配和不匹配缓存启动，观察初始展示和后台刷新。
3. 检查标题来源，导出JSON和SVG，观察分析期间网络流量。

**预期结果：** 各视图使用同一筛选报告并符合独立计算的合成数据；仅匹配缓存用于快速启动，新结果按当前筛选更新。标题来自已有元数据或人工名称，不触发模型总结。JSON、SVG均不含会话标题和路径；本地日志不外传，费用明确标为API等价估算而非订阅账单。

迁移理由（模型建议）：直接覆盖报告一致性、缓存匹配与隐私契约；历史来源不足以支持这些具体机制。

- 来源：PRD 基础用例，没有历史 issue 支撑。

## 补充边界

### TC004 各服务托盘取值优先级、零值与缺失回退

对应需求：R1；分类：额度展示；状态：未执行。

增量价值（模型判断）：新增实际托盘优先级、有效零值和字段缺失回退；已有测试仅覆盖总览缺失值。

前置条件：在 macOS、Windows、Linux 桌面构建中使用合成响应，可观察实际托盘。；Claude 各窗口使用率不同；Codex 主窗口已用80%、次窗口20%；Cursor 总体已用80%、autoPercent为20%；Grok共享池已用25%、Build已用4%。

1. 比较详情、总览和各服务托盘的剩余额度。
2. 将Codex次窗口、Cursor autoPercent分别改为0，再移除优先字段。
3. 移除所有可用额度字段；检查Antigravity状态展示。

**预期结果：** Claude托盘使用最紧张窗口；Codex、Cursor优先字段对应剩余80%，有效零值对应剩余100%，字段缺失后回退为剩余20%；Grok托盘显示共享池剩余75%。额度数字、环和条表达剩余量，低剩余量保留警示色。无可用数据时明确不可用，不出现undefined或虚构满额；Antigravity仅显示可用状态及额度待支持说明。

迁移理由（模型建议）：借用多窗口映射和可选字段缺失的触发条件，不引入OpenCode或自定义脚本功能。关联PR中的实现仅用于理解边界，未合并提案不视为修复事实，历史提炼不作为QuotaBar根因。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/quota\_overview.test.tsx:76
  源码引文：it.each(\[null, NaN, Infinity\])('does not turn missing or invalid usage (%s) into zero', (usedPercent) =&gt; {     const html = renderToStaticMarkup(&lt;QuotaOverview {...overviewProps()} summaries={\[{ ...claude, usedPercent }\]} windows={\[\]} /&gt;);     expect(html).toContain('&lt;strong&gt;—&lt;/strong&gt;');     expect(html).toContain('No quota data');     expect(html).not.toContain('role="progressbar"');     expect(html).not.toContain('quota-dial-fill');；触发总览缺失或非法使用率并断言不可用展示，没有实际托盘或各服务字段优先级断言。
- 来源：[farion1231/cc-switch — feat(usage): support OpenCode Go quota query](https://github.com/farion1231/cc-switch/issues/6350)
  原文证据：OpenCode Go exposes three dollar-denominated quota windows (5-hour, weekly, and monthly), but CC Switch currently cannot display them.
  关联 PR：[fix(opencode): render Go quota usage accurately](https://github.com/farion1231/cc-switch/pull/6547)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[feat(usage): support OpenCode Go quotas](https://github.com/farion1231/cc-switch/pull/6351)；未合并，交叉引用不等于确认修复。
- 来源：[farion1231/cc-switch — Custom usage script test can show undefined and saved query can reject HTTP LAN base URL](https://github.com/farion1231/cc-switch/issues/3128)
  原文证据：The modal test path can succeed, but the saved provider usage query path can fail before the custom request runs because it falls back to the provider base URL and validates that HTTP base URL even in \`templateType: "custom"\` mode.
  关联 PR：[\[codex\] Fix custom usage script summaries](https://github.com/farion1231/cc-switch/pull/3129)；已合并，交叉引用不等于确认修复。
### TC005 收藏和账户可见性约束下保留失败服务入口

对应需求：R2；分类：服务切换；状态：未执行。

增量价值（模型判断）：新增收藏持久化、搜索可见性和失败入口保留；请求竞态已有面板级覆盖。

前置条件：无保存偏好，已检测至少四个服务，Antigravity已安装；可控制检测响应完成顺序。

1. 查看首次启动的检测结果及登录说明，通过提供方登录后点击Check connection。
2. 保存三个收藏并尝试添加第四个；在All中搜索并修改账户可见性。
3. 让已检测服务的新检查失败，切换另一服务后再完成旧成功请求。
4. 重启并检查收藏和失败服务入口。

**预期结果：** 收藏最多三个且持久保存；All搜索遵循账户可见性。新失败可见，不被旧成功覆盖，不污染其他服务状态；未主动隐藏的已检测服务仍可访问。Antigravity只显示状态，不生成额度窗口；登录仍由提供方完成。

迁移理由（模型建议）：迁移失败后状态残留及历史成功标记失真的触发条件，不复制OAuth登录方法或消息通道。关联PR交叉引用不能证明修复了对应issue。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/provider\_refresh\_races.test.tsx:260
  源码引文：it('keeps new failure after old success', async () =&gt; {     const race = await start\_panel\_race(driver);     await settle(() =&gt; race.requests.reject(1, new Error('new failure')));     await settle(() =&gt; race.requests.resolve(0, 90));     expect(driver.marker(race.callbacks)).toEqual(\[driver.expected\_failure\_marker\]);     expect(rendered\_text(race.renderer)).toContain('new failure');；断言新失败不被旧成功覆盖，但没有收藏、搜索、账户可见性或失败入口可选择断言。
- 来源：[tinyhumansai/openhuman — OAuth connection badges get stuck in Connecting](https://github.com/tinyhumansai/openhuman/issues/2128)
  原文证据：OAuth connection badges can get stuck in \`Connecting\`, and starting a different OAuth method does not clear the prior pending state.
  关联 PR：[test(e2e): add E2E coverage for 15 Composio connector flows](https://github.com/tinyhumansai/openhuman/pull/2351)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(channels): clear stale OAuth Connecting badges across auth modes (\#2128)](https://github.com/tinyhumansai/openhuman/pull/2256)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(channels): show channel selector error state](https://github.com/tinyhumansai/openhuman/pull/2170)；未合并，交叉引用不等于确认修复。
- 来源：[tinyhumansai/openhuman — \[Bug\] Telegram and Discord messaging channels broken — show connected but messages not sending/receiving](https://github.com/tinyhumansai/openhuman/issues/3712)
  原文证据：Both channels fail silently with no visible error
  关联 PR：[fix(credentials): re-resolve active-user workspace in channel runtime + scheduler after store\_session (\#4398)](https://github.com/tinyhumansai/openhuman/pull/4411)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(channels): repair Discord &amp; Telegram messaging end-to-end (\#3712, \#3763)](https://github.com/tinyhumansai/openhuman/pull/3794)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC006 双窗口语言和缩放共享、持久化及持续轮询

对应需求：R4；分类：语言与显示；状态：未执行。

增量价值（模型判断）：新增真实双窗口、缩放、导航、持续轮询和进程重启；现有单组件语言测试关闭自动轮询。

前置条件：托盘面板和工作区打开，已有额度数据；工作区位于History，正常轮询开启；可限制屏幕可用空间。

1. 切换简体中文、English、Follow system，分别使用中文和非中文系统语言。
2. 依次选择100%、125%、150%，检查两个窗口的文本、控件、托盘锚点和滚动。
3. 切换语言期间观察下一轮数据更新及History导航，随后重启。

**预期结果：** 两个窗口即时共享语言和尺寸；Follow system将中文系统语言映射为简体中文，其他语言映射为英语。额度和导航保留，轮询持续。尺寸缩放作用于文本和控件，托盘仍锚定图标，有限空间可滚动访问全部内容；重启恢复偏好。

迁移理由（模型建议）：直接覆盖PRD基础契约，未找到相关历史来源不影响用例保留。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/i18n.test.tsx:247
  源码引文：await act(async () =&gt; { renderer = create(createElement(GrokPanel, { autoRefreshIntervalMs: 0 })); });     expect(JSON.stringify(renderer!.toJSON())).toContain('Weekly pool');     expect(JSON.stringify(renderer!.toJSON())).toContain('73% remaining');     await act(async () =&gt; { setLanguagePreference('zh-CN'); });     expect(JSON.stringify(renderer!.toJSON())).toContain('每周额度池');     expect(JSON.stringify(renderer!.toJSON())).toContain('剩余 73%');     expect(JSON.stringify(renderer!.toJSON())).not.toContain('Weekly pool');     expect(fetch).toHaveBeenCalledTimes(1);；覆盖单面板语言切换保留额度且不重取；不能证明双窗口、缩放和轮询持续。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC007 隐藏窗口轮询、429截止与Claude OAuth只读

对应需求：R5；分类：轮询与Claude认证；状态：未执行。

增量价值（模型判断）：新增真实请求退避、隐藏窗口、手动复查与限流交互及凭据只读；已有前端门控测试模拟了后端。

前置条件：三个支持平台使用合成凭据；macOS使用测试Keychain，Windows/Linux使用测试环境变量。；可观察真实请求时刻、凭据读取和写入，已有成功额度缓存。

1. 隐藏窗口并观察正常60秒轮询。
2. 返回429，在五分钟截止前、截止后观察自动请求，并在截止前点击手动复查。
3. 设置无效Claude凭据，观察额度请求前登录检查及凭据写入。
4. 通过Claude Code重新登录后手动复查，观察恢复后的轮询。
5. 记录认证失败后的自动重试行为，待澄清适用分支后核对一小时退避或手动门控。

**预期结果：** 隐藏窗口不停止正常轮询；429后五分钟截止前不发送额度请求，手动复查也遵守仍有效的限流截止。无效Claude凭据在额度请求前被拦截；QuotaBar不刷新或写OAuth token。重新登录后可通过显式复查恢复。认证失败的一小时退避与等待手动复查存在PRD歧义，该部分暂不作统一验收判定。

迁移理由（模型建议）：迁移认证失效后周期性重复失败的触发条件，不要求引入Sentry或账单接口；现有源码行为不能消除PRD恢复契约冲突。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/provider\_refresh\_races.test.tsx:1204
  源码引文：vi.mocked(backend.getQuota)       .mockResolvedValueOnce({ connected: false, error: 'Claude OAuth token expired or invalid. Please re-login.' })       .mockResolvedValue(quota(42));；触发条件为模拟的Claude认证失败响应，没有真实凭据读取。
- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/provider\_refresh\_races.test.tsx:1210
  源码引文：await act(async () =&gt; { await vi.advanceTimersByTimeAsync(2 \* 60 \* 60 \* 1000); });     expect(backend.getQuota).toHaveBeenCalledTimes(1);     await act(async () =&gt; { renderer.root.findByProps({ 'aria-label': 'Refresh current provider' }).props.onClick(); });     expect(backend.getQuota).toHaveBeenLastCalledWith(true);     expect(backend.getQuota).toHaveBeenCalledTimes(2);     await act(async () =&gt; { await vi.advanceTimersByTimeAsync(60\_000); });     expect(backend.getQuota).toHaveBeenCalledTimes(3);     expect(backend.getQuota).toHaveBeenLastCalledWith(false);；覆盖等待显式复查及恢复一分钟轮询，不覆盖429后端截止、凭据只读或一小时退避分支。
- 来源：[tinyhumansai/openhuman — Backend billing endpoint fires 1,437 Sentry errors on 401](https://github.com/tinyhumansai/openhuman/issues/2922)
  原文证据：When the session token is invalid/expired, every poll fires a Sentry error.
  关联 PR：[fix(observability): suppress billing 401 Sentry noise (TAURI-RUST-E, \#2922)](https://github.com/tinyhumansai/openhuman/pull/2924)；已合并，交叉引用不等于确认修复。
### TC008 过期读数不生成建议及已交付告警事件

对应需求：R6；分类：过期数据与告警；状态：未执行。

增量价值（模型判断）：新增建议抑制、恢复清除过期状态及额度事件到通知的链路；现有源码主要覆盖过期展示、设置和模拟通知发送。

前置条件：已有高使用量成功读数和重置时间；可模拟读取失败；通知运行时交付范围需先确认。

1. 让后续刷新失败，检查总览、详情、建议和恢复入口，再恢复成功读取。
2. 对确认已交付的告警注入新鲜80%、95%、100%已用事件、未使用奖励重置和奖励到期事件。
3. 关闭对应设置后重触发；切换语言后重放同一事件。

**预期结果：** 保留旧读数并明确标记过期和最后成功时间，原因与恢复入口可访问；过期读数不生成使用建议。恢复后更新状态，新鲜建议说明剩余额度和重置时间。确认已交付的通知响应对应事件并遵守开关及既有去重；语言切换不重复发送同一事件。交付范围未确认的通知保留为待验收，静态预览不能算运行时覆盖。

迁移理由（模型建议）：仅迁移缓存被误呈现为实时数据的风险；阈值、奖励事件和建议抑制来自PRD，不由模型目录issue证明。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/quota\_overview.test.tsx:88
  源码引文：readState: { error: 'HTTP 429', readAt: Date.parse('2026-09-14T12:00:00Z') },     }\]} /&gt;); });     const text = JSON.stringify(renderer!.toJSON());     expect(text).toContain('Showing stale data');     expect(text).toContain('Last successful read');     expect(text).toContain('last known data');；断言失败读数的过期标记，没有建议抑制、恢复状态或额度告警触发断言。
- 来源：[nexu-io/open-design — Fix Open Design not reading the latest model list from Codex CLI](https://github.com/nexu-io/open-design/issues/651)
  原文证据：As a result, the user cannot select the latest models in the Open Design settings UI, and runtime requests can fail because the app and CLI are out of sync on model availability.
  关联 PR：[fix: discover Codex models from installed CLI](https://github.com/nexu-io/open-design/pull/2082)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix: surface codex response failures](https://github.com/nexu-io/open-design/pull/1313)；未合并，交叉引用不等于确认修复。
### TC009 未知价格、公共目录回退及长请求定价

对应需求：R7；分类：费用与价格；状态：未执行。

增量价值（模型判断）：新增SDK实际下载、缓存回退、未知价格计算和272K边界；已有组件仅接收模拟估值错误。

前置条件：合成日志含已知和未知价格模型及GPT-6.1 Sol；可控制公共目录、价格缓存年龄和下载失败；另准备无日志状态。

1. 查看无日志和部分缺价情况下的今日、周、月估算。
2. 分别在无新鲜缓存和缓存超过24小时时观察下载；下载失败时检查旧缓存或内置价格回退。
3. 提供SDK可识别的新模型价格并刷新估算。
4. 构造GPT-6.1 Sol恰为272K及超过272K输入的请求，独立核算输入、缓存读写和输出费用。

**预期结果：** 缺失来源和不完整价格显式展示，未知模型不显示免费或把缺价费用记为有效零值。价格目录按规定刷新，失败使用已有缓存或内置价格，仍未知的价格保持不可用。SDK已识别的新目录模型无需QuotaBar发布即可估价。恰为272K使用标准档，超过272K整条请求使用PRD高档单价；金额明确为API等价估算。

迁移理由（模型建议）：借用缺失价格被转为零费用及缺失估算输入的边界；不沿用其他产品单价、数据库种子或回填机制。历史提炼中的根因解释不作为目标产品事实。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/i18n.test.tsx:203
  源码引文：const diagnostic = missingPrices       ? 'cannot price Codex models in the active weekly window: gpt-reserve'       : 'failed to load pricing data: network offline';；源码构造缺价或下载失败诊断，没有实际下载和定价触发。
- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/i18n.test.tsx:219
  源码引文：expect(copy()).toBe(missingPrices       ? '缺少 gpt-reserve 的价格，暂时无法计算每周估值。'       : '暂时无法计算每周估值，请展开诊断详情查看原因。');；覆盖不可计算提示，未断言未知价格不会被算作零费用，也未验证价格回退。
- 来源：[farion1231/cc-switch — \[Bug\] Claude pricing seed: Claude Opus 5.5 missing — requests stored at $0](https://github.com/farion1231/cc-switch/issues/7599)
  原文证据：Opus 5.5 requests are stored with \`total\_cost\_usd = 0\` (same failure mode as \#7050).
  关联 PR：[feat(pricing): seed Claude Opus 5.5](https://github.com/farion1231/cc-switch/pull/7600)；已合并，交叉引用不等于确认修复。
- 来源：[janhq/jan — feat(agent): add /usage and /context slash commands with per-provider token accounting](https://github.com/janhq/jan/issues/8730)
  原文证据：There is no way to answer "how much have I spent this thread", "what is eating my context window", or "what would this cost", and there is no per-provider token accounting.
  关联 PR：[feat(agent-tui): add /context to break down context window usage](https://github.com/janhq/jan/pull/8799)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC010 当前周混合token记录换算与来源切换

对应需求：R8；分类：Codex周估算；状态：未执行。

增量价值（模型判断）：新增从实际记录到换算结果的断言及低使用率、缓存token、gpt-reserve边界；现有测试输入预计算估值。

前置条件：当前周记录含多模型、缓存输入和普通Luna，官方已用2%；另有周外记录及独立gpt-reserve记录。；Astra价格可用，可独立计算匹配记录费用及相同token的Astra重放费用。

1. 核对当前周记录费用除以官方已用分数所得周价值。
2. 按周价值除以Astra重放费用再乘观察token数核对Astra容量，核对Sol为其2.5倍。
3. 检查一般用量与订阅周估算的gpt-reserve归属。
4. 切换本机和社区来源，观察请求数量及官方百分比。

**预期结果：** 混合模型、低于五个百分点且无连续单模型样本仍可估算；包含缓存输入及普通Luna，排除周外记录和订阅周估算中的独立gpt-reserve，但一般用量保留后者。仅显示Astra和GPT-5.6 Sol两行，说明不能相加；来源切换不重取用量，官方剩余98%不变，混合估值放在折叠详情。

迁移理由（模型建议）：换算和筛选公式直接来自PRD；提供的其他产品feature不能证明该算法或SDK计算正确。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/i18n.test.tsx:185
  源码引文：await act(async () =&gt; { toggles()\[0\].props.onClick(); });       expect(rows()\[0\].findByType('strong').children.join('')).toBe('≈900M tokens / week');       expect(rows()\[1\].findByType('strong').children.join('')).toBe('≈2.3B tokens / week');       expect(renderer!.root.findByProps({ className: 'weekly-value-gauge-center' }).findByType('strong').children.join('')).toBe('60%');       expect(fetch).toHaveBeenCalledTimes(1);；覆盖切回本机时官方比例不变且不重取，未从日志计算周价值或Astra重放费用。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC011 本机不可用回退社区及耗尽后的最后估值

对应需求：R8；分类：Codex周估算；状态：未执行。

增量价值（模型判断）：新增真实缺价、从可用到不可用的迁移及耗尽布局和奖励操作；已有参数化组件测试覆盖部分回退展示。

前置条件：已有当前周有效本机估值；可移除本地记录或Astra价格，并模拟官方周额度耗尽及可用奖励重置。

1. 分别移除记录和Astra价格，检查默认来源及本机切换限制。
2. 恢复有效估值，再将官方已用比例更新为100%。
3. 点击奖励重置入口并观察对应操作。

**预期结果：** 本机不可用时默认社区参考，不能切入有效本机视图，明确说明不可用原因；展示Astra约853.5M、Sol约3.6B、给定来源与日期及Pro 20× Standard单账户背景，不冒充当前账户额度。耗尽时官方剩余0%，保留最后有效估值及状态，奖励重置入口可操作；估值说明不包含快模式溢价和购买额度。

迁移理由（模型建议）：迁移估算输入缺失时不得编造数值的边界；社区回退及耗尽布局是PRD要求，关联PR明确延后usage功能，不能视为该估值机制的实现证据。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/i18n.test.tsx:113
  源码引文：\['missing local conversion', null, null\],     \['zero local conversion', 0, null\],     \['invalid local conversion', Number.NaN, null\],；现有测试包含本机转换结果缺失、零值和非法值输入，但没有实际Astra价格缺失触发。
- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/i18n.test.tsx:148
  源码引文：expect(toggles()\[0\].props\['aria-label'\]).toBe('Why local estimate is unavailable');       expect(toggles()\[0\].props\['aria-pressed'\]).toBeUndefined();     }     expect(rows()).toHaveLength(2);     expect(rows().map((row) =&gt; row.findByType('span').children.join(''))).toEqual(\['Astra', 'GPT-5.6 Sol'\]);     expect(rows()\[0\].findByType('strong').children.join('')).toBe(isLocal ? '≈900M tokens / week' : '≈853.5M tokens / week');     expect(rows()\[1\].findByType('strong').children.join('')).toBe(isLocal ? '≈2.3B tokens / week' : '≈3.6B tokens / week');；覆盖不可用入口、两行模型及社区数值，不覆盖额度耗尽后保留最后估值或奖励操作。
- 来源：[janhq/jan — feat(agent): add /usage and /context slash commands with per-provider token accounting](https://github.com/janhq/jan/issues/8730)
  原文证据：There is no way to answer "how much have I spent this thread", "what is eating my context window", or "what would this cost", and there is no per-provider token accounting.
  关联 PR：[feat(agent-tui): add /context to break down context window usage](https://github.com/janhq/jan/pull/8799)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。

## 已有覆盖（低优先级）

### TC012 隐藏周详情仍由最紧张周窗口决定标题

对应需求：R1；分类：额度展示；状态：未执行。

增量价值（模型判断）：无新增；保留为已有同等覆盖的基础回归项。

前置条件：Claude五小时已用73%，七日已用98%。

1. 关闭周详情，查看总览标题、窗口名称和可见进度条。

**预期结果：** 标题显示剩余2%并标识七日窗口；周详情隐藏，五小时进度条仍显示剩余27%。

迁移理由（模型建议）：直接覆盖PRD的基础契约，不依赖历史issue。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/quotabar/tests/quota\_overview.test.tsx:69
  源码引文：const html = renderToStaticMarkup(&lt;QuotaOverview {...overviewProps()} windows={\[windows\[0\], { ...windows\[1\], usedPercent: 98 }\]} display={{ weekly: false }} /&gt;);     expect(html).toContain('&lt;strong&gt;2%&lt;/strong&gt;');     expect(html).toContain('7-day usage · Closest to limit');     expect((html.match(/role="progressbar"/g) ?? \[\])).toHaveLength(1);     expect(html).toContain('aria-valuenow="27"');；同等触发条件下明确断言隐藏周详情后的标题排名和剩余量；这是源码覆盖判断，未执行测试。
- 来源：PRD 基础用例，没有历史 issue 支撑。

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：尚未逐项展开Claude Opus、Sonnet、Design、Fable 5窗口映射和重置时间；并列排名、异常比例和实际托盘颜色仍需补充。其他产品PR中的已用百分比展示不能替代QuotaBar剩余额度契约。
- R2：Add service完整设置路径、All／单服务预设和所有连接状态组合未充分展开；搜索匹配规则未明确，不自行规定模糊搜索。失败后入口保留已纳入方案，所给源码尚不足以证明该链路。
- R3：主题、macOS Hide Dock、工作区尺寸调整以及三个平台安装产物未展开；T4只有函数级托盘可见性测试。签名、公证、SHA-256清单和发布前人工审批的发行验证也未纳入这轮运行时优先用例。
- R4：全部页面长文本布局、首轮加载动画和来源徽章动画的reduced-motion行为未充分覆盖；已有语言存储事件模拟不能证明真实双窗口同步或重启持久化。
- R5：Claude认证失败后一小时退避与failed reads等待手动复查的适用分支尚待澄清。Grok续期失败退避与HTTP 429截止的组合、Codex和Cursor凭据来源矩阵仍需补充；前端getGrokInfo按60秒调用的测试不能证明后端实际请求或CLI续期按60秒执行。
- R6：通知运行时与静态预览的交付范围存在歧义。首次读数是否告警、阈值跨越、奖励到期提前量和系统权限拒绝尚未明确或覆盖。T3设置及去重资格、T5模拟通知发送不能证明额度事件已连通系统通知；桌面小组件不作为已交付功能。
- R7：Grok周／月共享池、Build／Chat／Imagine／Voice／API产品组合、额外额度及durable inference ledger输入未充分覆盖；ccstats 0.9.0依赖锁定和Grok 4.7定价也需补充。报告的时区及周期边界尚未展开，所给材料没有SDK实际定价测试。
- R8：官方已用比例为零、跨周旧估值处理、其他设备和云端偏差提示、社区快照精确时间及来源徽章reduced-motion仍未充分覆盖。已有前端测试主要接收预计算结果，不能证明实际换算。全部覆盖判断仅限本次提供的五个QuotaBar测试文件；外部PR补丁仅作迁移证据，缺失或截断补丁不证明没有回归测试。本方案及所引测试均未执行。
- 待确认：Claude 认证失败的恢复行为需澄清：Features 规定退避 1 小时，Development 又规定 failed reads 等待手动复查。哪些失败会自动重试，哪些必须手动复查？手动复查如何遵守仍有效的限流截止时间？
- 待确认：通知运行时范围需澄清：Features 明确列出通知功能，Demo Proof 又称 desktop widget and notification visuals 仅为静态设计预览，直到运行时实现发布。当前哪些通知已实现、哪些仍属预览？未明确前不将桌面小组件列为已交付功能。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
