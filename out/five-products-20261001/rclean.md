# 基于真实 issue 的测试方案

状态：**待评审、未执行**。以下是从同类产品历史问题迁移的测试建议，不是目标产品的已确认缺陷。

产品形态：cli；语料：16054 条；本次选入：12 条；测试建议：13 条。

来源只含 issue 标题与正文；没有读取关联 PR 补丁或评论。根因与适用性仍需人工复核。

## 需求与检索范围

- **R1 扫描与批量清理安全：校验项目标记、阻止符号链接，谨慎项须显式纳入**：- \`scan\` never deletes files. - blocked candidates are never selected by \`clean --all\`. - symlink candidates are blocked. - generic directories like \`build\`, \`dist\`, \`out\`, \`target\`, and \`vendor\` require   project marker evidence. - Python \`venv\` must contain virtualenv markers. - dirty git worktrees downgrade otherwise safe candidates to \`caution\`. - \`--all\` selects only \`safe\` candidates unless \`--include-caution\` is passed.
  检索词：symlink, classification, marker, deletion；选入候选 2 条。
- **R2 清理计划回放：删除前重新验证路径，拒绝新增符号链接及根路径变化**：The action plan is the trust boundary: \`clean --plan\` re-validates every path against the live filesystem before deleting, refuses to follow new symlinks, and rejects plans whose roots have changed shape since the scan.
  检索词：revalidation, symlink, race, traversal；选入候选 2 条。
- **R3 恢复操作：交互选择与确认、目标冲突检查、批量失败统计及无副作用预览**：Restore one grave directly with \`rclean restore --id &lt;ID&gt;\`. Add \`--to &lt;PATH&gt;\` to choose another destination. Running \`rclean restore\` without \`--id\` on a terminal opens a newest-first numbered selector that accepts numbers, ranges, \`all\`, or \`q\`, then asks for confirmation. Every selected item still passes through the same target-exists and symlink checks as a direct restore. A batch continues after an item is skipped or fails, prints restored/skipped/failed totals, and exits non-zero when any item was not restored.  Add \`--dry-run\` to either form to preview the selected restore operations without moving payloads, creating target directories, or updating the manifest:
  检索词：restore, collision, partial, dry-run；选入候选 2 条。
- **R4 按空间目标生成最小安全清理提案：不直接删除，正确处理不足及空结果**：\`rclean free &lt;size&gt;\` computes the smallest safe set that can meet a target reclaim amount and writes it as an ActionPlan for review. It never deletes by itself; replay the plan with \`rclean clean --plan ... --dry-run\` first. \`free --json\` emits a versioned proposal containing \`targetBytes\`, \`selectedBytes\`, \`targetMet\`, \`planPath\`, and the selected scan candidates. Exit code \`0\` means the target was met; exit code \`3\` means the safe set was short or empty. A short proposal still writes a reviewable plan, while an empty proposal reports \`planPath: null\` and writes none.
  检索词：selection, capacity, empty, exit-code；选入候选 2 条。
- **R5 管道提前关闭：避免崩溃、保留退出状态，并在删除开始前安全停止**：Non-interactive stdout is pipe-aware. If a downstream reader closes early (for example, \`rclean rules \| head -n 1\`), rclean stops writing without a panic or backtrace and retains any command exit status already determined. Other stdout I/O errors still fail explicitly. For \`clean\`, a closed pipe before the delete phase stops the command before any artifact is removed; if cleanup has already completed, its computed success or failure status is preserved.
  检索词：pipe, stdout, panic, exit-code；选入候选 1 条。
- **R6 忽略规则：文件与命令行排除叠加，区分非法模式的失败与警告**：If both an \`.rcleanignore\` entry and a \`--ignore\` glob match the same path, the path is excluded.  Invalid \`--ignore\` globs fail the scan. Invalid \`.rcleanignore\` files are reported as scan warnings so the scan can continue while still marking the result as potentially incomplete.
  检索词：glob, exclusion, validation, warning；选入候选 1 条。
- **R7 受保护用户记录：扫描、计划回放和删除均拒绝，自定义规则及篡改计划不能绕过**：User records are not cleanup candidates. The following paths are treated as protected user data and refused at scan, plan replay, and delete time — even if a custom rule or tampered ActionPlan points at them:  - \`~/.codex/sessions\`, \`~/.codex/memories\` - \`~/.claude/projects\`, \`~/.claude/sessions\`, \`~/.claude/history.jsonl\`,   \`~/.claude/shell-snapshots\`, \`~/.claude/file-history\`,   \`~/.claude/todos\`
  检索词：protection, bypass, tampering, deletion；选入候选 1 条。
- **R8 Docker 仅报告：子进程有超时、参数按数组传递，任何资源均不执行删除**：\`docker report\` uses the official Docker CLI with bounded subprocess timeouts and array arguments. It does not call \`docker system prune\`, \`docker builder prune\`, \`docker rm\`, \`docker rmi\`, \`docker volume rm\`, or any other deletion command. Build cache and dangling-image categories may be classified as \`caution\` in the report taxonomy, while volumes, named resources, networks, and tagged images remain \`report-only\`; all Docker rows are \`selected=false\` in this release.
  检索词：timeout, subprocess, arguments, deletion；选入候选 1 条。

## 扫描与批量清理安全

### TC001 符号链接候选被阻止且目标内容保持不变

对应需求：R1；状态：未执行。

前置条件：在 macOS 隔离目录中准备含 Cargo.toml 的干净项目。；项目的 target 为指向扫描根之外目录的符号链接，外部目录含已记录内容的哨兵文件。

1. 以包含 blocked 项、最小大小为 0 的选项扫描项目，检查分类并对比文件内容。
2. 分别预览和执行显式永久删除的 clean --all，加入 --include-caution 和 --include-blocked。
3. 检查符号链接及其目标中的哨兵文件。

**预期结果：** 扫描不修改文件；符号链接候选显示为 blocked，所有批量选择均不选中它；链接及外部目标保持不变。

迁移理由（模型建议）：引文分别报告符号链接访问异常和经符号链接父目录删除工作树外文件。迁移链接路径这一触发条件，按 rclean 的阻止策略判定，不沿用编辑器打开链接的功能要求，也不推断相同根因。

- 来源：[stablyai/orca — \[Bug\]: Symlink file cannot be opened, showing "Cannot open symlink target"](https://github.com/stablyai/orca/issues/11654)
  原文证据：Clicking on a soft symlink file displays a "Cannot open symlink target" error instead of opening the target file directly (expected behavior, matching VS Code).
- 来源：[stablyai/orca — \[Bug\]: Discard can delete files outside the worktree through symlink parents](https://github.com/stablyai/orca/issues/2928)
  原文证据：Discarding a path under a symlinked parent deletes files OUTSIDE the worktree via the rm fallback — data loss beyond the repository.

## 计划回放路径验证

### TC002 计划生成后候选被替换为符号链接

对应需求：R2；状态：未执行。

前置条件：在支持符号链接的 macOS 或 Linux 隔离环境中准备合法 Rust 项目及真实 target 目录。；生成选中 target 的永久删除 ActionPlan，并准备含哨兵文件的根外目录。

1. 将原 target 移到夹具保留位置，在原路径创建指向根外目录的符号链接。
2. 先进行计划回放预览，再执行该计划。
3. 检查拒绝信息、原目录和根外哨兵。

**预期结果：** 回放识别新增符号链接并拒绝清理该路径；不删除链接目标或保留位置中的原目录，不把该项报告为清理成功。

迁移理由（模型建议）：引文支持链接路径可能使删除越过仓库边界这一风险场景。将其迁移为扫描后路径变化，用 PRD 的实时重验要求确定预期；历史引文未证明存在扫描与删除之间的竞态根因。

- 来源：[stablyai/orca — \[Bug\]: Discard can delete files outside the worktree through symlink parents](https://github.com/stablyai/orca/issues/2928)
  原文证据：Discarding a path under a symlinked parent deletes files OUTSIDE the worktree via the rm fallback — data loss beyond the repository.
### TC003 候选父目录被替换为指向根外的符号链接

对应需求：R2；状态：未执行。

前置条件：在 macOS 或 Linux 隔离扫描根下准备 app/target，并生成选中它的永久删除计划。；另建根外目录，其中存在同名 target 和哨兵文件。

1. 保留原 app 目录，将扫描根下的 app 替换为指向根外目录的符号链接。
2. 预览并执行原计划。
3. 检查根外 target、哨兵及回放结果。

**预期结果：** 即使叶子路径名称未变，回放仍拒绝经新增符号链接父目录访问的候选；根外内容保持不变。

迁移理由（模型建议）：原文证据明确涉及 symlinked parent 导致工作树外删除，直接适用于验证 rclean 是否检查完整路径而非仅检查叶子目录。

- 来源：[stablyai/orca — \[Bug\]: Discard can delete files outside the worktree through symlink parents](https://github.com/stablyai/orca/issues/2928)
  原文证据：Discarding a path under a symlinked parent deletes files OUTSIDE the worktree via the rm fallback — data loss beyond the repository.
### TC004 计划根目录被替换为符号链接后拒绝回放

对应需求：R2；状态：未执行。

前置条件：在 macOS 或 Linux 隔离环境中，从真实项目根生成永久删除计划。；准备另一目录，包含相同相对路径的候选和哨兵。

1. 将原扫描根移到保留位置，并在原根路径创建指向另一目录的符号链接。
2. 预览并执行原计划。
3. 对比两个目录中的文件及回放结果。

**预期结果：** 回放因根路径形态变化拒绝计划，不沿替换后的根访问并删除另一目录的候选；两处数据均保持不变。

迁移理由（模型建议）：借用经符号链接父路径越界的触发条件，将链接位置提升到计划根；拒绝根形态变化是目标 PRD 的明确要求。

- 来源：[stablyai/orca — \[Bug\]: Discard can delete files outside the worktree through symlink parents](https://github.com/stablyai/orca/issues/2928)
  原文证据：Discarding a path under a symlinked parent deletes files OUTSIDE the worktree via the rm fallback — data loss beyond the repository.

## 恢复冲突保护

### TC005 恢复目标已有数据时不覆盖现有内容

对应需求：R3；状态：未执行。

前置条件：在 macOS 或 Linux 隔离环境中准备有效 grave 及其 payload。；在原恢复位置建立同名目录并放入不同内容的哨兵；另准备同样冲突的 --to 目标。；记录现有目标、payload 和 manifest 内容。

1. 使用 grave 的实际 ID 恢复至原位置。
2. 使用同一 grave 的实际 ID 和 --to 恢复至另一个已存在目标。
3. 检查两处目标和 grave 状态。

**预期结果：** 两次操作均拒绝覆盖已存在目标，不先删除目标再尝试恢复；现有内容及未恢复 payload 保留，结果不声称恢复成功。

迁移理由（模型建议）：引文描述恢复失败时原有子树已丢失或仅部分恢复。迁移为文件恢复遇到现存目标的保护检查，不复制注册表功能，也不假定 rclean 必须实现 PRD 未要求的事务回滚。

- 来源：[Raphire/Win11Debloat — Registry restore deletes the key subtree before rewriting, with no rollback on partial failure (data loss)](https://github.com/Raphire/Win11Debloat/issues/686)
  原文证据：In both cases the live subtree is already gone; the user sees a 'restore failed' message but their registry data is now lost or half-restored (including any live values outside this backup's captured scope).

## 恢复批量失败

### TC006 批量恢复中间项失败后继续并准确统计

对应需求：R3；状态：未执行。

前置条件：在 macOS 或 Linux 的 TTY 中准备三个有效 grave，确保编号顺序已知。；第一项和第三项目标可写且不存在；第二项通过权限夹具在恢复时触发确定的写入失败。；以非特权身份运行，确保失败条件实际生效。

1. 运行不带 --id 的恢复，选择三个项目并确认。
2. 观察第二项失败后是否尝试第三项。
3. 核对各目标实际内容、restored/skipped/failed 汇总和进程退出状态。

**预期结果：** 第一项和第三项恢复成功，第二项记为失败；批量操作继续，汇总为 restored=2、skipped=0、failed=1，退出非零，不将部分恢复报告为全部成功。

迁移理由（模型建议）：引文支持恢复失败可能留下部分完成状态。迁移该条件验证 rclean 明确规定的继续处理、准确汇总和非零退出，不把提炼中的权限变化原因作为已证实历史事实。

- 来源：[Raphire/Win11Debloat — Registry restore deletes the key subtree before rewriting, with no rollback on partial failure (data loss)](https://github.com/Raphire/Win11Debloat/issues/686)
  原文证据：In both cases the live subtree is already gone; the user sees a 'restore failed' message but their registry data is now lost or half-restored (including any live values outside this backup's captured scope).

## 管道提前关闭

### TC007 只读输出遇到提前断管时无 panic

对应需求：R5；状态：未执行。

前置条件：在 macOS 或 Linux 中以非交互 stdout 运行。；接收端能够读取少量内容后立即关闭；测试装置分别采集生产端状态和 stderr。；确保关闭后生产端仍会尝试写入，避免输出已全部进入缓冲区而未触发断管。

1. 让 rules 输出进入提前关闭的接收端。
2. 检查生产端 stderr 和退出情况。
3. 以完整读取输出作为对照。

**预期结果：** 提前断管时停止写入，无 panic 或 backtrace；完整读取时输出正常完成。退出状态遵循 rclean 的已确定状态保留要求，不套用其他产品的 SIGPIPE 退出码。

迁移理由（模型建议）：原文直接描述接收端提前退出触发生产端恐慌，和 R5 的触发条件一致；原文提炼中的具体 Rust 实现原因不作为本方案事实。

- 来源：[Hmbown/Codewhale — Bug: panic on broken pipe (SIGPIPE) — crash dump when piping codewhale output](https://github.com/Hmbown/Codewhale/issues/4030)
  原文证据：When codewhale output is piped to another command (e.g. \`codewhale doctor \| head\`) and the receiving end exits before codewhale finishes writing, the process panics with a noisy crash dump instead of terminating cleanly.

## 管道与退出状态

### TC008 空间提案状态已确定后断管仍保留退出码

对应需求：R5；状态：未执行。

前置条件：在 macOS 或 Linux 隔离目录中分别准备目标可满足、非空但不足、无安全候选三种 free 场景。；设置输出故障注入点，在提案结果已计算完成且仍有 stdout 写入时产生断管。

1. 分别完整读取三种 free --json 调用，记录生产端退出码。
2. 对相同场景在结果确定后的输出阶段触发断管。
3. 采集生产端退出码和 stderr。

**预期结果：** 可满足场景保持退出码 0；不足及空场景保持退出码 3；均不因断管出现 panic 或 backtrace。

迁移理由（模型建议）：借用接收端提前退出这一已引证条件验证 R5 的状态保留；0 和 3 来自 rclean PRD，不采用其他产品的退出语义。本条不覆盖 free 的最小集合算法。

- 来源：[Hmbown/Codewhale — Bug: panic on broken pipe (SIGPIPE) — crash dump when piping codewhale output](https://github.com/Hmbown/Codewhale/issues/4030)
  原文证据：When codewhale output is piped to another command (e.g. \`codewhale doctor \| head\`) and the receiving end exits before codewhale finishes writing, the process panics with a noisy crash dump instead of terminating cleanly.

## 删除前断管

### TC009 清理进入删除阶段前断管不移除任何候选

对应需求：R5；状态：未执行。

前置条件：在 macOS 或 Linux 隔离项目中准备多个 safe 候选并记录完整内容。；采用显式永久删除参数，避免默认删除去向歧义。；测试装置能够在删除前输出阶段稳定触发断管并确认触发时序。

1. 启动 clean --all --permanent --yes，将 stdout 接入受控接收端。
2. 在删除阶段开始前关闭接收端并使下一次写入遇到断管。
3. 检查所有候选和 stderr。

**预期结果：** 命令在删除前停止，所有候选及内容保持不变，无 panic 或 backtrace。

迁移理由（模型建议）：迁移原文的提前断管条件至 rclean 的破坏性操作边界；不推断历史产品曾因断管发生误删。

- 来源：[Hmbown/Codewhale — Bug: panic on broken pipe (SIGPIPE) — crash dump when piping codewhale output](https://github.com/Hmbown/Codewhale/issues/4030)
  原文证据：When codewhale output is piped to another command (e.g. \`codewhale doctor \| head\`) and the receiving end exits before codewhale finishes writing, the process panics with a noisy crash dump instead of terminating cleanly.

## 删除后断管

### TC010 清理已完成后的断管保留成功或失败状态

对应需求：R5；状态：未执行。

前置条件：在 macOS 或 Linux 准备全部清理成功和包含确定删除失败的两套隔离夹具。；使用显式永久删除模式，并能在清理结果确定后的摘要输出阶段注入断管。；能够采集生产端自身的退出状态。

1. 在完整接收输出时运行两套夹具，记录计算结果和退出状态。
2. 重建夹具，在清理完成后的摘要输出阶段分别触发断管。
3. 比较实际清理结果、生产端状态及 stderr。

**预期结果：** 断管不改变已经计算出的清理成功或失败状态，不将失败改为成功；无 panic 或 backtrace，实际文件状态与已完成的清理结果一致。

迁移理由（模型建议）：同一提前关闭接收端的条件用于覆盖 PRD 明确区分的删除后阶段；不要求回滚已完成清理。

- 来源：[Hmbown/Codewhale — Bug: panic on broken pipe (SIGPIPE) — crash dump when piping codewhale output](https://github.com/Hmbown/Codewhale/issues/4030)
  原文证据：When codewhale output is piped to another command (e.g. \`codewhale doctor \| head\`) and the receiving end exits before codewhale finishes writing, the process panics with a noisy crash dump instead of terminating cleanly.

## 忽略规则一致性

### TC011 文件排除与命令行排除在扫描和清理预览中一致

对应需求：R6；状态：未执行。

前置条件：准备四个独立、带项目标记的 safe 候选 A、B、C、D。；.rcleanignore 排除 A 和 C；--ignore 排除 B 和 C；D 不被排除。；各入口使用相同扫描根、大小和其他过滤条件。

1. 分别运行人类可读扫描、JSON 扫描和 clean --all --dry-run。
2. 比较报告及预览中的候选路径。
3. 检查夹具未发生变化。

**预期结果：** A、B、C 均被排除，D 被保留；不同输出和预览入口的排除结果一致，扫描及预览均不修改候选。

迁移理由（模型建议）：原文明确指出两个工具排除集合不一致。迁移同一文件集合经不同入口筛选的条件，不照搬来源产品对 node\_modules 等目录的默认排除策略。

- 来源：[google-gemini/gemini-cli — Consolidate file exclusion patterns between glob tool and read-many-files tool](https://github.com/google-gemini/gemini-cli/issues/6414)
  原文证据：Inconsistent behavior: glob.ts only excludes node\_modules and .git, while read-many-files.ts excludes build dirs, binaries, coverage files, etc.

## 忽略规则叠加

### TC012 文件规则重新纳入后命令行排除仍生效

对应需求：R6；状态：未执行。

前置条件：在 legacy-monorepo 下准备多个合法项目及 node\_modules。；.rcleanignore 排除 legacy-monorepo/，并通过 PRD 示例形式的否定规则重新纳入其中一个项目的 node\_modules。；准备一个只匹配该重新纳入候选的 --ignore 模式。

1. 不加命令行排除进行扫描和清理预览，记录重新纳入项。
2. 加入准备好的 --ignore，再次进行扫描和清理预览。
3. 比较各入口的选择结果。

**预期结果：** 仅使用文件规则时指定候选被重新纳入，其他被排除项目保持排除；加入命令行排除后该候选也被排除，扫描和清理预览一致。

迁移理由（模型建议）：借用多个筛选入口行为不一致的历史现象，检查 rclean 自身定义的否定规则与命令行叠加语义；不声称来源证据包含否定规则故障。

- 来源：[google-gemini/gemini-cli — Consolidate file exclusion patterns between glob tool and read-many-files tool](https://github.com/google-gemini/gemini-cli/issues/6414)
  原文证据：Inconsistent behavior: glob.ts only excludes node\_modules and .git, while read-many-files.ts excludes build dirs, binaries, coverage files, etc.

## 用户数据保护

### TC013 清理候选与受保护记录共存时保留全部记录

对应需求：R7；状态：未执行。

前置条件：使用隔离 HOME，不接触真实用户记录。；创建 PRD 列出的全部受保护路径，各自放入可核对的合成内容，同时准备合法 safe 缓存。；记录受保护内容，清理时显式指定永久删除模式。

1. 扫描隔离 HOME；对没有被 --home 遍历到的受保护路径另做显式扫描。
2. 检查受保护路径是否进入可选择候选集合。
3. 对隔离 HOME 执行允许宽根的批量清理，包含 caution 项。
4. 逐项对比受保护记录，并确认合法缓存按选择结果处理。

**预期结果：** 受保护记录不成为可清理项，内容保持不变；包含 caution 或允许宽根均不解除用户数据保护。

迁移理由（模型建议）：唯一原文证据是标题所报告的清理误删 helper，未给出路径或复现条件。仅借用清理时混有应保留数据这一有限场景检查目标产品明确的保护名单，不引入 Aldente 功能或断言历史根因。

- 来源：[tw93/Mole — \[BUG\] \`mole clean\` deletes Aldente helper tool](https://github.com/tw93/Mole/issues/753)
  原文证据：\[BUG\] \`mole clean\` deletes Aldente helper tool

## 覆盖缺口与待确认事项

这不是完整的 PRD 覆盖率统计：当前仅抽取最多 8 个主题，受形态语料、关键词和候选数量限制。

- R1：已覆盖符号链接候选及扫描不删除，但缺少与项目标记缺失、虚拟环境标记、脏工作树降级及 caution 显式纳入相关的原文触发证据。相对链接与工作目录变化仅见模型提炼，858324277 的 evidence\_quote 不足以独立确认完整条件，未据此生成专门用例。Windows 链接权限及跨平台差异也未充分覆盖。
- R1：默认清理去向在 graveyard 与 Trash 之间存在待澄清冲突，已有清理用例显式采用永久删除，不能覆盖默认模式。模型目录 report-only 与部分 caution 规则的范围也尚不明确，不能制定统一选择预期。
- R2：已覆盖候选、父目录和根被替换为符号链接；未充分覆盖非链接形式的根变化、验证完成到实际删除之间的时序变化及 Windows 路径行为。5145521751 的原文仅说明未捕获异常使测试框架终止，不能证明与计划回放相关的具体触发条件，未迁移测试框架功能。
- R3：已覆盖目标冲突和部分失败继续处理；最新优先排序、数字与范围及 all/q 输入、取消确认、恢复路径符号链接检查、跳过项统计、直接及交互 dry-run 的 payload/目录/manifest 无副作用尚未充分覆盖。5357643798 的引文只证明发布过程部分上传后验证失败，没有 dry-run 的原文证据，不能据提炼将其作为恢复预览故障证据。批量恢复也未据历史材料扩展为 PRD 未承诺的事务回滚。
- R4：没有直接相关的空间提案选择证据：4399114659 引文涉及会话状态为空，4671767128 涉及窄终端分隔符导致容量溢出，均不能用来验证磁盘空间集合选择。尚缺最小安全集合、禁止直接删除、JSON 版本和字段、不足时仍写计划、空结果不写计划等覆盖；smallest safe set 的优化目标也待明确。R5 中的退出码用例仅检查断管状态保留。
- R5：已覆盖提前断管、已确定退出状态及删除前后边界；非 Broken pipe 的 stdout I/O 错误必须显式失败尚无对应历史证据。Windows 管道行为也未覆盖；SIGPIPE 继承状态仅见模型提炼，未作为已证实历史触发条件。删除阶段时序用例需要可控输出注入，普通 head 管道不足以证明命中指定阶段。
- R6：已覆盖排除叠加和入口一致性；非法 --ignore 必须失败、非法 .rcleanignore 只产生可恢复警告、JSON warnings 与表格警告一致及结果不完整标记仍缺少相关历史证据，不能由来源的排除列表不一致推断这些错误路径。
- R7：误删来源仅有标题，证据强度有限。已生成普通清理共存保护用例，但自定义规则绕过、篡改 ActionPlan、回放及实际删除阶段分别重验保护名单尚无具体历史触发证据，不能把普通清理用例视为这些绕过场景已覆盖。
- R8：16408569 的原文是 shell 补全辅助函数不存在，与 Docker 报告的子进程超时、数组参数和禁止删除无实质关联，因此不生成用例。超时处理、参数边界、资源分类、所有行 selected=false、禁止删除命令及不生成文件系统候选或 ActionPlan 项均缺少相关历史证据。
- 待确认：默认删除去向存在冲突：Usage 指定无子命令交互流程默认移入 rclean graveyard，Safety Model 则写明默认 clean 在可用时移入 Trash。两者是否按调用方式区分？普通 clean 及计划中的默认 deleteMode 应采用哪一种？
- 待确认：Product Boundaries 要求本地模型存储等高成本用户数据保持 report-only，但规则表将 HuggingFace Hub 和 Whisper 模型列为 caution。哪些模型目录属于明确允许清理的缓存例外，哪些必须始终禁止选择？
- 待确认：free 所称“smallest safe set”是最少候选数量、最小总字节数，还是其他优化目标？这会影响提案选择结果的测试判定。

详细来源、提炼结果、模型调用信息与 PRD 摘要哈希见同名 JSON。
