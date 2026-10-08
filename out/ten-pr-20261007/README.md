# 10 个真实 PR 对照与执行：2026-10-07

**10 个不同项目的真实 PR 已全部执行，两组共生成并逐项复核 93 条建议。实验发现 1 个可独立复现的 tqdm 异常后锁恢复缺陷；仍没有证据证明历史材料整体优于直接读代码。** 真实维护者评价未获得，已采纳且有效建议与额外人工审查时间均未知；不能把本机技术验证称作外部采纳。

6 个 PR 未选到适用历史，A/B 是同输入的重复生成，不能算历史处理有效的配对；4 个 PR 的 B 组实际加入历史，只有5条B建议引用了历史。全部10个原始范围保留，没有用 rclean 旧案例代替，也没有为了凑处理组加入不相关来源。[冻结协议](PROTOCOL.md) · [机器汇总](summary.json) · [10对输入一致性核验](selected-pairs.json)

## 每个 PR 的真实结果

| 真实 PR | 固定 head | A / B 建议 | B 历史来源 | 相关原生测试 | 证据 |
|---|---|---:|---:|---|---|
| [Textualize/rich #3180](https://github.com/Textualize/rich/pull/3180) | `05c5dfc8fcbb` | 4 / 5 | 0 | 114 passed | [逐项](assessment_Textualize--rich.json) / [原生](native_Textualize--rich.json) |
| [pallets/click #3865](https://github.com/pallets/click/pull/3865) | `f67c2bb6c2f0` | 4 / 5 | 0 | 36 passed | [逐项](assessment_pallets--click.json) / [原生](native_pallets--click.json) |
| [fastapi/typer #1821](https://github.com/fastapi/typer/pull/1821) | `5bec961514de` | 5 / 5 | 1 | 9 passed | [逐项](assessment_fastapi--typer.json) / [原生](native_fastapi--typer.json) |
| [theskumar/python-dotenv #700](https://github.com/theskumar/python-dotenv/pull/700) | `004b454e37f4` | 5 / 5 | 0 | 45 passed | [逐项](assessment_theskumar--python-dotenv.json) / [原生](native_theskumar--python-dotenv.json) |
| [tox-dev/platformdirs #566](https://github.com/tox-dev/platformdirs/pull/566) | `0fe7a0c57a0c` | 5 / 5 | 1 | 352 passed / 6 skipped | [逐项](assessment_tox-dev--platformdirs.json) / [原生](native_tox-dev--platformdirs.json) |
| [tox-dev/filelock #756](https://github.com/tox-dev/filelock/pull/756) | `2a533f305344` | 5 / 5 | 0 | 128 passed | [逐项](assessment_tox-dev--filelock.json) / [原生](native_tox-dev--filelock.json) |
| [pypa/packaging #1430](https://github.com/pypa/packaging/pull/1430) | `45473a150d41` | 4 / 4 | 0 | 7382 passed | [逐项](assessment_pypa--packaging.json) / [原生](native_pypa--packaging.json) |
| [cpburnz/python-pathspec #142](https://github.com/cpburnz/python-pathspec/pull/142) | `73120f31ad25` | 5 / 4 | 0 | 6 passed | [逐项](assessment_cpburnz--python-pathspec.json) / [原生](native_cpburnz--python-pathspec.json) |
| [tqdm/tqdm #1830](https://github.com/tqdm/tqdm/pull/1830) | `24b9e1e08a09` | 5 / 5 | 1 | 13 passed / 3 skipped；3.14 另16 passed | [逐项](assessment_tqdm--tqdm.json) / [原生](native_tqdm--tqdm.json) |
| [python-humanize/humanize #392](https://github.com/python-humanize/humanize/pull/392) | `244ac0ed6bae` | 4 / 4 | 1 | 234 passed | [逐项](assessment_python-humanize--humanize.json) / [原生](native_python-humanize--humanize.json) |

这些是当前固定head上指定原生文件的结果，包含PR已有测试，不能算新增有效建议。platformdirs六项Windows测试在本机跳过；补充检查的Windows mock与Unix类本机调用没有冒充原生Windows/Linux/Android验收。filelock仅验证相关文件，未宣称完整tox通过。其浅克隆版本识别和virtualenv版本约束冲突、dotenv首轮PATH失败及修正均保留在日志。

## 建议执行与真实发现

| 技术执行指标 | A：直接代码等资料 | B：额外历史 |
|---|---:|---:|
| 生成并逐项复核 | 46 | 47 |
| 执行者采用为隔离回归/跟进候选 | 27 | 25 |
| 复核已有完整覆盖 | 18 | 20 |
| 真实维护者采纳且有效 | 未评价 | 未评价 |

52条“技术采用”按arm-case计数，跨组可能同场景；这是代理执行者选择进行验证/跟进，未提交这些测试到样本项目，不能当成52条维护者采纳。初次补充执行111个参数化检查：110通过、1失败。tqdm隔离复核另3项通过，初次失败保留；既有原生通过不能覆盖该新序列失败。判断与原生断言、脚本、JUnit、命令、退出码逐项相连。[前五汇总](native_first_five_summary.json) · [后五汇总](assessment_last_five_summary.json)

**tqdm：工作函数异常污染后续并发调用。** B TC001要求未知长度输入下工作函数的`ValueError`真实传播，这一断言通过；随后正常`process_map`失败，执行者追加锁恢复调查。默认API、无monkeypatch的独立复现显示：`interpreter_map`工作函数失败后，`tqdm.auto`全局锁变为`_InterpreterLock`且未恢复，后续`process_map`报`TypeError: cannot pickle '_thread.RLock' object`。失败序列exit1，成功工作函数对照exit0，已知长度错误对照也exit1。[具体判断与源码行](assessment_tqdm--tqdm.json) · [最小复现](evidence/model-checks/reproduce_tqdm_error_lock.py) · [失败日志](evidence/logs/model-checks/tqdm--tqdm/07_reproduce_error_lock.log) · [成功对照](evidence/logs/model-checks/tqdm--tqdm/08_control_success.log)

`ensure_lock`的`yield`之后恢复缺少`finally`，异常跳过恢复；旧base源码有相同机制。旧base二进制/运行时未执行，“既有、不是本PR新引入”是相同源码和已知长度对照支持的推断。未确认上游此前是否已知该缺陷。锁恢复和后续调用验证是实际失败后的追加调查，不能说原模型预言了锁泄漏，不能将Mole弱类比归因成已证明的因果收益。没有修改tqdm生产代码或发送外部消息。

历史来源的技术判断：Typer←Codewhale默认值、platformdirs←orca克隆中止、tqdm←Mole慢统计三处是弱类比，不认定相同故障机制；humanize←n8n数值转换精度是有限相关，语言、输入形态及溢出边界不同。n8n关联PR的范围检查也不能当成精度问题已修复的证明。**未生成确认缺陷指控不等于误报率为0。** 当前能报告这些弱类比/覆盖纠正，真实维护者的建议误报与有效性判断仍为空。

## 时间、调用与费用边界

- 20份有效方案：A输入337,060/output25,018 tokens；B输入350,373/output26,814 tokens。B输入约多3.95%，但只有4对实际增加历史，不能归因为纯历史开销。
- 有效方案模型等待：A 906.5秒、B 1138.5秒；共享需求分析及历史检索/提炼/PR证据准备另686.9秒。这是阶段耗时之和，并行执行时不等于全程墙钟，也不等于人类审查时间。
- 前置阶段在内，共43个不同已完成模型调用：输入1,126,353 tokens（其中187,264 cached，已包含在输入中），输出57,643。两次原方案超时另耗约600秒，没有usage回执，耗用未知；不能按零计费。

filelock A、packaging B首次300秒超时的原始状态不变。各只做一次明确重跑，复用同一冻结输入、模型、提示词与检查；有效pair选自runs-2，其余选runs-1。原主run仍以失败状态保存，不伪装成首轮全通过。[成本明细](costs.json) · [原失败总览](runs-1/run.json) · [同输入重跑脚本](evidence/retry_exact.py)

使用实际Codex CLI0.160.0，固定请求`gpt-6.1-sol`；成功回执记录thread_id和usage，没有独立确认的底层供应商模型身份。真实账单、订阅额度折算费用、维护者额外审查时间未知，没有生成美元成本。前期不兼容模型/失败API连通检查单独记录，不混入实验结果。[环境与连通边界](environment.json)

## 原范围状态与交付

| 范围 | 状态 | 交付/缺项 |
|---|---|---|
| 复用已有diff筛选、测试对照、关联PR及rclean历史 | 已完成 | 复用现有模块；历史5场景通过、3边界入测试、无新缺陷的原记录不变，未计作本实验增益。 |
| 不同项目10PR、同模型同代码版本A/B | 已完成执行；真实维护者判断待验证 | 20份输出/93条复核；6对缺适用历史，不计历史有效处理。 |
| 实际模型、代码、原生测试、误报及成本 | 已完成可得技术执行；已实现待人类验证 | 原生/补充失败均保留；有效维护者采纳和审查时间尚不可得。 |
| 其他chat仓库只读、独立样本环境 | 已完成 | 10个专属clone/venv；最终head固定、工作区干净；未写litellm/remem/refine/harness。 |
| 最小流程缺口/可重复命令与报告 | 已完成 | 一个薄实验入口、同输入重跑、冻结资料、执行证据及报告；未扩语料或建新平台。 |
| 真实参与者评价入口及缺项 | 已实现待验证／受阻 | 93行[维护者评价表](maintainer-review.csv)；无人类评价，未擅自招募或发消息。 |
| 相关升级/恢复可作为diff场景；不另建平台 | 已完成边界保持 | 当前样本按实际diff验证，不强加无关升级功能，不新增平台仓库。 |
| 发布PR | 已完成（2026-10-08） | [PR #2](https://github.com/majiayu000/issue-lens/pull/2)已创建；认证恢复为仓库所有者，权限ADMIN。实验阶段的只读权限阻塞已解除。 |

维护者可打开对应逐项JSON、冻结输入和原始脚本，填写评价表的适用、已有覆盖、可执行、真实问题、是否采纳、采用后有效及review_minutes。字段是开放判断，不用规则引擎替维护者打分；缺项必须保持空值。Windows/Linux/Android原生设备验收如涉及相应建议也仍需要真实环境。

**本轮决策：当前不扩大语料库。** 6个空历史、3个弱类比，以及只有一个需要执行者追加调查的真实发现，足以支持继续核验这个窄流程，尚不足以证明扩大采集规模有收益。保留现有库和实验入口，待真实维护者判断及准确审查时间后再作扩大决定。

## 复跑与证据

```sh
ISSUE_LENS_LLM_ENGINE=codex ISSUE_LENS_MODEL=gpt-6.1-sol \
python3 experiments/ten_pr_comparison.py \
  --inputs out/ten-pr-20261007 --db /absolute/path/issues.db \
  --out /absolute/path/new-run
```

新的目录才允许运行；已有目录拒绝覆盖已实际验证。样本原生命令/依赖安装、环境版本、修正前失败、版本freeze、JUnit及补充场景全部在[evidence](evidence/README.md)。原始本机路径仍保留，副本映射见[evidence-location.json](evidence-location.json)。`acquire.py`为当次获取记录，不可对原目录再次运行覆盖冻结资料；重取样本应使用新的目录并核对manifest固定head。[原始输入清单](manifest.json) · [全文/实际提供片段核验](input-audit.json)

已完成检查：仓库既有58项离线单元测试、Python编译检查通过（有既存ResourceWarning）；10个pair实际同输入/提示词/模型请求核对通过；93条评估与对应模型case逐项一一相符。现有main的[CI](https://github.com/majiayu000/issue-lens/actions/runs/37049099210)在任务开始时成功，本次交付检查见[PR checks](https://github.com/majiayu000/issue-lens/pull/2/checks)。

## 2026-10-08 交付更新

复用实验提交 `4c6d326`，已推送原独立分支并创建[PR #2](https://github.com/majiayu000/issue-lens/pull/2)。当前认证与权限已经恢复；`environment.json`里的READ记录属于10月7日当次环境，保留为原始证据。10月8日再次用CI相同的Python3.12运行编译检查及58项离线测试，均通过。

本次只更新交付状态，未重跑模型或样本实验，也未修改110通过/1失败、tqdm复现、已有覆盖、费用未知与人类评价缺项。真实维护者评价及部分跨平台原生验证仍待完成；是否合并由维护者审阅本PR决定。
