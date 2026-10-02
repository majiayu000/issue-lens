# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是依据 PRD 和同类产品历史问题生成的测试建议，不是目标产品的已确认缺陷。

产品形态：cli；语料：16054 条；本次选入：0 条；测试建议：12 条。

基础用例来自 PRD，历史启发用例附 issue 来源。PR 证据按来源单独标注；未采集评论。

已有覆盖只指所提供测试文件中的源码断言，未执行测试；未检出不等于全仓库无覆盖。

## 需求与检索范围

- **R1 扫描范围与安全分类：仅识别规则匹配的可重建产物，保护用户数据并限制平台和扫描入口**：User records are not cleanup candidates. The following paths are treated as protected user data and refused at scan, plan replay, and delete time — even if a custom rule or tampered ActionPlan points at them:
  组合检索：scan AND delete OR cache AND marker AND missing OR plan AND tampered AND protected；选入候选 0 条。
- **R2 清理选择与计划重验证：禁止选择 blocked、report-only，谨慎项需显式启用，删除前验证链接和根路径**：The action plan is the trust boundary: \`clean --plan\` re-validates every path against the live filesystem before deleting, refuses to follow new symlinks, and rejects plans whose roots have changed shape since the scan.
  组合检索：symlink AND delete OR plan AND root AND changed OR selection AND blocked；选入候选 0 条。
- **R3 目标空间提案与时间戳清扫：仅生成可审阅计划，正确处理目标不足、空结果和产物变化**：\`rclean free &lt;size&gt;\` computes the smallest safe set that can meet a target reclaim amount and writes it as an ActionPlan for review. It never deletes by itself; replay the plan with \`rclean clean --plan ... --dry-run\` first. \`free --json\` emits a versioned proposal containing \`targetBytes\`, \`selectedBytes\`, \`targetMet\`, \`planPath\`, and the selected scan candidates. Exit code \`0\` means the target was met; exit code \`3\` means the safe set was short or empty. A short proposal still writes a reviewable plan, while an empty proposal reports \`planPath: null\` and writes none.
  组合检索：plan AND empty OR target AND insufficient OR stamp AND changed；选入候选 0 条。
- **R4 交互清理与恢复：确认后执行可恢复清理，恢复检查目标和链接，批次失败继续且预演无副作用**：Restore one grave directly with \`rclean restore --id &lt;ID&gt;\`. Add \`--to &lt;PATH&gt;\` to choose another destination. Running \`rclean restore\` without \`--id\` on a terminal opens a newest-first numbered selector that accepts numbers, ranges, \`all\`, or \`q\`, then asks for confirmation. Every selected item still passes through the same target-exists and symlink checks as a direct restore. A batch continues after an item is skipped or fails, prints restored/skipped/failed totals, and exits non-zero when any item was not restored.
  组合检索：restore AND overwrite OR restore AND batch AND failure OR restore AND dry-run AND manifest；选入候选 0 条。
- **R5 筛选、自定义规则与忽略配置：遵守分类后筛选、规则优先级及不同配置错误的失败或告警契约**：Invalid \`--ignore\` globs fail the scan. Invalid \`.rcleanignore\` files are reported as scan warnings so the scan can continue while still marking the result as potentially incomplete.
  组合检索：glob AND invalid OR rule AND duplicate OR ignore AND negation；选入候选 0 条。
- **R6 扫描报告与解释：人工和 JSON 输出呈现陈旧度、候选解释及一致的不完整结果告警**：Scan reports include a top-level \`warnings\` list for recoverable scan problems such as invalid \`.rcleanignore\` files or filesystem walk errors. The table output prints the same warning summary; JSON consumers should treat a non-empty \`warnings\` array as "results may be incomplete."
  组合检索：scan AND warning OR json AND stalenessDays AND missing OR filesystem AND error AND incomplete；选入候选 0 条。
- **R7 管道与输出错误处理：提前关闭无崩溃，保留已确定退出状态，删除前断管必须停止清理**：Non-interactive stdout is pipe-aware. If a downstream reader closes early (for example, \`rclean rules \| head -n 1\`), rclean stops writing without a panic or backtrace and retains any command exit status already determined. Other stdout I/O errors still fail explicitly. For \`clean\`, a closed pipe before the delete phase stops the command before any artifact is removed; if cleanup has already completed, its computed success or failure status is preserved.
  组合检索：pipe AND error OR stdout AND closed AND delete OR pipe AND exit AND status；选入候选 0 条。
- **R8 Docker 只读报告：子进程超时受限、参数使用数组，所有资源均不得进入清理计划或执行删除**：\`docker report\` uses the official Docker CLI with bounded subprocess timeouts and array arguments. It does not call \`docker system prune\`, \`docker builder prune\`, \`docker rm\`, \`docker rmi\`, \`docker volume rm\`, or any other deletion command. Build cache and dangling-image categories may be classified as \`caution\` in the report taxonomy, while volumes, named resources, networks, and tagged images remain \`report-only\`; all Docker rows are \`selected=false\` in this release.
  组合检索：subprocess AND timeout OR report AND delete OR arguments AND injection；选入候选 0 条。

## 潜在遗漏（所给文件中未检出）

### TC001 项目标记和虚拟环境标记限制候选识别

对应需求：R1；分类：扫描识别与数据保护；状态：未执行。

增量价值（模型判断）：补充标记存在与缺失的对照、根项目扫描及扫描无副作用检查；所给测试未发现同等覆盖。

前置条件：在隔离工作区准备有 Cargo.toml 的 target、有 package.json 的 node\_modules，以及无项目标记的 build、dist、out、target、vendor。；准备有 Python 项目标记的项目，分别放置带虚拟环境标记的 venv 和仅同名的普通目录。；为所有目录写入可校验内容，扫描使用 --min-size 0。

1. 分别扫描项目根目录和工作区根目录，输出人工报告及 JSON。
2. 对识别出的候选执行 explain。
3. 比较扫描前后的文件内容和目录结构。

**预期结果：** 有充分标记证据的可重建产物被识别，解释对应规则和恢复方式；缺少项目证据的通用目录及缺少虚拟环境标记的 venv 不成为可清理候选。扫描和解释不删除或修改测试内容。

迁移理由（模型建议）：直接覆盖 PRD 的识别基础契约；没有提供历史来源，不借用其他产品功能扩展识别范围。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC002 home、tmp、system 和显式路径仅发现各自允许的精确锚点

对应需求：R1；分类：扫描入口与平台边界；状态：未执行。

增量价值（模型判断）：补充扫描入口隔离、平台限制、精确锚点负例及自定义规则不能绕过用户数据保护的边界。

前置条件：在 macOS 隔离环境准备 PRD 列出的 home 缓存、Ollama 模型目录、受保护用户记录及名称相近的非锚点目录。；在实际 temp 根下准备带项目标记的 rclean-\* 工作树、其中的 target，以及无项目标记的同名前缀目录。；准备 macOS system 精确锚点及 Chrome code-sign clone 的显式路径测试夹具；系统目录测试仅在可还原的隔离机器进行。；为 Linux、Windows 准备各自已列出的平台路径；不把 macOS 专属锚点作为其他平台的识别要求。

1. 分别执行 scan --home、scan --tmp、macOS 的 scan --system 和 Chrome clone 的显式路径扫描。
2. 检查候选路径、规则、安全状态及 requiresSudo。
3. 在 home 扫描根配置匹配用户记录名称的自定义规则，再扫描受保护记录。
4. 比较扫描前后所有夹具内容；在 Linux、Windows 检查入口未产生 macOS 专属候选。

**预期结果：** 仅发现入口和平台允许的规则锚点；缺失路径被静默过滤。模型目录为 report-only，system 精确锚点为 report-only 且 requiresSudo=true；受保护记录不能成为可清理候选。tmp 不整体清空，合格临时工作树为 caution，嵌套产物按规则分类；无标记同名前缀目录不满足工作树规则。默认 tmp 不因 Chrome clone 位于 X 桶而发现它。扫描无删除行为。

迁移理由（模型建议）：按 PRD 已明确列出的精确锚点设计范围测试，不把“every cache”理解为任意目录；规则目录与产品边界的冲突仍需澄清。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC003 free 的达标、不足和空集合均只生成提案

对应需求：R3；分类：目标空间提案；状态：未执行。

增量价值（模型判断）：补充 free 的安全集合、计划落盘、JSON 字段和退出码联合契约；不自行规定 PRD 未定义的组合优化或并列排序算法。

前置条件：准备可测量的 safe 候选集合，使目标可由单个候选满足，并有更大候选作为对照。；另准备 safe 总量不足及没有 safe 候选的夹具；不足夹具中可放置大容量 caution 和 report-only 项。；使用不同且不存在的计划输出路径，记录全部产物内容。

1. 对三个夹具执行 free &lt;size&gt; --json --write-plan。
2. 核对版本、targetBytes、selectedBytes、targetMet、planPath、所选候选和退出码。
3. 检查达标夹具没有加入满足目标所不需要的候选。
4. 检查计划是否存在，并对非空计划执行 clean --plan --dry-run；比较全部产物内容。

**预期结果：** 达标提案使用可满足目标的最小 safe 集合，退出码为 0；safe 总量不足时 targetMet=false、退出码为 3，仍写出非空可审阅计划；空集合退出码为 3、planPath=null 且不写计划。caution、blocked、report-only 不用于弥补安全集合不足。free 和计划预演均不删除产物。

迁移理由（模型建议）：覆盖 PRD 明确的三个结果分支，不因缺少历史 issue 或 free 测试材料而省略。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC004 stamp sweep 仅提议已盖章且未变化的产物

对应需求：R3；分类：时间戳清扫；状态：未执行。

增量价值（模型判断）：补充未盖章、未变化和已变化的最小对照集合。

前置条件：准备三个独立的规则匹配产物，其中两个先执行 stamp，第三个保持未盖章。；记录盖章后的状态，再修改其中一个已盖章产物的内容和大小。；使用新的计划输出路径。

1. 执行 stamp --sweep --write-plan，阈值设置为包含所有测试产物。
2. 检查计划 selected 路径。
3. 执行该计划的 clean --dry-run，比较所有产物内容和目录结构。

**预期结果：** 计划仅包含已盖章且盖章后未变化的合格产物；变化产物及未盖章产物不被加入。sweep 仅生成计划，预演也不删除产物。

迁移理由（模型建议）：覆盖 PRD 明确的“previously stamped”及“have not changed”契约，不推定时间戳实现或指纹算法。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC005 无子命令流程在确认前不删除，确认后进入 graveyard

对应需求：R4；分类：交互可恢复清理；状态：未执行。

增量价值（模型判断）：补充 TTY 确认、取消、TUI 解释及无 TUI 回退；T3 的显式 --graveyard 非交互辅助流程不等同于本场景。

前置条件：使用隔离 graveyard 和含 safe 产物的当前目录，在真实 TTY 或伪终端运行。；分别准备包含 tui 和不包含 tui、保留 graveyard 的构建。；记录候选内容及 graveyard manifest 初始状态。

1. 无子命令启动 rclean，选择候选后取消确认，检查产物和 manifest。
2. 重新启动并确认清理；TUI 构建按 ? 查看当前候选解释，无 TUI 构建使用编号选择。
3. 检查摘要中的保留窗口及恢复命令。
4. 用摘要指引恢复该项并校验原始内容。

**预期结果：** 取消确认不移动产物或写入墓地记录。确认后按 PRD 对无子命令入口的明确描述将候选移动至 rclean graveyard，摘要提供保留窗口和恢复指引，恢复后内容完整。TUI 解释与候选安全状态一致，无 TUI 构建使用编号选择器。

迁移理由（模型建议）：仅采用无子命令入口明确描述的 graveyard 行为；不把它推广为所有 clean 入口默认模式，其他入口的 Trash/graveyard 冲突保留为缺口。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC006 Docker 报告仅执行有界只读调用且不生成清理候选

对应需求：R8；分类：Docker 只读诊断；状态：未执行。

增量价值（模型判断）：补充报告分类、argv 边界、超时及删除调用负断言；所给 Docker 存储保护测试不等同于报告子进程测试。

前置条件：在隔离环境以可记录 argv 的 Docker CLI 测试替身提供 build cache、dangling image、tagged image、volume、network 和 named resource 数据。；替身可模拟正常响应、超过 --timeout 的挂起及 CLI 失败，并记录所有调用。；资源名称含空格和 shell 元字符，设置执行副作用哨兵。

1. 执行 docker report 人工及 JSON 输出，检查分类和 selected。
2. 检查调用 argv 和哨兵，确认名称保持参数边界且未触发 shell 执行。
3. 模拟子进程挂起，执行 docker report --json --timeout 5s，检查受限结束及可观察失败。
4. 检查调用记录和报告，确认没有删除命令、文件系统清理候选或 ActionPlan 条目。

**预期结果：** 所有 Docker 行 selected=false；build cache 和 dangling image 可为 caution，卷、命名资源、网络及 tagged image 为 report-only。调用使用参数数组且没有 shell 注入副作用；挂起调用在有界时间内结束并报告问题。没有 prune、rm、rmi、volume rm 或其他删除调用，Docker 资源不进入文件系统清理计划。

迁移理由（模型建议）：覆盖 PRD 明确的 Docker inspect-only 边界；不将 Docker 分类中的 caution 解释为可以启用删除。

- 来源：PRD 基础用例，没有历史 issue 支撑。

## 补充边界

### TC007 批量清理仅选择允许的安全状态并拒绝篡改计划

对应需求：R2；分类：清理选择策略；状态：未执行。

增量价值（模型判断）：新增 safe/caution/blocked/report-only 混合报告的 CLI 选择矩阵、脏工作树降级和伪造安全状态的执行边界。

前置条件：准备 safe 产物、脏 Git 工作树中的 caution 产物、符号链接 blocked 候选及 report-only 模型目录。；准备受保护用户记录和 macOS requiresSudo 锚点的隔离夹具。；记录各目录内容；所有真实删除仅作用于隔离夹具。

1. 分别执行 clean --all --dry-run 和附加 --include-caution 的预演，使用 --include-blocked 显示被阻止项。
2. 写出 ActionPlan，核对 selected 集合。
3. 在独立计划副本中把受保护路径或 report-only 路径注入 selected，并伪造 safety=safe；尝试预演及执行。
4. 对允许的 safe 夹具执行 --permanent --yes，比较清理范围。

**预期结果：** 默认 --all 仅选择 safe；--include-caution 才增加 caution。blocked 和 report-only 始终不被选中，显示 blocked 不改变选择策略。篡改计划不能使保护路径变为可清理对象；requiresSudo 项被拒绝且不运行 sudo。预演不删除，永久清理仅删除允许选择的隔离产物。

迁移理由（模型建议）：覆盖 PRD 的分类后选择及计划信任边界；现有保护路径单元测试不能证明整个 CLI 选择流程已覆盖。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/src/clean/tests.rs:334
  源码引文：let err = validate\_for\_deletion\_with\_rule(&amp;sessions, Some("go.build\_cache"))         .expect\_err("Codex session history must never be cleanable")         .to\_string();      assert!(         err.contains("protected user data"),         "unexpected error: {err}"     );；已有测试把 Codex sessions 传给全局规则的最终删除验证并断言拒绝；未覆盖混合安全状态的批量选择及 CLI 篡改计划执行。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC008 计划生成后祖先链接或根路径形态变化时停止越界清理

对应需求：R2；分类：计划重验证；状态：未执行。

增量价值（模型判断）：新增祖先目录链接替换、根形态变化及 CLI 执行后的外部数据完整性断言。

前置条件：准备含可清理产物的项目、项目外的哨兵目录及其校验内容。；扫描并写出包含该产物的 ActionPlan。；在支持的 macOS、Linux、Windows 上使用相应目录链接机制；Windows 链接夹具需要创建权限。

1. 在独立夹具中保留候选末级目录名称，将其祖先目录替换为指向根外哨兵目录的链接。
2. 在另一夹具中将计划根替换为文件或目录链接。
3. 分别执行 clean --plan 的预演和实际执行，检查退出结果、错误及哨兵内容。
4. 保留候选末级目录被替换为链接的已有回归场景作为对照。

**预期结果：** 祖先链接造成的越界路径及根形态变化被拒绝，错误可观察且不删除外部哨兵内容。末级候选链接也不能被跟随；失败不能被报告为成功清理。

迁移理由（模型建议）：直接来自 PRD 的根边界和实时文件系统重验证契约；从已提供测试识别末级链接已有覆盖，补充祖先及根变化，不推断实际缺陷。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/src/plan/tests.rs:239
  源码引文：fs::remove\_dir\_all(&amp;candidate).unwrap();     \#\[cfg(unix)\]     std::os::unix::fs::symlink(&amp;real, &amp;candidate).unwrap();     \#\[cfg(windows)\]     std::os::windows::fs::symlink\_dir(&amp;real, &amp;candidate).unwrap();      assert!(revalidate\_selected(&amp;plan, selected).is\_err());；已有测试将候选末级目录替换为链接并断言重验证失败；触发条件不等同于祖先链接或计划根改变，也没有 CLI 外部数据完整性断言。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC009 恢复预演无副作用，实际批次遇到冲突和链接仍继续

对应需求：R4；分类：交互批量恢复；状态：未执行。

增量价值（模型判断）：新增交互批次预演、最新优先列表、混合冲突和链接、失败后继续及汇总退出状态。

前置条件：隔离 graveyard 中存在三条删除时间不同、内容可校验的 active 记录。；一条恢复目标不存在，一条目标已存在并含哨兵内容，一条目标祖先被替换为目录链接。；记录 payload、目标父目录及 manifest 的初始状态，在 TTY 中运行。

1. 执行 restore --dry-run，核对最新优先的编号列表，选择覆盖三项的编号或范围并确认。
2. 检查 payload、manifest 和原先不存在的目标父目录均未变化。
3. 执行实际 restore，选择相同三项并确认。
4. 检查成功项内容、冲突目标哨兵、链接外部内容、摘要和退出码。

**预期结果：** 预演仅展示操作，不移动 payload、不创建目标目录、不修改 manifest。实际批次恢复可恢复项，对已存在目标不覆盖，对链接路径不跟随；遇到跳过或失败仍处理后续项。摘要的 restored/skipped/failed 与实际结果一致，任何项未恢复时退出非零。

迁移理由（模型建议）：依据恢复批次的明确契约补充交互与混合结果，不引入强制覆盖、批量 --to 或其他已排除功能。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/graveyard\_subcommands.rs:249
  源码引文：.args(\[             "restore",             "--id",             &amp;id,             "--to",             alternate.to\_str().unwrap(),             "--dry-run",         \])         .assert()         .success()         .stdout(predicate::str::contains("would attempt to restore"))         .stdout(predicate::str::contains("payload"))         .stdout(predicate::str::contains(alternate.to\_str().unwrap()));      assert!(!original.exists());     assert!(!alternate.exists());     assert!(         !alternate.parent().unwrap().exists(),         "dry-run must not create the target parent"     );     assert\_eq!(         fs::read(manifest\_path(&amp;graveyard)).unwrap(),         manifest\_before     );     assert\_eq!(active\_records(&amp;graveyard).len(), 1);；已有测试覆盖显式 ID 加 --to 的恢复预演，断言目标父目录、manifest 和 active 记录无变化；未覆盖 TTY 多项选择、混合失败和批次继续。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC010 规则优先级、忽略叠加和配置错误保持不同处理方式

对应需求：R5；分类：配置与忽略契约；状态：未执行。

增量价值（模型判断）：新增自定义规则优先级、合法性、OR 标记和文件否定规则与 CLI 排除的组合；已有非法 CLI glob 分支无需另写重复用例。

前置条件：准备内置 node\_modules 候选、两个自定义候选，以及可排除后重新纳入的嵌套项目。；配置重复自定义 id、两个 OR parent\_markers、非法 category、blocked safety、无 marker 的 caution 规则及覆盖 node\_modules 的用户规则。；为独立运行准备有效忽略文件、非法 .rcleanignore 和非法 --ignore glob。

1. 扫描有效配置，核对内置规则优先、重复 id 首条生效、任一 marker 可启用规则以及无 marker 时不启用。
2. 使用 .rcleanignore 的排除和否定规则重新纳入嵌套候选，再以 --ignore 排除该候选。
3. 分别运行非法 .rcleanignore 和非法 --ignore glob 的扫描。
4. 检查非法自定义规则的 stderr 警告及其余有效候选；移除 .rclean.toml 后检查没有缺失文件警告。

**预期结果：** 内置匹配不被用户规则覆盖；重复 id 首条生效并警告；parent\_markers 按 OR 处理。非法自定义规则被警告并丢弃，扫描继续。CLI 忽略叠加后仍可排除被文件否定规则纳入的候选。非法 .rcleanignore 产生不完整结果警告并继续；非法 --ignore 使扫描明确失败；缺少 .rclean.toml 不警告。

迁移理由（模型建议）：覆盖配置基础契约及错误分支；源码注释中的实现顺序不替代 PRD 的分类后筛选要求。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/ignore\_file.rs:275
  源码引文：.args(\[             "scan",             temp.path().to\_str().unwrap(),             "--json",             "--min-size",             "0",             "--ignore",             "{a,b",         \])         .assert()         .failure()         .stderr(predicate::str::contains("invalid --ignore glob"));；已有测试提供非法 CLI glob 的实际输入并断言失败及错误文本；没有覆盖本用例的自定义规则及忽略否定组合。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC011 陈旧度、候选解释和遍历不完整警告在输出中一致

对应需求：R6；分类：报告与解释；状态：未执行。

增量价值（模型判断）：新增陈旧度阈值、人工/JSON 字段一致性、比例及 explain 对照；部分计量过滤后保留警告已有源码覆盖。

前置条件：准备项目活动年龄明显低于和高于配置 stale\_after\_days 的候选，避免临界时间误差。；在 macOS 或 Linux 非特权测试账户下准备部分可读、部分不可遍历的候选目录。；保留一个完全可读的候选作为输出对照。

1. 设置 stale\_after\_days，分别输出人工 scan 和 scan --json。
2. 核对 Stale、staleAfterDays、可获得的 stalenessDays 和 Biggest wins 中的项目产物比例。
3. 对候选执行 explain，核对规则、风险理由和恢复提示。
4. 提高 --min-size 过滤掉部分计量候选，检查警告是否仍保留并标示结果可能不完整。

**预期结果：** 人工与 JSON 表达一致的陈旧度和阈值，比例对应夹具统计；explain 对应当前候选分类。遍历问题在 JSON 顶层 warnings 和人工警告摘要中可观察，过滤候选不使扫描问题消失；不把部分计量结果表述为完整结果。

迁移理由（模型建议）：直接覆盖报告信任契约；权限触发仅在能够真实产生拒绝访问的环境执行，不能以管理员绕过权限的结果判定该边界。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/ignore\_file.rs:347
  源码引文：let filtered = run\_json("4097");     assert\_eq!(filtered.status.code(), Some(3));     let filtered\_report: Value = serde\_json::from\_slice(&amp;filtered.stdout).unwrap();     assert\_eq!(filtered\_report\["summary"\]\["candidates"\], 0);     assert\_eq!(filtered\_report\["warnings"\], first\_report\["warnings"\]);；已有测试在部分计量夹具上提高大小阈值，断言候选被过滤而 warnings 保留；不包含陈旧度、项目比例或 explain 断言。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC012 区分删除前断管、清理完成后断管和其他 stdout 错误

对应需求：R7；分类：管道与输出错误；状态：未执行。

增量价值（模型判断）：新增清理完成后断管的状态保留及非 BrokenPipe 错误；删除前断管保留为已有基线。

前置条件：准备隔离 safe 产物和能够控制读端关闭时机的管道测试程序。；准备可观察删除完成与最终输出阶段的同步手段；不以固定延时猜测阶段。；准备可注入非 BrokenPipe stdout 错误的测试装置，以及成功和已确定失败的命令结果。

1. 在 clean 首次删除前关闭 stdout 读端，运行 --all --permanent --yes。
2. 在清理完成后、最终输出前关闭读端，分别检查已确定的成功和失败退出状态。
3. 对只读输出命令关闭读端，检查 stderr。
4. 注入其他 stdout I/O 错误，检查错误报告及退出结果。

**预期结果：** 删除前断管停止清理且产物保留；断管不产生 panic 或 backtrace。清理完成后的断管保留已计算的成功或失败状态，不能掩盖失败。其他 stdout I/O 错误明确失败，不按正常断管静默处理。

迁移理由（模型建议）：按 PRD 明确区分输出阶段和错误类型；已有测试只覆盖启动时读端已关闭，不能推导清理完成后状态已覆盖。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/cli/pipe\_output.rs:58
  源码引文：let output = run\_with\_closed\_stdout(&amp;\[         "clean",         &amp;root,         "--all",         "--yes",         "--permanent",         "--min-size",         "0",     \])?;      assert\_eq!(output.status.code(), Some(0));     assert\_no\_output\_panic(&amp;output);     assert!(         candidate.exists(),         "closed pre-delete stdout must stop clean"     );；辅助函数在启动前关闭读端；该片段断言 clean 无 panic、退出 0 且候选保留。没有清理完成后关闭或其他 stdout 错误触发。
- 来源：PRD 基础用例，没有历史 issue 支撑。

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：方案优先覆盖识别和入口边界，尚未逐项覆盖全部项目生态、home 规则、编辑器旧版本识别和环境路径覆盖行为，包括 GOPATH 与 XDG override。规则目录包含非开发缓存与产品边界存在解释冲突；当前仅按已列精确锚点测试，不能扩展到任意应用数据。
- R2：尚未充分覆盖 --allow-broad-root 的默认拒绝与显式放行、放行后保护仍有效，以及重验证后至实际删除之间的祖先目录竞态。T1/T2 提供末级链接、文件替换及部分保护验证，但未执行这些源码测试，也不能据此证明整个删除链路安全。
- R3：“smallest safe set”的优化指标和并列选择规则未明确，方案只检查无须额外候选即可满足的明确夹具；不验收未定义算法。stamp 的变化判据、陈旧等待条件及空 sweep 输出契约未提供，尚缺同大小内容变化和时间临界点的确定验收依据。
- R4：无子命令入口明确使用 graveyard，但其他 clean 入口的默认 Trash/graveyard 模式存在冲突，需澄清后补默认目的地用例。恢复方案尚未覆盖 q、all、非法范围、全部批次结果组合、链接 payload，以及跨文件系统恢复；T3 的 graveyard 年龄筛选和不支持参数测试仅作为所给材料观察，未在本草稿展开。
- R5：尚未充分覆盖 depth、min-size 临界值、older-than、category、rule 的组合及 blocked 不被大小过滤的特殊契约。自定义规则默认字段、非法配置整体解析和所有 glob 语法也未逐项覆盖；现有用例集中于优先级及错误处理。
- R6：尚缺未知活动年龄的输出、陈旧度临界时间、多个遍历错误及不同根之间的告警汇总。诊断、优化、补全和手册仅有部分现状描述，缺少明确验收契约；未提供链接文档内容，无法补充这些要求。
- R7：方案已描述关键阶段，但输入未提供清理完成后输出同步点或非 BrokenPipe 错误注入设施，执行前需落实可控装置。尚未逐个输出子命令覆盖断管；T4 只能支持其提供的关闭时机和断言，不能代表全仓库已有覆盖。
- R8：尚未覆盖 Docker 未安装、daemon 不可达、无效 JSON、部分查询失败及 doctor --docker 的汇总行为；PRD 未定义这些情况的具体退出码和部分报告契约。CLI 替身验证不能替代各支持平台上的真实 Docker 兼容性检查。
- 待确认：默认清理目的地存在冲突：Usage 明确描述无子命令交互清理移动到 rclean graveyard，Safety Model 则写“default clean mode moves to Trash when available.”。是否分别适用于不同入口？各入口的默认删除模式需明确。
- 待确认：产品边界限定为开发产物和工具链缓存，但规则目录包含浏览器缓存、壁纸视频、地图及媒体分析缓存。应将这些已列出的精确锚点视为明确范围例外，还是收窄规则目录？不能据“every cache”扩展到任意目录。
- 待确认：Current Status 的功能列表属于现状描述，不能据此推导新增需求；其中仅列名、缺少行为契约的诊断、优化、补全和手册功能是否另有验收要求？所链接文档内容未提供，无法据其补充要求。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
