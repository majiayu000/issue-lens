# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是依据 PRD 和同类产品历史问题生成的测试建议，不是目标产品的已确认缺陷。

产品形态：cli；语料：16054 条；本次选入：12 条；测试建议：12 条。

基础用例来自 PRD，历史启发用例附 issue 来源。PR 证据按来源单独标注；未采集评论。

已有覆盖只指所提供测试文件中的源码断言，未执行测试；未检出不等于全仓库无覆盖。

## 需求与检索范围

- **R1 扫描范围与安全分类：仅识别规则匹配的可重建产物，保护用户数据并限制平台和扫描入口**：User records are not cleanup candidates. The following paths are treated as protected user data and refused at scan, plan replay, and delete time — even if a custom rule or tampered ActionPlan points at them:
  组合检索：scan AND delete OR cache AND marker AND missing OR plan AND tampered AND protected；选入候选 0 条。
- **R2 清理选择与计划重验证：禁止选择 blocked、report-only，谨慎项需显式启用，删除前验证链接和根路径**：The action plan is the trust boundary: \`clean --plan\` re-validates every path against the live filesystem before deleting, refuses to follow new symlinks, and rejects plans whose roots have changed shape since the scan.
  组合检索：symlink AND delete OR plan AND root AND changed OR selection AND blocked；选入候选 2 条。
- **R3 目标空间提案与时间戳清扫：仅生成可审阅计划，正确处理目标不足、空结果和产物变化**：\`rclean free &lt;size&gt;\` computes the smallest safe set that can meet a target reclaim amount and writes it as an ActionPlan for review. It never deletes by itself; replay the plan with \`rclean clean --plan ... --dry-run\` first. \`free --json\` emits a versioned proposal containing \`targetBytes\`, \`selectedBytes\`, \`targetMet\`, \`planPath\`, and the selected scan candidates. Exit code \`0\` means the target was met; exit code \`3\` means the safe set was short or empty. A short proposal still writes a reviewable plan, while an empty proposal reports \`planPath: null\` and writes none.
  组合检索：plan AND empty OR target AND insufficient OR stamp AND changed；选入候选 0 条。
- **R4 交互清理与恢复：确认后执行可恢复清理，恢复检查目标和链接，批次失败继续且预演无副作用**：Restore one grave directly with \`rclean restore --id &lt;ID&gt;\`. Add \`--to &lt;PATH&gt;\` to choose another destination. Running \`rclean restore\` without \`--id\` on a terminal opens a newest-first numbered selector that accepts numbers, ranges, \`all\`, or \`q\`, then asks for confirmation. Every selected item still passes through the same target-exists and symlink checks as a direct restore. A batch continues after an item is skipped or fails, prints restored/skipped/failed totals, and exits non-zero when any item was not restored.
  组合检索：restore AND overwrite OR restore AND batch AND failure OR restore AND dry-run AND manifest；选入候选 1 条。
- **R5 筛选、自定义规则与忽略配置：遵守分类后筛选、规则优先级及不同配置错误的失败或告警契约**：Invalid \`--ignore\` globs fail the scan. Invalid \`.rcleanignore\` files are reported as scan warnings so the scan can continue while still marking the result as potentially incomplete.
  组合检索：glob AND invalid OR rule AND duplicate OR ignore AND negation；选入候选 1 条。
- **R6 扫描报告与解释：人工和 JSON 输出呈现陈旧度、候选解释及一致的不完整结果告警**：Scan reports include a top-level \`warnings\` list for recoverable scan problems such as invalid \`.rcleanignore\` files or filesystem walk errors. The table output prints the same warning summary; JSON consumers should treat a non-empty \`warnings\` array as "results may be incomplete."
  组合检索：scan AND warning OR json AND stalenessDays AND missing OR filesystem AND error AND incomplete；选入候选 1 条。
- **R7 管道与输出错误处理：提前关闭无崩溃，保留已确定退出状态，删除前断管必须停止清理**：Non-interactive stdout is pipe-aware. If a downstream reader closes early (for example, \`rclean rules \| head -n 1\`), rclean stops writing without a panic or backtrace and retains any command exit status already determined. Other stdout I/O errors still fail explicitly. For \`clean\`, a closed pipe before the delete phase stops the command before any artifact is removed; if cleanup has already completed, its computed success or failure status is preserved.
  组合检索：pipe AND error OR stdout AND closed AND delete OR pipe AND exit AND status；选入候选 4 条。
- **R8 Docker 只读报告：子进程超时受限、参数使用数组，所有资源均不得进入清理计划或执行删除**：\`docker report\` uses the official Docker CLI with bounded subprocess timeouts and array arguments. It does not call \`docker system prune\`, \`docker builder prune\`, \`docker rm\`, \`docker rmi\`, \`docker volume rm\`, or any other deletion command. Build cache and dangling-image categories may be classified as \`caution\` in the report taxonomy, while volumes, named resources, networks, and tagged images remain \`report-only\`; all Docker rows are \`selected=false\` in this release.
  组合检索：subprocess AND timeout OR report AND delete OR arguments AND injection；选入候选 3 条。

## 潜在遗漏（所给文件中未检出）

### TC001 安全状态控制批量选择，脏工作树不会被默认清理

对应需求：R2；分类：清理选择；状态：未执行。

增量价值（模型判断）：所给文件未发现同时验证四种安全状态、caution 显式启用及未提交用户内容保护的同等用例。

前置条件：隔离工作区中同时存在 safe 产物、脏 Git 项目中的可重建产物、符号链接候选和有明确项目标记的 report-only 模型目录。；脏项目包含已跟踪未提交文件和未跟踪用户文件，保存内容及 Git 状态快照。；产物尺寸超过测试使用的最小尺寸阈值。

1. 扫描并解释各候选，核对脏工作树产物降为 caution、链接为 blocked、模型目录为 report-only。
2. 执行 clean --all --dry-run，再加入 --include-caution 和 --include-blocked 比较选择集合。
3. 在重建的隔离夹具上执行经审阅的永久清理，分别验证默认选择和显式包含 caution 的选择。
4. 比较模型、链接目标、用户文件内容及 Git 状态。

**预期结果：** 默认 --all 仅选择 safe；--include-caution 才增加 caution；--include-blocked 只影响展示，不允许选择 blocked；report-only 始终不被选择。只删除已选产物，用户文件内容和原有 Git 编辑状态保持不变。

迁移理由（模型建议）：迁移历史报告中的“已跟踪但未提交用户内容与自动操作共存”触发条件，检验 rclean 的脏工作树分类和选择边界，不引入更新或回滚功能。所给 PR 仅支持收敛到用户内容保护风险，不能证明 rclean 存在同类问题。

- 来源：[career-ops-hq/career-ops — update-system.mjs apply: failed update triggers a rollback that wipes a git-tracked user file (interview-prep/story-bank.md)](https://github.com/career-ops-hq/career-ops/issues/995)
  原文证据：The rollback \*\*reset \`story-bank.md\` to the upstream stub\*\* (\`&lt;!-- Stories will be added here --&gt;\`), discarding accumulated stories.
  关联 PR：[fix(updater): git-safety on abort + preserve user files on safety-violation rollback (\#915)](https://github.com/career-ops-hq/career-ops/pull/1099)；已合并，交叉引用不等于确认修复。
  关联 PR：[fix(updater): fix three git-safety bugs that can lose uncommitted work (\#915)](https://github.com/career-ops-hq/career-ops/pull/1066)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(updater): preserve user files during safety-violation rollback (\#995)](https://github.com/career-ops-hq/career-ops/pull/1061)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。
### TC002 free 的达标、不足和空集合均只提案并保持退出码契约

对应需求：R3；分类：空间提案；状态：未执行。

增量价值（模型判断）：所给计划单元测试未发现 free 的选择算法、JSON、三种结果状态及无删除副作用的同等断言。

前置条件：准备尺寸可控的 safe 产物，另有很大的 caution、blocked、report-only 候选。；每轮使用独立且事先不存在的计划文件路径，保存产物快照。；达标夹具使仅需一个 safe 候选即可达到目标，避免依赖未明确的多解择优规则。

1. 执行 free &lt;size&gt; --json --write-plan，分别设置可达目标、超过所有 safe 产物总量的目标。
2. 在只有非 safe 候选的夹具上执行同一提案命令。
3. 解析 JSON、检查进程退出码及计划文件存在性，核对计划所选路径和字节合计。
4. 对生成的计划执行 clean --plan --dry-run，并比较所有产物快照。

**预期结果：** 达标时退出 0，targetMet=true，选择满足目标的最小 safe 集合；不足但非空时退出 3，targetMet=false，仍写可审阅计划；空集合退出 3，planPath=null 且不写计划。JSON 包含版本及 targetBytes、selectedBytes、targetMet、planPath、所选候选；提案和预演均不删除产物。

迁移理由（模型建议）：覆盖 PRD 明确的提案基础契约，不能因历史来源缺失而省略。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC003 stamp --sweep 只为已标记且未变化的候选写计划

对应需求：R3；分类：时间戳清扫；状态：未执行。

增量价值（模型判断）：所给文件未发现 stamp 状态与产物变化比较的触发及断言。

前置条件：隔离工作区包含三个满足扫描规则的产物 A、B、C。；A、B 可被 stamp；C 在完成 stamp 后才创建。；保留产物内容快照，计划输出路径事先不存在。

1. 对 A、B 执行 stamp，随后修改 B 的文件内容并创建 C。
2. 执行 stamp --sweep --write-plan，检查计划选择。
3. 对计划执行 clean --plan --dry-run，检查预览并比较 A、B、C 内容。

**预期结果：** 清扫计划仅包含此前已 stamp 且未变化的 A；变化后的 B 和未 stamp 的 C 不被选择。sweep 只生成计划，预演不移除产物。

迁移理由（模型建议）：直接覆盖 PRD 的已标记和未变化双重条件，不从普通 ActionPlan 尺寸更新测试推导已有 stamp 覆盖。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC004 无参数 TTY 流程先解释和确认，再执行可恢复清理

对应需求：R4；分类：交互清理；状态：未执行。

增量价值（模型判断）：T3 使用显式 --graveyard 的非交互 clean，不能等同于无参数 TTY、取消确认、TUI 解释或无 tui 回退覆盖。

前置条件：隔离当前目录包含至少两个可选择产物，使用独立 graveyard 数据目录。；准备包含 tui 的默认构建和启用 graveyard、未启用 tui 的构建。；通过伪终端驱动交互，保存产物内容快照。

1. 在 TTY 中无参数启动，确认扫描当前目录；TUI 构建对高亮候选按 ? 查看解释，文本构建使用编号选择。
2. 选择一个候选并取消最终确认，检查文件保持原状。
3. 重新启动并确认同一选择，检查未选候选、清理摘要和 graveyard 记录。
4. 使用摘要提供的恢复方式恢复所选产物，比较恢复后的文件内容。

**预期结果：** TUI 或编号选择器与构建特性一致；确认前及取消后不清理。无参数交互入口确认后将所选产物移入 rclean graveyard，未选产物不变；摘要显示保留窗口和恢复命令，恢复后内容与清理前一致。

迁移理由（模型建议）：依据 Usage 对无参数交互入口的明确契约验收；普通 clean 默认目的地的冲突另列缺口，不据此混同入口。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC005 自定义规则遵守标记 OR、内置优先和无效规则告警继续

对应需求：R5；分类：规则配置；状态：未执行。

增量价值（模型判断）：所给文件未发现自定义配置解析、标记 OR、重复 ID 和内置优先的同等测试。

前置条件：扫描根含 .rclean.toml，配置合法 safe 规则、带两个 parent\_markers 的 caution 规则、重复 ID、blocked 规则及无标记的 caution 规则。；准备仅满足其中一个标记的自定义产物、没有任何标记的对照目录和内置 node\_modules 候选。；另准备试图覆盖 node\_modules 分类与说明的用户规则。

1. 执行 scan --json --min-size 0 并收集 stderr。
2. 比较各候选的 ruleId、安全分类和解释内容。
3. 对重复 ID 的首条与后条配置可区分的说明，检查采用结果。
4. 移除配置文件再扫描，检查缺失配置是否产生告警。

**预期结果：** parent\_markers 任一存在即可启用合法规则；无标记的 caution 和自定义 blocked 规则被丢弃并输出 warning，其他合法规则仍生效。重复 ID 首条生效、后条跳过并告警；内置规则先匹配，用户规则不能覆盖 node\_modules。配置缺失不告警。

迁移理由（模型建议）：覆盖 PRD 的配置基础契约，不增加封闭规则引擎或兼容行为。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC006 Docker 报告受限等待并保持只读，特殊资源名不能变成命令

对应需求：R8；分类：Docker 只读报告；状态：未执行。

增量价值（模型判断）：T1、T2 的 Docker 存储路径拒绝测试不等同于 daemon 报告的 argv、超时、资源分类和无删除调用覆盖；所给文件未发现这些断言。

前置条件：在隔离 PATH 中提供可记录 argv、模拟官方 Docker CLI 响应的测试替身，不连接真实生产 daemon。；响应包含构建缓存、悬空镜像、带标签镜像、卷、命名资源和网络；资源名称含空格及 shell 元字符。；替身可逐项模拟立即响应、非零退出和持续阻塞。

1. 执行 docker report --json --timeout 5s，核对分类和所有 selected 字段。
2. 检查替身记录的每次启动参数，确认参数按数组边界传递且没有 shell 展开。
3. 检查无任何 prune、rm、rmi、volume rm 或其他删除调用，Docker 资源未进入文件系统候选或 ActionPlan。
4. 将一次报告子进程保持阻塞，记录超时终止及返回结果；另用非零退出作为对照。

**预期结果：** 所有 Docker 行 selected=false；构建缓存和悬空镜像允许 caution，卷、命名资源、网络和带标签镜像为 report-only。没有删除调用、计划条目或元字符引发的额外进程。阻塞子进程在配置的超时边界及合理调度误差内结束等待，不能无限挂起；错误或超时不伪装成完整成功报告，具体错误格式与退出码待补充契约。

迁移理由（模型建议）：仅迁移历史案例的外部子进程被审批或其他机制持续阻塞条件，验证 PRD 已要求的 Docker 超时。不引入 GUI 启动、agent 批量探测或 PATH shim 回退；所给相关未合并 PR 不能证明该历史问题已修复。

- 来源：[stablyai/orca — \[Bug\]: Startup hangs (up to ~5min) or crashes on Windows when serial \`where.exe\` agent-detection probes get gated by privilege-management software](https://github.com/stablyai/orca/issues/9297)
  原文证据：Orca crashes or hangs for up to ~5 minutes on startup when a corporate privilege-management / application-control tool gates the \`where.exe\` calls Orca uses for agent detection.
  关联 PR：[fix: recover local forge CLIs shadowed by broken PATH shims](https://github.com/stablyai/orca/pull/23275)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[Add IBM Bob agent support](https://github.com/stablyai/orca/pull/7698)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[Sync upstream 927ca9e94 (conflicts)](https://github.com/WrittenByAI/orcafork/pull/1)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。

## 补充边界

### TC007 规则证据决定候选资格，受保护记录不能被自定义规则或计划绕过

对应需求：R1；分类：扫描与数据保护；状态：未执行。

增量价值（模型判断）：已有源码覆盖 Codex sessions 的最终删除校验；补充完整受保护路径集合、自定义规则绕过、真实扫描入口及文件内容不变断言。

前置条件：使用隔离的用户目录和工作区，记录所有哨兵文件的内容。；准备有 Cargo.toml 的 target、无项目标记的同名 target、有虚拟环境标记的 venv、无标记的同名目录及普通用户资料目录。；在隔离用户目录中准备 PRD 列出的 Codex、Claude 受保护记录，并设置试图匹配它们的自定义 safe 规则。

1. 执行工作区扫描和 scan --home，使用 --min-size 0 获取人工及 JSON 报告。
2. 检查有效项目产物、缺少标记的目录和受保护记录的候选资格。
3. 将合法 ActionPlan 的 selected 路径分别篡改为受保护记录，尝试预演和真实清理；真实清理仅针对隔离夹具。
4. 比较扫描、预演和拒绝清理后的哨兵内容。

**预期结果：** 扫描不删除文件；有规则和标记证据的产物可被识别，缺少必要标记的目录及普通资料不进入可清理集合。所有列出的受保护记录在扫描、计划回放和删除阶段均不能成为可清理目标，内容保持一致。

迁移理由（模型建议）：直接覆盖 PRD 的候选识别和用户记录保护契约，不依赖历史 issue，也不将任意大目录视为缓存。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/src/clean/tests.rs:331
  源码引文：    let sessions = temp.path().join(".codex").join("sessions");     fs::create\_dir\_all(&amp;sessions).unwrap();      let err = validate\_for\_deletion\_with\_rule(&amp;sessions, Some("go.build\_cache"))         .expect\_err("Codex session history must never be cleanable")         .to\_string();      assert!(         err.contains("protected user data"),         "unexpected error: {err}"     );；实际触发为受保护目录搭配全局规则，断言最终校验拒绝；没有断言自定义规则扫描、Codex memories 或完整 CLI 流程。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC008 计划生成后父目录或扫描根被替换为外部链接时拒绝越界删除

对应需求：R2；分类：计划重验证；状态：未执行。

增量价值（模型判断）：已有测试替换候选叶子为链接；新增叶子仍为普通目录但祖先为链接，以及扫描根本身变化的边界。

前置条件：在普通扫描根内建立带项目标记的 app/target，并生成合法 ActionPlan。；扫描根外准备同样结构的目录和内容哨兵。；macOS、Linux 使用目录符号链接；Windows x64 使用可创建的目录链接或 junction，并记录环境权限限制。

1. 保留 candidate 叶子为普通目录，将其父目录 app 替换为指向根外目录的链接。
2. 分别执行 clean --plan 的预演及隔离夹具上的真实清理，检查错误和外部哨兵。
3. 重建夹具，将整个计划扫描根替换为外部链接，再重复计划回放。
4. 与未改变根和父目录的合法计划对照。

**预期结果：** 父目录链接导致路径越界或根形态变化时，回放明确拒绝相关目标，外部目录及哨兵内容不变；普通未变化的合法计划仍可预演。不得沿新链接执行删除。

迁移理由（模型建议）：历史报告和所给外部 PR 测试补丁共同呈现父目录链接通向工作树外部的触发条件。仅迁移真实路径边界检查；不复制 Git discard、叶子链接可删除或批量原子性语义，交叉引用也不作为修复核验。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/src/plan/tests.rs:239
  源码引文：    fs::remove\_dir\_all(&amp;candidate).unwrap();     \#\[cfg(unix)\]     std::os::unix::fs::symlink(&amp;real, &amp;candidate).unwrap();     \#\[cfg(windows)\]     std::os::windows::fs::symlink\_dir(&amp;real, &amp;candidate).unwrap();      assert!(revalidate\_selected(&amp;plan, selected).is\_err());；引文覆盖叶子路径被替换为链接后的重验证拒绝，没有构造符号链接父目录、根替换或断言外部文件内容。
- 来源：[stablyai/orca — \[Bug\]: Discard can delete files outside the worktree through symlink parents](https://github.com/stablyai/orca/issues/2928)
  原文证据：Discarding a path under a symlinked parent deletes files OUTSIDE the worktree via the rm fallback — data loss beyond the repository.
  关联 PR：[Guard untracked discard against symlink escapes](https://github.com/stablyai/orca/pull/2947)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC009 混合恢复批次遇到目标冲突或链接仍继续，预演不改变任何状态

对应需求：R4；分类：恢复安全；状态：未执行。

增量价值（模型判断）：已有直接 ID 恢复的预演断言；新增 TTY 混合批次、链接父目录、失败后继续和汇总退出码。

前置条件：隔离 graveyard 中有三个可恢复记录，删除时间不同。；一个目标不存在，一个目标已存在并含用户哨兵，另一个目标父目录为指向外部目录的链接。；保存 manifest、payload、目标目录和外部哨兵快照。

1. 在 TTY 中运行 restore --dry-run，核对最新优先排列，以编号和范围选择记录并确认。
2. 检查预演后 payload、manifest 和不存在的目标父目录。
3. 运行真实交互恢复并选择相同记录，观察正常项恢复及冲突、链接项处理。
4. 核对 restored/skipped/failed 总数、退出码、正常项内容和所有哨兵。

**预期结果：** 预演只展示操作，不移动 payload、创建目标目录或更新 manifest。真实批次对已存在目标和不安全链接拒绝恢复且不覆盖哨兵，仍处理后续正常项；汇总与逐项结果一致，只要任一项未恢复就非零退出。

迁移理由（模型建议）：覆盖 PRD 恢复批次的继续处理、目标和链接校验，以及预演无副作用契约；不添加强制覆盖或批量 --to。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/graveyard\_subcommands.rs:250
  源码引文：            "restore",             "--id",             &amp;id,             "--to",             alternate.to\_str().unwrap(),             "--dry-run",         \])         .assert()         .success()         .stdout(predicate::str::contains("would attempt to restore"))         .stdout(predicate::str::contains("payload"))         .stdout(predicate::str::contains(alternate.to\_str().unwrap()));      assert!(!original.exists());     assert!(!alternate.exists());     assert!(         !alternate.parent().unwrap().exists(),         "dry-run must not create the target parent"     );     assert\_eq!(         fs::read(manifest\_path(&amp;graveyard)).unwrap(),         manifest\_before     );     assert\_eq!(active\_records(&amp;graveyard).len(), 1);；实际覆盖单个 ID 加 --to 的预演输出、目标父目录和 manifest 不变；没有交互选择及混合成功、跳过、失败批次。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC010 多个子项目的忽略规则相互隔离，CLI 排除压过文件重包含

对应需求：R5；分类：忽略与筛选；状态：未执行。

增量价值（模型判断）：已有单根候选重包含断言；新增跨子项目上下文、名称交换及文件重包含与 CLI 排除的组合。

前置条件：单一扫描根下有两个带 package.json 的子项目，各含 node\_modules。；根 .rcleanignore 排除两个子项目的产物，再仅重包含其中一个。；使用可重复建立的夹具，支持交换两个子项目名称；不假设 CLI 支持多个位置根参数。

1. 扫描单一工作区根，核对仅重包含的候选出现。
2. 加入针对重包含候选的 --ignore，再添加一个不匹配任何路径的 --ignore，检查两个排除条件的叠加。
3. 交换子项目名称并同步调整规则，再扫描并按项目角色归一化结果。
4. 使用合法的 --category 和 --rule 缩小集合，执行相同参数的 clean --all --dry-run。

**预期结果：** 根忽略规则作用于嵌套候选，! 可重包含指定产物；CLI 排除仍移除被文件重包含的候选，额外不匹配 glob 不改变结果。交换子项目名称后按角色归一化的结果一致；扫描与清理预演遵守相同筛选，筛选不能使禁止选择的路径变为可选。

迁移理由（模型建议）：借用历史 issue 中不同遍历上下文复用忽略状态的风险，落到 rclean 已明确支持的单根嵌套扫描和忽略叠加。外部未合并 PR 的缓存解释只是提案证据，不作为确定根因或目标实现事实，也不扩展多根 CLI 能力。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/ignore\_file.rs:119
  源码引文：        "\*\\n!node\_modules/\\n!package.json\\n",     )     .unwrap();      Command::cargo\_bin("rclean")         .unwrap()         .args(\[             "scan",             temp.path().to\_str().unwrap(),             "--json",             "--min-size",             "0",         \])         .assert()         .success()         .stdout(predicate::str::contains(             "\\"ruleId\\": \\"node.node\_modules\\"",         ));；逐字片段包含重包含规则和候选出现断言；触发是单个根级项目，没有叠加 CLI 排除或跨子项目上下文比较。
- 来源：[BurntSushi/ripgrep — \`.gitignore\` not taken into account when multiple search paths are provided](https://github.com/BurntSushi/ripgrep/issues/3376)
  原文证据：6. \`rg "this" src/ tests/\` =&gt; \*\*\`src/invalid\` is found\*\* 7. \`rg "this" tests/ src/\` =&gt; funnily, \`src/invalid\` is not found
  关联 PR：[chore(deps): update ⬆️ mise-packages](https://github.com/scottames/dots/pull/980)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[ripgrep 15.2.0](https://github.com/Homebrew/homebrew-core/pull/293401)；已合并，交叉引用不等于确认修复。
  关联 PR：[fix(ignore): respect .gitignore with multiple search paths](https://github.com/BurntSushi/ripgrep/pull/3417)；未合并，交叉引用不等于确认修复。
### TC011 筛选不吞掉不完整扫描告警，陈旧度与解释在人工和 JSON 中可核对

对应需求：R6；分类：报告与解释；状态：未执行。

增量价值（模型判断）：已有尺寸筛选后保留告警的断言；新增年龄筛选、跨平台失败夹具、自定义陈旧阈值及 explain 一致性。

前置条件：隔离工作区中存在尺寸已知的产物，以及可控的目录遍历或 metadata 失败。；Unix 使用非特权用户制造访问拒绝；Windows 使用可控 ACL 或故障注入，避免依赖 Unix 权限位。；设置 stale\_after\_days=60，并准备活动时间明确位于阈值两侧的项目。

1. 分别执行人工和 JSON 扫描，记录同一失败的路径与原因。
2. 用 --min-size 和 --older-than 分别将候选过滤掉，再检查告警。
3. 核对 JSON 的 staleAfterDays、可用时的 stalenessDays 与人工 Stale 列。
4. 对保留的候选执行 explain，核对规则、安全状态、理由及恢复提示。
5. 独立将 .rcleanignore 和 --ignore 设置为同一个无效 glob，比较继续告警与明确失败。

**预期结果：** 遍历失败仍在顶层 warnings 中呈现，人工输出提醒结果可能不完整；候选被尺寸或年龄筛掉后，已发现的扫描告警不应丢失。陈旧阈值为 60，已知活动时间的年龄报告可核对，解释与候选分类一致。无效忽略文件告警后继续；无效 CLI glob 明确失败。

迁移理由（模型建议）：迁移历史案例中日期筛选改变告警分支的触发条件，验证 rclean 的告警契约，不引入分页或提高 max\_pages 的建议。外部 PR 的来源分支修订仅帮助收敛风险，不证明目标实现相同。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/ignore\_file.rs:347
  源码引文：    let filtered = run\_json("4097");     assert\_eq!(filtered.status.code(), Some(3));     let filtered\_report: Value = serde\_json::from\_slice(&amp;filtered.stdout).unwrap();     assert\_eq!(filtered\_report\["summary"\]\["candidates"\], 0);     assert\_eq!(filtered\_report\["warnings"\], first\_report\["warnings"\]);；实际触发为尺寸阈值高于可读部分字节数，断言候选为空但告警不变；没有 --older-than、陈旧度或候选解释断言。
- 来源：[career-ops-hq/career-ops — scan.mjs --since gets the wrong max\_pages cap warning (sinceMs is no longer a clean proxy after \#2418)](https://github.com/career-ops-hq/career-ops/issues/2495)
  原文证据：Run \`node scan.mjs --since 7d\` → same tenant, same cap, but the warning now reads \`truncated at N pages (X of Y jobs)\`, with no suggestion. ❌
  关联 PR：[fix(workday): key the cap-hit warning on entry provenance, not on --since](https://github.com/career-ops-hq/career-ops/pull/2763)；已合并，交叉引用不等于确认修复。
  关联 PR：[docs(workday): correct the stale ctx.sinceMs caller note after \#2418](https://github.com/career-ops-hq/career-ops/pull/2496)；已合并，交叉引用不等于确认修复。
### TC012 按输出失败类型和清理阶段保留正确状态，删除前断管停止清理

对应需求：R7；分类：管道与输出错误；状态：未执行。

增量价值（模型判断）：已有预先关闭 stdout 的删除前保护；新增读取后关闭、非零业务状态、完成后断管和非 BrokenPipe 错误。

前置条件：使用可控下游读取器及实际生产者退出状态采集器，不能只取 shell 管道最后一项状态。；隔离夹具含可清理产物；可在删除前输出和完成后摘要输出阶段控制关闭时机。；Linux 可使用 /dev/full 制造非 BrokenPipe 错误；其他支持平台使用可控写入故障。Unix 另准备继承 SIGPIPE 忽略状态的启动器。

1. 让 rules 输出被少量读取后关闭，并对 Unix 继承信号状态进行对照。
2. 对 free 的不足提案在已确定状态后关闭输出，检查生产者仍退出 3。
3. 对 clean --all --permanent --yes 在删除前关闭输出，检查产物保持原状。
4. 对已完成成功清理和已完成失败清理分别在摘要输出阶段关闭管道，与正常读取时的退出状态比较。
5. 向非 BrokenPipe 的故障输出目标写入，检查显式错误及非零退出。

**预期结果：** 提前关闭 stdout 不产生 panic 或 backtrace，已确定的业务退出状态保持不变，不能统一替换为其他产品的 141。删除前断管不移除任何产物；完成后断管保持已计算的成功或失败状态。其他 stdout I/O 错误明确失败。

迁移理由（模型建议）：合并两类相同管道故障来源，迁移下游提前关闭及继承信号状态条件，避免重复展开。所给 rtk 未合并 PR 提供 /dev/full 失败形态作为补充边界，不视为已修复事实；不复制全局 SIGPIPE 策略、MCP 或模型输出功能。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/cli/pipe\_output.rs:58
  源码引文：    let output = run\_with\_closed\_stdout(&amp;\[         "clean",         &amp;root,         "--all",         "--yes",         "--permanent",         "--min-size",         "0",     \])?;      assert\_eq!(output.status.code(), Some(0));     assert\_no\_output\_panic(&amp;output);     assert!(         candidate.exists(),         "closed pre-delete stdout must stop clean"     );；触发为启动前已关闭的 stdout，断言退出 0、无输出 panic 且候选仍存在；不覆盖已读取部分内容、清理完成后关闭或非 BrokenPipe 写入失败。
- 来源：[rtk-ai/rtk — panic/SIGABRT on Broken pipe while writing stdout](https://github.com/rtk-ai/rtk/issues/1004)
  原文证据：\`rtk\` aborts with a Rust panic when stdout is closed (\`Broken pipe\`), producing \`SIGABRT\` + coredump instead of exiting gracefully.
  关联 PR：[fix(cli): exit instead of aborting when stdout cannot be written](https://github.com/rtk-ai/rtk/pull/4108)；未合并，交叉引用不等于确认修复。
  关联 PR：[⬆️ Upstream sync — v0.42.3](https://github.com/AlobarQuest/rtk/pull/1)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[rtk 0.42.3](https://github.com/Homebrew/homebrew-core/pull/286502)；已合并，交叉引用不等于确认修复。
  PR 关联扫描达到数量上限，结果可能不完整。
- 来源：[Hmbown/Codewhale — Bug: panic on broken pipe (SIGPIPE) — crash dump when piping codewhale output](https://github.com/Hmbown/Codewhale/issues/4030)
  原文证据：When codewhale output is piped to another command (e.g. \`codewhale doctor \| head\`) and the receiving end exits before codewhale finishes writing, the process panics with a noisy crash dump instead of terminating cleanly.
  关联 PR：[fix(exec): survive closed child pipes under --auto; strip DeepSeek DSML in one-shot exec](https://github.com/Hmbown/Codewhale/pull/6605)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(cli): reset SIGPIPE to SIG\_DFL so piped output exits cleanly](https://github.com/Hmbown/Codewhale/pull/4043)；未合并，交叉引用不等于确认修复。

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：本草稿未充分覆盖 --home 各平台精确锚点、XDG/GOPATH 扩展及缺失路径静默过滤；--tmp 的顶层名称加项目标记、整工作树 caution 与嵌套产物 safe、macOS X 桶仅显式路径发现，以及 --system 唯一锚点和 requiresSudo 均需补充平台用例。发布平台仅为 macOS arm64/x64、Linux x64/arm64、Windows x64；不能迁移其他平台。浏览器、壁纸、地图和媒体缓存是否作为边界例外仍待明确，不能据此扩大任意目录扫描。
- R2：父链接和根替换用例未穷尽扫描根变为普通文件、宽泛根默认拒绝及 --allow-broad-root 显式放行；叶子链接最终删除保护已有源码断言，但 CLI 到实际删除阶段的竞态窗口仍需专门控制。计划当前尺寸读取不完整的拒绝和路径诊断在 T1 有单元断言，尚未纳入本轮优先 CLI 用例。仅审查所给文件，未判断仓库其他测试是否存在。
- R3：free 已覆盖三种结果状态，但“smallest safe set”缺少最小候选数、最小总字节或其他优化目标及并列选择规则，无法完整定义多解验收。stamp 的状态保存位置、变化判定依据和时间边界未提供，当前只验证明确内容变化及未标记排除。
- R4：无参数入口明确使用 graveyard，但普通 clean 默认 Trash 与其他默认模式描述存在冲突，需按入口确认验收目的地。本草稿未充分覆盖 restore 的 all、q、去重及无效范围、直接 --to 的链接安全、graveyard list 时间筛选边界和清理摘要保留窗口的具体值。T3 已有直接恢复、预演、时间筛选和不支持参数的源码断言，但没有据此声称这些测试已执行。
- R5：尚未充分覆盖默认 depth=6 及边界层级、最小尺寸恰等阈值、项目最新活动决定 --older-than、blocked 不被尺寸过滤、全部 category/rule 组合，以及自定义规则缺失字段和非法类别。忽略用例只使用明确支持的单一扫描根；多位置根参数的支持未在所给 PRD 明确，不直接复制 ripgrep 多根接口。T5 注释中的分类前忽略说法不作为高于 PRD 的行为契约。
- R6：报告用例未充分覆盖年龄无法取得时的字段处理、Biggest wins 排序、项目产物占比及 JSON 完整模式契约。doctor、agent doctor/optimize、completions、man 仅有部分现状描述，缺少详细验收要求；所链接文档未提供，不能补造。整体结论仅来自提供的五个目标测试文件和外部补丁，未检查整个仓库。
- R7：完成后断管需要可靠的阶段控制点，所给测试没有提供该设施；应先明确夹具实现，不能以时序碰运气声称覆盖。其他 stdout I/O 错误的具体退出码未规定，只能要求显式非零失败。无参数非 TTY 行为缺少明确契约，不能据 Gemini 历史案例添加 stdin 读取或超时规则。
- R8：Docker 不可用、daemon 不可达、响应损坏、部分子命令失败及超时的报告格式和退出码未明确；--timeout 是逐子进程还是整个报告总预算也需澄清。当前以替身验证参数和等待边界，不能等同于 macOS、Linux、Windows 上真实官方 CLI 及 daemon 的集成验证。未用外部产品的 MCP 诊断或 agent 检测功能填补此缺口。
- 待确认：默认清理目的地存在冲突：Usage 明确描述无子命令交互清理移动到 rclean graveyard，Safety Model 则写“default clean mode moves to Trash when available.”。是否分别适用于不同入口？各入口的默认删除模式需明确。
- 待确认：产品边界限定为开发产物和工具链缓存，但规则目录包含浏览器缓存、壁纸视频、地图及媒体分析缓存。应将这些已列出的精确锚点视为明确范围例外，还是收窄规则目录？不能据“every cache”扩展到任意目录。
- 待确认：Current Status 的功能列表属于现状描述，不能据此推导新增需求；其中仅列名、缺少行为契约的诊断、优化、补全和手册功能是否另有验收要求？所链接文档内容未提供，无法据其补充要求。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
