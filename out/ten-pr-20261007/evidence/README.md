# 当次原始执行证据副本

原始根目录 `/Users/apple/.codex/task-evidence/issue-lens-20261007` 保留，未删除。相对日志路径 `native-logs/`、`logs/` 对应本目录；原绝对 `model-checks/` 路径也有同名副本。原JSON命令不改写，保留当时真实运行路径。

- `native-logs/`：前五环境安装、native及补充检查日志/JUnit。
- `logs/`：后五原生、补充检查、依赖失败、Python3.14追加验证与tqdm最小复现/对照。
- `model-checks/`：全部隔离执行脚本，含tqdm失败最小复现。
- native/assess/run_model脚本是该次执行与技术判断的记录，不是新评测平台；其中判断对应冻结样本，不可泛化到新模型输出。
- `acquire.py`及`run_pairs.py`记录当次采集和有界并发入口；不得对已存在的原始目录重跑覆盖。推荐复跑入口是仓库的`experiments/ten_pr_comparison.py`，指定新的输出目录。
- `retry_exact.py`保留有效旧arm，只对缺失arm同输入重跑，输出目录必须为新目录。

tqdm新增检查的exit1与两次默认API失败复现是故障证据，不能改写为成功；成功对照和隔离重核单独保留。
