# 把 GitHub issue 变成"按产品形态查询的测试灵感库"——调研报告

- 调研日期:2026-09-22 ~ 09-23
- 方法:4 个角度并行网络调研(数据可行性 / 先例与竞品 / 学术证据 / 落地方案),每份调研的关键断言由独立核查员对抗性复核。共核查 24 条断言:**17 条确认、7 条细节修正、0 条证伪**,本文所有数字均已按核查结果修正。
- 标注约定:【事实】= 有原始出处可查;【推断】= 基于证据的推理,未经直接验证。

> 2026-10-02 实现进展：已接入 Codex CLI，支持选中 issue 的提炼与缓存，以及 PRD/README → 组合 FTS 检索与相关性筛选 → 带来源的测试方案草稿。可提供现有测试源码作覆盖对照，并按需补充最终引用 issue 的关联 PR 正文与补丁；没有历史案例时仍可生成 PRD 基础用例。当前最多提取 8 个需求主题，默认选取 12 条候选，不做全库批量模型处理或 PR 抓取，未采集评论。使用方式与边界见 [README](../README.md#generate-a-test-plan-with-codex-cli)。以下保留原调研时点的论述和建议。

---

## 一句话结论

**能做,而且大概率是个空白点——但建议把"全景语料库"收缩为"按你的产品形态圈定 30–50 个头部仓库"的 MVP 起步。**

- 核心假设"同类产品的 bug 类型高度重复"有多项实证支持(最强一条:从 25 个修复补丁提炼的性能反模式规则做跨应用迁移,直接发现了 219 个此前未知的 bug)。
- 数据管道已被 SWE-bench、StarCoder2、common-pile 等项目在工业规模上验证。
- "按产品形态索引、面向测试设计的跨项目 issue 知识库"在开源与商业产品中**均未检索到直接对标**【推断:基于多轮中英文检索的空结果,不能 100% 排除小众项目】。

---

## 1. 想法拆解

你的想法里其实包含两个待验证命题和一个工程问题:

1. **价值假设**:同类产品形态的项目(桌面 App / CLI / Web 前端 / 后端 / 移动端 / 库 SDK),其 issue 类型分布高度重复,可跨项目复用为测试角度清单。
2. **空白判断**:这件事没人做过或没做好。
3. **工程问题**:能否低成本拿到数据、按形态分类、提炼成"可测点"。

---

## 2. 核心假设的证据

### 2.1 支持:同形态软件的缺陷高度集中于少数类别,且跨项目/跨时间重复【事实】

| 证据 | 产品形态 | 关键结论 | 出处 |
|---|---|---|---|
| 性能 bug 可迁移 | 通用大型软件 | Jin et al. (PLDI 2012) 抽样 109 个真实性能 bug,从 Apache/Mozilla/MySQL 的 25 个补丁提炼简单规则,在最新版本发现 332 个未知性能问题,其中 **219 个来自跨应用迁移规则**——同形态项目间 bug 模式可直接迁移复用 | [DOI 10.1145/2254064.2254075](https://dl.acm.org/doi/10.1145/2254064.2254075) |
| 并发 bug 两类占 97% | 服务端/桌面大型应用 | Lu et al. (ASPLOS 2008):MySQL/Apache/Mozilla/OpenOffice 的 105 个真实并发 bug,非死锁类约 97% 属原子性违反与顺序违反两类 | ASPLOS 2008《Learning from Mistakes》 |
| 缺陷类型十年稳定 | 操作系统/内核 | Chou (SOSP 2001) → Palix (ASPLOS 2011) 重复研究:驱动目录缺陷密度最高可达其他目录 7 倍,主导缺陷类型十年后仍占主导(注意:2014 扩展版显示缺陷率呈下降趋势) | [DOI 10.1145/1950365.1950401](https://dl.acm.org/doi/10.1145/1950365.1950401) |
| 配置错误是大头 | 后端/服务端 | Yin et al. (SOSP 2011):546 个真实配置错误(309 个来自商业存储系统 COMP-A,237 个来自 CentOS/MySQL/Apache/OpenLDAP),**70.0%–85.5% 属参数设置错误**——后端产品的测试清单里"配置"应是第一优先级 | SOSP 2011,作者 UIUC/UCSD/NetApp |
| 内存安全 ~70% | 客户端 C/C++ 系 | Chromium 官方:约 70% 高危安全 bug 是内存安全问题(其中约一半是 use-after-free,基于 2015 年以来 912 个高危样本);Microsoft (BlueHat IL 2019):约 70% CVE 为内存安全;2025 年 Microsoft Patch Tuesday 修复中 728/955 (76%) 为内存安全 bug | [chromium.org](https://www.chromium.org/Home/chromium-security/memory-safety/) ; Jerry Gamblin/RunSafe 2025 |
| JS 引擎大规模实证 | 运行时/SDK | Wang et al. (IST Vol.155, 2023):V8/SpiderMonkey/Chakra 的 19,019 条 bug 报告、16,437 个修复、540 个深入分析 | DOI 10.1016/j.infsof.2022.107105 |
| 分布式并发分类学 | 后端/分布式 | TaxDC (ASPLOS 2016):Cassandra/HBase/ZooKeeper 等 104 个非确定性并发 bug,超过 60% 由单条不合时宜消息触发(此比例为二手转述,置信中等) | ASPLOS 2016 |
| 移动端已有现成清单 | 移动端 | Fan et al. (ICSE 2018):2,486 个 Android 应用 16,245 条唯一异常栈;Su et al. (TSE 2022)《Why My App Crashes?》归纳 **11 类 fault pattern** 并公开 DroidDefects 数据库——移动端形态可直接引用的缺陷分类清单 | [github.com/tingsu/DroidDefects](https://github.com/tingsu/DroidDefects) |
| 工业分类法 | 跨形态 | ODC(Chillarege, IBM 1992):缺陷按少量固定语义类型归类,分布随开发阶段呈规律"签名",宣称与过程/语言/领域无关,多家企业采用 | Wikipedia: Orthogonal defect classification |

**"产品形态"本身是被验证过的分析维度**【事实】:Zhang et al.《Bug Reports for Desktop Software and Mobile Apps in GitHub: What's the Difference?》(IEEE Software 36(1):63-71,**2019 年刊**,2017 年为在线出版)系统比较桌面与移动 App 的 bug 报告:移动报告更短(平均 180.5 vs 246.4 词)但含更多调试元素(栈回溯 10.13% vs 2.85%、代码示例 23.40% vs 11.64%)。另外 Android bug 类型分布(功能性 65.4%、崩溃 30.9%,Xiong et al. 2023)与服务端明显不同——不同形态的高风险区域确实不同。

### 2.2 反面与警告【事实】

- **跨项目迁移不总是有效**:Zimmermann et al. (ESEM 2009) 的 622 个跨项目缺陷预测组合中仅 21 个 (3.4%) 达到可用精度。注意:它检验的是"度量指标型预测模型"的迁移,不是 issue 文本知识的复用——方向性警告,不是否证。
- **标签噪声大**:Herzig et al. (ICSE 2013) 人工核查 5 个项目 7,000+ issue,**33.8% 的"bug"实际是功能请求/文档/重构**(原始数据现已恢复:[github.com/kimherzig/icse2013-bugclassify](https://github.com/kimherzig/kimherzig-bugclassify));重复 bug 报告占 12.67%–23%(Lazar et al.)。语料必须过滤,不能全量采信。
- **证据是间接的**【推断】:上述支持证据都是"某类软件内部缺陷集中"的单项研究;**直接以"同形态项目的 issue 类型分布相似"为假设的大规模实证检验未检索到**。你的想法是把多项间接证据组合成一个应用假设——合理,但需要用 MVP 快速验证价值。

---

## 3. 有没有人做过(先例地图)

各组成部分都有成熟先例,但**组合形态是新的**:

| 先例 | 它做了什么 | 与你想法的差异 |
|---|---|---|
| SWE-bench(Princeton, 2023) | 从 12 个 Python 仓库约 9 万个 PR 中筛出 2,294 个 issue+PR+测试对 | 证明了"爬 issue→关联修复 PR→测试验证"管道可行;但用途是 LLM 评测,且无形态维度。SWE-bench Verified 为 OpenAI 人工复核的 500 条子集 |
| Defects4J / BugsInPy / BugSwarm | 854 个 Java / 493 个 Python / ~3,091 对 fail-pass 可复现 bug | 均按"项目"组织,构成偏库/框架/CLI 工具,**无产品形态索引**。注意 BugsInPy 现址:github.com/soarsmu/BugsInPy |
| LIBRO (ICSE 2023)、Yakusu (ISSTA 2018)、AndroB2O (ASE 2025) 等 | bug report → 单个可执行测试/复现步骤 | 学术线活跃,但都是**单条报告转单个测试**,不产"测试角度清单" |
| Issue-Label-Bot(16M+ issues 训练,bug/feature/question 三分类,已归档)、微软 dotnet/issue-labeler(活跃)、Linear Triage Intelligence(2025) | issue 自动打标/去重 | 分类技术可复用,但分类轴是"类型",**无产品形态轴** |
| danluu/post-mortems(≈12.5k star)+ postmortems.app | 收集 AWS/Cloudflare/GitLab 等真实事故复盘,按根因类型组织 | 验证了"策展+分类的真实故障集"有社区消费习惯;但面向运维事故,不是功能测试 |
| Kaner《Testing Computer Software》"Common Software Errors"附录(约 89 页)、Test Heuristics Cheat Sheet 等 | 人工提炼的问题模式库 | 这正是你要"自动化+带真实案例"替代的**人工静态版**;手工、更新慢、无案例链接 |
| 商业 AI 测试工具(TestPilot、Launchable、Meta 预测性测试选择) | 输入是代码+文档或测试执行历史 | **没有一家以"同类产品的历史 issue"作为测试设计输入** |

**结论**:你想法的空白点在于三个从来没有被组合过的要素——①跨项目(不限于自家数据)、②按产品形态索引、③产物是"测试角度/检查清单"而非单个测试用例。【推断:基于检索空结果;这也是机会所在】

---

## 4. 数据与工程可行性

### 4.1 唯一的硬限制:"按形态直接搜 issue"不可行【事实,实测】

GitHub Search API 的 issue 搜索**不支持 topic: 限定符**(实测 `topic:electron is:issue` 返回 0 条;官方限定符列表确认),且单次查询硬顶 **1,000 条结果**、认证后 30 次/分钟。所以"搜索所有 Electron 应用的 issue"这条路直接封死,必须走"先圈仓库、再按仓库枚举"。

### 4.2 三条取数路径【事实,均经实测或文档核实】

| 路径 | 说明 | 量级 |
|---|---|---|
| **A. 现成语料(推荐起步)** | [common-pile/github_archive](https://huggingface.co/datasets/common-pile/github_archive)(HF, 2025-06):GH Archive 全量 issue/PR 线程清洗后 **3,032 万条文档、85.7GB**,含正文、剔除 bot 评论、逐条带仓库许可元数据(仅保留许可友好仓库约 1,000 万个),数据覆盖至 2025-01 | 下载即可用 |
| **B. BigQuery githubarchive** | GH Archive 全量公开事件(2011-02 至今),IssuesEvent 含 issue 标题与正文(已实测验证字段存在);$6.25/TiB,**每月前 1 TiB 免费**;参考规模:2011–2020 仅事件就有 31 亿条(ClickHouse 镜像) | 按需 SQL 取数 |
| **C. REST API 按仓库枚举** | `/repos/{owner}/{repo}/issues` 分页**不受 1000 条上限约束**(实测 vscode 25.4 万条 issue 在 page=20 正常返回);5000 次/小时配额下单 token 理论每日可抓约 1,200 万条。注意:该端点默认 issue+PR 混排,需按 `pull_request` 字段排除 PR | 适合 MVP 的 30–50 个仓库 |

辅助:GraphQL 点数制(5,000 点/小时,单查询 ≤50 万节点),适合一次拉取 repo→issues→comments 关联结构。StarCoder2 论文确认其预训练语料包含"从 GH Archive 收集的 GitHub issues"——大规模取 issue 作语料的路线已被工业级验证。

### 4.3 产品形态怎么判【事实+推断】

- 现成信号够用:GitHub topics 直接可查(2026-09 实测:`cli` 13.2 万仓库、`electron` 2.7 万、`desktop-app` 2.3 万),再加框架依赖(electron/Tauri→桌面、npm `bin` 字段→CLI、README 关键词)【事实】。
- **但没有现成的"产品形态"分类器**:EASE 2025 的系统性映射研究综述了 2002–2023 年 43 项仓库自动分类研究(选型起点);Auch et al. 2024 的库分类 balanced accuracy 约 71%–94%,但都不是按产品形态。【推断:需自建规则组合 + 小样本人工标注验证,工作量不大】

### 4.4 过滤与提炼【事实】

- 零成本过滤信号:`state_reason` 字段(completed / not_planned / duplicate / reopened)直接可用;"completed + 关联修复 PR"多为真问题。
- 最严标准参照 SWE-bench:合并 PR 解决 issue + 改动测试 + 改前失败改后通过——9 万 PR 只剩 2,294 (2.5%)。你的用途不需要这么严(不必可复现),但它是质量上限参照。
- LLM 提炼"症状→根因→可测点"有同构先例:OM-RAG(2026, symptom–root-cause–resolution 三元组 + 向量检索)、RCEGen(2025, LLM 从 bug report 生成根因解释)、AutoSDT-5K(自动管线收集 5,404 个任务,专家抽查 93% 有效)。issue 自动分类的 LLM 准确率:微调 GPT-4o 平均 F1≈80.7%(arXiv:2506.00128),zero-shot 也有竞争力——粗粒度分类足够支撑语料库。

### 4.5 架构选择:预构建语料 + 检索,而不是查询时临时搜【事实+推断】

查询时临时搜索受 Search API 硬限制(30 次/分、1,000 条/次);Google Self-Route 研究(arXiv:2407.16833)也支持"预构建语料 + RAG 以显著更低成本获得接近长上下文的质量"。【推断:对你的场景,预构建是明确更优解】

### 4.6 成本量级【事实价格锚 + 推算】

- embedding:text-embedding-3-small $0.02/1M tokens(Batch 减半);廉价 LLM(DeepSeek 系)输入 $0.15/1M。
- 【推断】MVP 10 万条 issue × 平均 2k tokens 输入 ≈ **几十美元**量级;REST 取数免费;存储为 SQLite 级别。

---

## 5. 风险与短板

1. **"桌面 App"维度数据最稀缺**【事实】:现有数据集与研究集中在库/框架/CLI/移动端;桌面 GUI(Electron/Tauri 等)只有零散研究(如 Quan et al. ASE 2022 手工分析含桌面应用在内的 329 个 bug),无系统语料。若你的产品是桌面形态,采集成本最高、但也最没人做。
2. **合规与 PII**【事实】:GitHub ToS 无一般性再分发禁令,但禁止绕限速/共享 token,商用 AI 访问需注意"访问对等"条款(学术豁免);GH Archive 官方声明数据"可能含第三方权利材料"、未正式声明数据集许可——**公开再分发前许可链条不确定**;有真实前例:提取 580 万 commit 邮箱的仓库被 GitHub 下架。issue 正文/评论中的邮箱、用户名必须清洗。
3. **近期数据完整性待验证**【事实】:有社区报告 2026 年 GH Archive 存在数据异常("Data Cliff",称 PullRequestEvent 占比骤降),未能核实原文;GitHub 2025-08 宣布 Activity Events payload 变更。**若依赖 2025–2026 增量数据,先做 dry-run 核对字段**。
4. **标签噪声 33.8% + 重复 12–23%**:分类精度上限受此约束,需抽检机制。
5. **价值假设未经直接验证**:没有研究直接证明"跨项目形态清单能提升测试效果"——这是 MVP 要回答的问题,不是调研能回答的。

---

## 6. 推荐落地路线

### 阶段 0:价值验证(1 天,零代码)

1. 选定你的产品形态,`/search/repositories topic:<形态> stars:>500 sort:stars` 圈出头部 30–50 个仓库(topic:electron stars:>500 实测 626 个,足够挑)。
2. 人工读这些仓库 **reaction 最多的 closed issue**(按 👍 排序)。
3. 判断:读别人的 issue 是否真的给了你测试角度?——这一步直接回答核心假设值不值钱,再决定往下走。

### 阶段 1:MVP 语料库(约一个周末)

- 取数:路径 C(REST 按仓库枚举,`state=closed`,排除 PR,保留 `state_reason=completed` 且关联修复 PR 的)。
- 提炼:廉价 LLM 逐条输出结构化 JSON——`{症状, 根因类别, 环境因素(平台/版本/权限/输入), 可转化为的测试点}`,类别表从第 2 节的现成分类法起步(移动端直接用 DroidDefects 11 类;后端把"配置错误"放首位;C/C++ 系把"内存安全"放首位;桌面形态【推断:需从数据中归纳】)。
- 存储:SQLite + FTS5(全文)+ 向量列(检索"和你 PRD 描述相似的 issue")。
- 质检:随机抽 100 条人工核对 LLM 提炼质量(参照 AutoSDT-5K 的 93% 抽查做法)。

### 阶段 2:使用工具

输入 = 你的产品形态 + PRD/功能描述 → 检索同类 issue → LLM 生成**分组测试清单**(每条附真实 issue 链接作案例)。产出形态接近"自动化的 Kaner 错误附录,但带真实案例且可按形态更新"。

### 阶段 3:扩大与发布(可选)

- BigQuery 路径 B 扩到全形态(每月 1 TiB 免费额度足够试水);GH Archive 小时级增量更新。
- 若公开分发:先解决许可链条与 PII 清洗,优先参考 common-pile 的做法(只保留许可友好仓库 + 逐条许可标注)。

---

## 7. 本次调研未尽事项(诚实清单)

- githubarchive 各年度 issue 事件精确条数与查询扫描量未实测(需 GCP 账号);"单年查询在 1 TiB 免费额度内"是推断。
- GH Archive"Data Cliff"数据异常报告未核实原文;2025-08 payload 变更后的字段完整性未逐项验证。
- githubarchive 数据集无官方许可声明;公开再分发前的许可链条待确认。
- StarCoder2 的 issues 子集未见独立公开发布(bigcode/github-issues 404);Multi-SWE-bench 的 GitHub 仓库 404,许可信息仅来自 HF 卡片。
- Palix 2014 扩展版的"缺陷率持续下降"与"类型十年稳定"并存,引用时注意口径;"Linux 2.6.33 新发现 723 个缺陷"一数无法验证,已弃用。
- 尚无"产品形态"维度的现成分类器及其准确率数据。
