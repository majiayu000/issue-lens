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

### TC001 四种安全状态决定批量选择，预演不执行清理

对应需求：R2；分类：选择与清理预演；状态：未执行。

增量价值（模型判断）：所给文件未发现实际分类、四态批量选择、预演和执行串联的同等覆盖。

前置条件：准备实际规则可识别的 safe、脏 Git 工作树 caution、符号链接 blocked 和模型存储 report-only 候选。；保存候选内容及恢复存储快照，真实删除仅使用可丢弃夹具。

1. 执行 clean --all --dry-run，记录选中集合。
2. 加入 --include-caution，再加入 --include-blocked，比较报告与选中集合。
3. 生成对应 ActionPlan 并预演。
4. 对隔离夹具执行 --all --include-caution --permanent --yes，检查保留路径。

**预期结果：** 默认只选择 safe；显式启用后才选择 caution。blocked 可展示但永不选中，report-only 始终不选中。预演不移动、删除产物或创建恢复记录。永久清理仅移除授权候选，blocked 和 report-only 内容不变。

迁移理由（模型建议）：覆盖 PRD 的选择基础契约；requiresSudo 特例测试不能替代完整安全状态矩阵。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC002 free 正确处理达标、不足和空集，始终只生成提案

对应需求：R3；分类：目标空间提案；状态：未执行。

增量价值（模型判断）：所给文件未发现 free 的目标、退出码、空计划和无删除行为测试。

前置条件：准备大小可核对的 safe 集合及不能参与提案的其他安全状态候选。；建立达标、不足、无 safe 候选三组夹具，计划位置初始不存在。；达标夹具仅有一个 safe 候选，且足以满足目标。

1. 分别执行 free &lt;size&gt; --json --write-plan，直接记录生产者退出码。
2. 核对版本字段、targetBytes、selectedBytes、targetMet、planPath 和候选集合。
3. 对非空计划执行 clean --plan --dry-run。
4. 比较产物和恢复存储快照。

**预期结果：** 达标退出 0；不足退出 3、targetMet=false，仍生成可审阅计划；空集退出 3、planPath=null，不创建计划。字节汇总与选中 safe 候选一致，其他安全状态不参与。free 和预演均不移动或删除产物。

迁移理由（模型建议）：直接覆盖 PRD 明确规定的三类结果，不因缺少历史来源跳过。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC003 stamp sweep 排除未标记和标记后变化的产物

对应需求：R3；分类：时间戳清扫；状态：未执行。

增量价值（模型判断）：新增标记状态与标记后变化边界；所给文件未发现同等测试。

前置条件：准备三个合法产物：标记后不变、标记后修改、始终未标记。；修改夹具使用大小和修改时间均明显变化的内容，避免依赖未说明的精细变化判据。

1. 仅对前两个产物执行 stamp。
2. 修改第二个产物，随后执行 stamp --sweep --write-plan。
3. 读取计划并执行计划预演，比较全部产物内容。

**预期结果：** 计划仅选择已标记且未变化的产物；修改过的和未标记的产物不被选中。sweep 仅生成计划，预演不移动或删除产物。

迁移理由（模型建议）：资格要求来自 PRD；普通计划重算大小不等同于 stamp 状态覆盖。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC004 无子命令流程确认后进入 graveyard，取消不产生清理

对应需求：R4；分类：交互可恢复清理；状态：未执行。

增量价值（模型判断）：T3 使用显式 --graveyard，不等同于无子命令 TTY、取消确认、选择器回退及摘要指引覆盖。

前置条件：隔离 HOME 和 graveyard，使用受控 TTY，当前目录有多个合法候选。；分别准备含 tui 的默认构建及不含 tui、含 graveyard 的构建。；保存候选内容。

1. 无子命令启动，选择部分候选后取消确认，检查文件及 graveyard。
2. 重新启动并确认选择；TUI 用 ? 查看解释，无 tui 构建使用编号选择。
3. 检查清理摘要及 graveyard list，取得 ID。
4. 执行 restore --id 并比较恢复内容。

**预期结果：** 取消不移动产物、不新增恢复记录；确认后仅选中候选进入 graveyard。构建分别提供 TUI 或编号选择，解释符合候选资格。摘要包含保留窗口和恢复指引，恢复后文件内容与清理前一致。

迁移理由（模型建议）：仅验收 PRD 明确的无子命令入口，不自行解决显式 clean 默认 Trash 与 graveyard 的描述冲突。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC005 规则标记 OR、内置优先级及无效规则告警

对应需求：R5；分类：自定义规则；状态：未执行。

增量价值（模型判断）：所给文件未发现标记 OR、规则优先级及单条无效规则处理的同等覆盖。

前置条件：准备合法 safe 规则、含两个 parent\_markers 的 caution 规则及匹配目录。；重复 ID、blocked、无标记 caution 分别使用独立配置夹具，同时保留合法规则。；准备同时匹配内置和自定义规则的 node\_modules。

1. 分别仅保留两个标记中的一个，扫描并执行 explain。
2. 扫描重复 ID 和各无效规则夹具，检查 stderr 及有效候选。
3. 扫描同时匹配内置和自定义规则的目录。
4. 移除配置后再次扫描。

**预期结果：** 任一 parent marker 足以启用规则；有效规则的原因和恢复提示可观察。内置规则优先。重复 ID 首条生效，其余告警跳过；blocked 和无标记 caution 规则告警丢弃，合法规则继续生效。缺失配置不产生缺失警告。

迁移理由（模型建议）：直接覆盖 PRD 规则契约，不用忽略文件测试替代规则加载测试。

- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC006 Docker 调用有界、参数边界完整且无删除命令

对应需求：R8；分类：Docker 只读报告；状态：未执行。

增量价值（模型判断）：T1/T2 的 Docker 存储路径拒绝测试不等同于 Docker 报告的 argv、超时、分类及删除调用隔离覆盖。

前置条件：使用记录程序路径、argv 和调用时间的 Docker CLI 替身，返回各资源类别的固定数据。；分别准备立即响应、配置时限内响应、持续阻塞及等待 stdin 的行为。；在支持平台执行，Windows 独立验证延迟边界；保存资源和文件快照。

1. 执行 docker report、JSON 报告及 doctor --docker，核对分类和 selected。
2. 使用含空格的可执行路径夹具，记录参数数组边界。
3. 执行 --timeout 5s，分别测试时限内响应、持续阻塞和等待输入。
4. 核对全部调用记录、资源快照及清理计划输出。

**预期结果：** 每次子进程等待受配置超时限制，不无限挂起；时限内有效响应得到处理，超时诊断可观察。参数按数组边界传递。构建缓存和悬空镜像可为 caution，其余指定资源为 report-only，所有行 selected=false。Docker 资源不成为文件系统候选或计划项，不调用任何删除命令，资源不变。

迁移理由（模型建议）：迁移外部探测阻塞、非 TTY 等待 EOF 和平台延迟边界，不增加并行、缓存或 MCP 功能。Windows issue 同时涉及调用形式和超时，PR 又提出输出解析原因，不能认定超时为已核验唯一根因。

- 来源：[stablyai/orca — \[Bug\]: Startup hangs (up to ~5min) or crashes on Windows when serial \`where.exe\` agent-detection probes get gated by privilege-management software](https://github.com/stablyai/orca/issues/9297)
  原文证据：Orca crashes or hangs for up to ~5 minutes on startup when a corporate privilege-management / application-control tool gates the \`where.exe\` calls Orca uses for agent detection.
  关联 PR：[fix: recover local forge CLIs shadowed by broken PATH shims](https://github.com/stablyai/orca/pull/23275)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[Add IBM Bob agent support](https://github.com/stablyai/orca/pull/7698)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[Sync upstream 927ca9e94 (conflicts)](https://github.com/WrittenByAI/orcafork/pull/1)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。
- 来源：[google-gemini/gemini-cli — hangs indefinitely when executed from Node.js \`child\_process\` (subprocess)](https://github.com/google-gemini/gemini-cli/issues/6715)
  原文证据：Gemini CLI version 0.1.22 hangs indefinitely when executed from Node.js \`child\_process\` (subprocess), while the exact same commands work perfectly when run directly from a terminal.
  关联 PR：[fix(cli): improve stdin handling and add initial state check](https://github.com/google-gemini/gemini-cli/pull/6747)；已合并，交叉引用不等于确认修复。
- 来源：[Panniantong/Agent-Reach — doctor falsely reports XiaoHongShu MCP connection failure on Windows with mcporter 0.7.3](https://github.com/Panniantong/Agent-Reach/issues/159)
  原文证据：But the MCP server is actually running and usable.
  关联 PR：[fix(xiaohongshu): robust JSON parsing + Windows timeouts for doctor check](https://github.com/Panniantong/Agent-Reach/pull/161)；已合并，交叉引用不等于确认修复。

## 补充边界

### TC007 项目标记和用户数据保护不能被自定义规则或计划绕过

对应需求：R1；分类：扫描资格与数据保护；状态：未执行。

增量价值（模型判断）：补充扫描、自定义规则、标记资格及数据不变断言；已有源码覆盖部分计划拒绝和最终删除校验。

前置条件：使用隔离工作区及测试 HOME，保存文件内容和目录快照。；准备有 Cargo.toml 的 target、无项目标记的 target，以及有、无虚拟环境标记的 venv。；准备 PRD 列出的 Codex、Claude 用户记录，配置尝试匹配这些记录的自定义规则。

1. 执行人工和 JSON 扫描，使用 --min-size 0，并对可报告路径执行 explain。
2. 将合法计划的选中路径逐项篡改为受保护记录，执行计划预演。
3. 比较扫描和预演前后的文件内容及目录快照。

**预期结果：** 具备对应标记的产物可被识别；缺少标记的通用 target 和非虚拟环境 venv 不成为可清理候选。受保护记录不能通过自定义规则或篡改计划进入清理选择，拒绝原因可观察。扫描和预演不修改或删除测试数据。

迁移理由（模型建议）：直接覆盖 PRD 的基础资格和用户数据保护要求，不依赖历史 issue。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/src/clean/tests.rs:334
  源码引文：let err = validate\_for\_deletion\_with\_rule(&amp;sessions, Some("go.build\_cache"))         .expect\_err("Codex session history must never be cleanable")         .to\_string();      assert!(         err.contains("protected user data"),         "unexpected error: {err}"     );；实际调用以全局规则名校验 Codex sessions，断言保护错误；没有覆盖扫描、自定义规则及全部用户记录。
- 来源：PRD 基础用例，没有历史 issue 支撑。
### TC008 生成计划后替换父目录或扫描根为外部链接

对应需求：R2；分类：计划重验证；状态：未执行。

增量价值（模型判断）：补充父目录链及扫描根替换，现有目标产品测试主要替换候选末级目录。

前置条件：在支持目录链接的 macOS、Linux 或 Windows 隔离环境生成合法项目计划；Windows 创建链接所需权限已具备。；根外目录包含同名产物和哨兵文件，保存内容快照。

1. 生成计划后移走候选父目录，在原位置建立指向根外目录的链接，使候选末级路径仍可解析。
2. 分别执行计划预演和真实清理，检查拒绝信息及文件快照。
3. 使用独立夹具将扫描根本身替换为外部目录链接，再重放计划。

**预期结果：** 父目录链逃逸和根路径形态变化均被拒绝，不沿链接清理外部同名产物；外部文件、移走的原项目及替代目录内容不变。错误能够定位相关路径或根边界。

迁移理由（模型建议）：历史报告提供父目录符号链接导致删除越界的触发线索，所给 PR 补丁也包含父链接拒绝断言；不据交叉引用认定修复关系，不迁移 Git 丢弃功能、末级链接删除策略或批量原子性。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/src/plan/tests.rs:239
  源码引文：fs::remove\_dir\_all(&amp;candidate).unwrap();     \#\[cfg(unix)\]     std::os::unix::fs::symlink(&amp;real, &amp;candidate).unwrap();     \#\[cfg(windows)\]     std::os::windows::fs::symlink\_dir(&amp;real, &amp;candidate).unwrap();      assert!(revalidate\_selected(&amp;plan, selected).is\_err());；触发条件为候选末级目录换成链接，断言重验证失败；未替换父目录或扫描根，也没有实际清理后的内容断言。
- 来源：[stablyai/orca — \[Bug\]: Discard can delete files outside the worktree through symlink parents](https://github.com/stablyai/orca/issues/2928)
  原文证据：Discarding a path under a symlinked parent deletes files OUTSIDE the worktree via the rm fallback — data loss beyond the repository.
  关联 PR：[Guard untracked discard against symlink escapes](https://github.com/stablyai/orca/pull/2947)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
### TC009 混合恢复批次不覆盖用户目标，拒绝链接且失败后继续

对应需求：R4；分类：恢复保护与批次；状态：未执行。

增量价值（模型判断）：补充交互混合批次、用户内容逐字保留、父链接、失败继续和汇总退出码。

前置条件：隔离 graveyard 有可恢复项、已有用户目标项、父目录链接指向外部的项。；保存 payload、manifest、已有目标及外部文件内容，提供受控 TTY。

1. 执行交互 restore --dry-run，核对 newest-first 顺序，用编号和范围选择混合批次并确认。
2. 比较快照及缺失目标父目录。
3. 执行真实交互 restore，用 all 选择并确认。
4. 核对成功项内容、拒绝项 payload、统计和退出码。

**预期结果：** 预演不移动 payload、不创建目标目录、不更新 manifest。真实恢复不覆盖已有用户内容、不沿链接写入外部目录；拒绝项不妨碍可恢复项继续处理。restored/skipped/failed 总数与结果一致，有任何项未恢复则非零退出。

迁移理由（模型建议）：迁移历史报告中已有用户内容被恢复操作覆盖的触发条件；不迁移升级功能或将提炼的可能根因写成事实。批次与预演断言来自 PRD。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/graveyard\_subcommands.rs:199
  源码引文：.args(\["restore", "--id", &amp;id\])         .assert()         .failure()         .stderr(predicate::str::contains("already exists"));；该唯一调用片段位于重新创建原目标目录的测试中，覆盖直接恢复拒绝已有目标；没有用户内容保留或批次继续断言。
- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/graveyard\_subcommands.rs:250
  源码引文："restore",             "--id",             &amp;id,             "--to",             alternate.to\_str().unwrap(),             "--dry-run",         \])         .assert()         .success()         .stdout(predicate::str::contains("would attempt to restore"))         .stdout(predicate::str::contains("payload"))         .stdout(predicate::str::contains(alternate.to\_str().unwrap()));      assert!(!original.exists());     assert!(!alternate.exists());     assert!(         !alternate.parent().unwrap().exists(),         "dry-run must not create the target parent"     );     assert\_eq!(         fs::read(manifest\_path(&amp;graveyard)).unwrap(),         manifest\_before     );     assert\_eq!(active\_records(&amp;graveyard).len(), 1);；覆盖直接 ID 恢复预演、目标父目录不创建和 manifest 不变；不覆盖交互混合批次及链接目标。
- 来源：[career-ops-hq/career-ops — update-system.mjs apply: failed update triggers a rollback that wipes a git-tracked user file (interview-prep/story-bank.md)](https://github.com/career-ops-hq/career-ops/issues/995)
  原文证据：The rollback \*\*reset \`story-bank.md\` to the upstream stub\*\* (\`&lt;!-- Stories will be added here --&gt;\`), discarding accumulated stories.
  关联 PR：[fix(updater): git-safety on abort + preserve user files on safety-violation rollback (\#915)](https://github.com/career-ops-hq/career-ops/pull/1099)；已合并，交叉引用不等于确认修复。
  关联 PR：[fix(updater): fix three git-safety bugs that can lose uncommitted work (\#915)](https://github.com/career-ops-hq/career-ops/pull/1066)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[fix(updater): preserve user files during safety-violation rollback (\#995)](https://github.com/career-ops-hq/career-ops/pull/1061)；未合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  PR 关联扫描达到数量上限，结果可能不完整。
### TC010 父目录排除后的深层重新包含及命令行覆盖

对应需求：R5；分类：忽略作用域与错误契约；状态：未执行。

增量价值（模型判断）：新增整个父目录排除后重新包含深层项目，以及命令行排除与文件否定规则叠加。

前置条件：单一扫描根包含多个子项目；根 .rcleanignore 排除 legacy-monorepo/，再重新包含 important-app/node\_modules。；另备非法 .rcleanignore 和非法 --ignore 的独立夹具。

1. 扫描共同根，核对深层重新包含路径及其他排除路径。
2. 叠加匹配重新包含路径的 --ignore，重新扫描。
3. 分别使用非法忽略文件和非法命令行 glob 扫描，记录告警和退出状态。

**预期结果：** 深层重新包含符合 PRD 示例；命令行忽略仍可排除被文件重新包含的路径。非法 --ignore 使扫描失败；非法 .rcleanignore 告警后继续报告合法候选，并标明结果可能不完整。

迁移理由（模型建议）：历史案例提示扫描入口变化可能影响忽略作用域；仅迁移作用域边界到明确支持的单根嵌套项目。所给 ripgrep PR 未合并，其多根测试不构成 rclean 覆盖或多位置参数支持依据。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/ignore\_file.rs:117
  源码引文：std::fs::write(         temp.path().join(".rcleanignore"),         "\*\\n!node\_modules/\\n!package.json\\n",     )     .unwrap();      Command::cargo\_bin("rclean")         .unwrap()         .args(\[             "scan",             temp.path().to\_str().unwrap(),             "--json",             "--min-size",             "0",         \])         .assert()         .success()         .stdout(predicate::str::contains(             "\\"ruleId\\": \\"node.node\_modules\\"",         ));；已有触发为根级通配排除后重新包含，断言候选出现；不等同于父目录排除后的深层重新包含。
- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/ignore\_file.rs:281
  源码引文："--ignore",             "{a,b",         \])         .assert()         .failure()         .stderr(predicate::str::contains("invalid --ignore glob"));；已有非法命令行 glob 的失败和诊断断言，此基础部分无新增。
- 来源：[BurntSushi/ripgrep — \`.gitignore\` not taken into account when multiple search paths are provided](https://github.com/BurntSushi/ripgrep/issues/3376)
  原文证据：6. \`rg "this" src/ tests/\` =&gt; \*\*\`src/invalid\` is found\*\* 7. \`rg "this" tests/ src/\` =&gt; funnily, \`src/invalid\` is not found
  关联 PR：[chore(deps): update ⬆️ mise-packages](https://github.com/scottames/dots/pull/980)；已合并，交叉引用不等于确认修复。
  PR 正文/补丁存在截断或缺失；完整范围见 JSON 标记。
  关联 PR：[ripgrep 15.2.0](https://github.com/Homebrew/homebrew-core/pull/293401)；已合并，交叉引用不等于确认修复。
  关联 PR：[fix(ignore): respect .gitignore with multiple search paths](https://github.com/BurntSushi/ripgrep/pull/3417)；未合并，交叉引用不等于确认修复。
### TC011 陈旧度、摘要、解释及筛选后的不完整告警一致

对应需求：R6；分类：报告与解释；状态：未执行。

增量价值（模型判断）：补充陈旧度、解释、百分比和类别筛选分支；大小筛选后保留告警已有覆盖。

前置条件：准备活动时间可控制的新旧项目，配置 stale\_after\_days=60，候选大小及项目总大小可核对。；注入稳定遍历错误；权限夹具仅在适用平台以非特权身份使用。；准备能够过滤出错候选的大小或类别条件。

1. 比较人工与 JSON 扫描的候选、字节数及陈旧度。
2. 执行 explain，核对分类原因和恢复提示。
3. 过滤出错候选后再次比较两种输出的告警含义。
4. 核对 Biggest wins 的候选大小及项目产物百分比。

**预期结果：** 人工输出有 Stale，JSON 有 staleAfterDays=60，并在可获得时报告相符的 stalenessDays。解释符合扫描分类，摘要数据与夹具一致。JSON 顶层 warnings 和人工摘要均保留实际错误及结果可能不完整的含义，不因候选被筛掉而隐藏错误。

迁移理由（模型建议）：迁移历史报告中筛选参数改变不完整告警的触发条件，不迁移分页、招聘平台或编辑配置建议。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/ignore\_file.rs:347
  源码引文：let filtered = run\_json("4097");     assert\_eq!(filtered.status.code(), Some(3));     let filtered\_report: Value = serde\_json::from\_slice(&amp;filtered.stdout).unwrap();     assert\_eq!(filtered\_report\["summary"\]\["candidates"\], 0);     assert\_eq!(filtered\_report\["warnings"\], first\_report\["warnings"\]);      Command::cargo\_bin("rclean")         .unwrap()         .args(\["scan", temp.path().to\_str().unwrap(), "--min-size", "0"\])         .assert()         .success()         .stdout(predicate::str::contains("Warnings during scan:"))         .stdout(predicate::str::contains("Results may be incomplete."));；不可读目录触发遍历错误后，大小筛选排除候选仍保留 warnings，并检查人工不完整提示；没有陈旧度、解释及百分比断言。
- 来源：[career-ops-hq/career-ops — scan.mjs --since gets the wrong max\_pages cap warning (sinceMs is no longer a clean proxy after \#2418)](https://github.com/career-ops-hq/career-ops/issues/2495)
  原文证据：Run \`node scan.mjs --since 7d\` → same tenant, same cap, but the warning now reads \`truncated at N pages (X of Y jobs)\`, with no suggestion. ❌
  关联 PR：[fix(workday): key the cap-hit warning on entry provenance, not on --since](https://github.com/career-ops-hq/career-ops/pull/2763)；已合并，交叉引用不等于确认修复。
  关联 PR：[docs(workday): correct the stale ctx.sinceMs caller note after \#2418](https://github.com/career-ops-hq/career-ops/pull/2496)；已合并，交叉引用不等于确认修复。
### TC012 按阶段断管保护删除边界并保留既定退出状态

对应需求：R7；分类：输出与管道；状态：未执行。

增量价值（模型判断）：新增部分读取后关闭、清理完成后的成功与失败状态及非断管错误；现有夹具在启动前关闭读端。

前置条件：具备可控制关闭时机的消费者或输出故障注入设施，直接收集生产者退出状态。；准备成功清理及稳定失败的隔离夹具，保存候选内容。；支持注入非 EPIPE 写错误；Unix 可控制继承的 SIGPIPE 状态。

1. 读取 rules 和 scan 部分输出后关闭消费者，检查 stderr 和状态。
2. 在 clean 删除前输出阶段断管，比较候选内容。
3. 在清理已完成、退出状态已确定而摘要尚未写完时断管，分别测试成功和失败夹具。
4. 独立注入非 EPIPE stdout 写错误。

**预期结果：** 断管无 panic、backtrace 或异常崩溃。删除前断管保留全部候选内容；删除完成后的断管保留原计算状态，失败不能变成功。其他 stdout I/O 错误明确失败；不照搬其他产品的 141 退出约定。

迁移理由（模型建议）：迁移下游关闭、继承 SIGPIPE 状态和管道掩盖失败的触发线索。所给 Codewhale 测试关闭的是 MCP 子进程 stdin，不等同于 stdout 消费者关闭；rtk 非断管写错误 PR 未合并，只作为边界提案证据。

- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/cli/pipe\_output.rs:10
  源码引文：let (reader, writer) = io::pipe()?;     drop(reader);      let mut command = Command::cargo\_bin("rclean")?;；表明断管发生在命令启动前，没有覆盖运行中或删除完成后关闭。
- 现有测试：/Users/lifcc/Desktop/code/AI/tools/test/issue-lens/out/five-products-20261002/inputs/tests/rclean/tests/cli/pipe\_output.rs:58
  源码引文：let output = run\_with\_closed\_stdout(&amp;\[         "clean",         &amp;root,         "--all",         "--yes",         "--permanent",         "--min-size",         "0",     \])?;      assert\_eq!(output.status.code(), Some(0));     assert\_no\_output\_panic(&amp;output);     assert!(         candidate.exists(),         "closed pre-delete stdout must stop clean"     );；覆盖启动前断管时永久清理退出 0、无输出 panic 且候选存在；未断言内容逐字不变或完成后的失败状态。
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
- 来源：[google/zx — Awkward behavior on error with pipe](https://github.com/google/zx/issues/640)
  原文证据：hello not error at first file:///wd/temp.ts:106     await $\`exit 1\`.pipe($\`echo hello\`);
  关联 PR：[fix: propagate rejection on pipe](https://github.com/google/zx/pull/899)；已合并，交叉引用不等于确认修复。

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：尚未充分覆盖全部生态、精确 home 锚点、GOPATH/XDG、不存在路径静默跳过，以及 macOS arm64/x64、Linux x64/arm64、Windows x64 平台组合。--tmp 顶层命名与项目标记、macOS --system 精确 allowlist/report-only/requiresSudo、X 代码签名目录仅显式扫描仍需专项覆盖。浏览器、壁纸等列出锚点与总边界的解释待确认，不据此扩展到任意大目录。
- R2：尚未充分覆盖最终验证与删除之间再次替换的竞争窗口、Windows 父目录 junction/reparse point、标记移除、实时变为 caution，以及宽泛根和 --allow-broad-root 的端到端行为。T1/T2 已有候选消失、末级链接及部分篡改拒绝断言，但不能证明所有入口同等覆盖。
- R3：smallest safe set 的最优准则未明确，复杂组合暂不能确定按最少数量还是最少超额字节验收。stamp 的变化判据及时间窗口未提供，同大小内容变化、时间戳精度和 sweep 后再变化未充分覆盖。
- R4：显式 clean 默认 Trash 与无子命令 graveyard 的适用入口需澄清。恢复 q、取消确认、全部选择语法、payload 丢失和权限失败未充分覆盖。T3 已有直接 --to、非 TTY 拒绝、older-than 和不支持参数拒绝测试，本草稿未补齐其平台与交互组合。
- R5：depth、min-size 等值边界、older-than 活动判定、category/rule 组合，以及 blocked 不因大小而被过滤的要求未充分覆盖。自定义规则非法类别、缺失字段和非法 name\_glob 仍需补充。未明确多位置参数支持，不照搬历史产品的多根命令。
- R6：陈旧度不可获得的表达、阈值等值边界、空项目百分比、多错误汇总和全部输出分支未充分覆盖。诊断、优化、补全及手册仅部分列名，缺少完整验收行为；未读取链接文档，不能据其补充要求。
- R7：指定阶段断管和非 EPIPE 注入需要受控设施，必须验证实际关闭阶段。全部输出命令、支持平台和 stderr 自身失败尚未充分覆盖。所给源码仅供静态比较，不代表执行结果。
- R8：Docker CLI 缺失、daemon 不可达、非零退出、畸形或部分输出及版本差异未充分覆盖。PRD 未规定整个多子进程报告的总时限及超时准确退出码，不能编造断言。全部 coverage 判断仅限提供的 T1–T5 和可见 PR 补丁；截断或缺失补丁不证明没有回归测试，也未检查整个仓库或执行测试。
- 待确认：默认清理目的地存在冲突：Usage 明确描述无子命令交互清理移动到 rclean graveyard，Safety Model 则写“default clean mode moves to Trash when available.”。是否分别适用于不同入口？各入口的默认删除模式需明确。
- 待确认：产品边界限定为开发产物和工具链缓存，但规则目录包含浏览器缓存、壁纸视频、地图及媒体分析缓存。应将这些已列出的精确锚点视为明确范围例外，还是收窄规则目录？不能据“every cache”扩展到任意目录。
- 待确认：Current Status 的功能列表属于现状描述，不能据此推导新增需求；其中仅列名、缺少行为契约的诊断、优化、补全和手册功能是否另有验收要求？所链接文档内容未提供，无法据其补充要求。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
