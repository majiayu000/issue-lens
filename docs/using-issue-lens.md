# 把历史 issue 用到自己的开发流程

issue-lens 提供三种入口：原文检索、按任务分类归并、结合产品文档和代码改动生成测试草稿。实际执行由目标项目的测试工具完成。

## 修改代码后：只看这次改动

给 Codex 的任务可以这样写：

> 根据这次 diff 和当前产品文档，从 issue-lens 找相关历史问题，对照我指定的测试文件，提出 3–5 个值得执行的场景。给出来源、适用条件和现有覆盖证据，不把建议当成已确认缺陷。

先在目标项目中导出明确的改动范围，再在 issue-lens 中运行：

```bash
# 在目标项目根目录：按需要选择已提交的区间；未提交改动可用 git diff HEAD。
git diff HEAD~1 HEAD -- src > /tmp/product-change.diff

# 在 issue-lens 根目录：把产品和测试文件路径换成实际路径。
export ISSUE_LENS_LLM_ENGINE=codex
python3 s05_plan.py --form cli --prd /path/to/product/README.md \
  --diff /tmp/product-change.diff --tests /path/to/product/tests/test_paths.py \
  --with-pr-evidence --limit 6 --out out/change-review.md
```

`--diff` 会同时限制需求检索和方案生成。它不读取整个工作区，也不把代码变化自动当成产品要求；文档中没有说明的行为会列为待确认事项。报告记录 diff 哈希。模型使用本机 Codex 可用的默认值，也可以显式设置 `ISSUE_LENS_MODEL`；不支持的模型会使命令失败，不自动换模型。

## 开发前或遇到故障时：按任务整理案例

```bash
python3 s06_curate.py --form cli --q "restore" \
  --repo restic/restic --repo rclone/rclone --limit 6 \
  --with-pr-evidence --out out/restore-review.md

python3 s06_curate.py --form desktop --q "update" \
  --repo electron-userland/electron-builder --limit 6 \
  --with-pr-evidence --out out/updater-review.md
```

这里的多个查询词按 AND 匹配，`--repo` 是可重复的精确来源筛选。每条选中记录会分为 bug、feature、question 或 unclear，然后由模型按相同触发机制和可测试边界归组。不相关记录单独列出理由；所有原始记录都保留，不会从数据库删除。

输出同时列出本次分析数量、全库数量和已有提炼缓存数量。**没有提炼的记录就是未分析，不能拿抓取量当分析量。** 分组是测试场景整理，不代表原维护者认定 issue 重复；引文存在也不保证模型推理正确。

启用 `--with-pr-evidence` 后，优先读取 GitHub 当前关闭事件中的 PR，再取显式关联的关闭候选，最多 3 个；不再使用任意时间线交叉引用。每个 PR 仍限首 100 个文件、6,000 字符正文和 12,000 字符补丁。再读取最近 8 条 issue 评论，每条最多 1,000 字符。完整数量、截断情况和读取时间记录在 JSON；没有证据时不声称没有修复。

GitHub 的关闭关系证明关联，不证明根因，也不证明补丁适用于你的产品。即使上游用例能复现，对目标项目也要重新构造夹具并执行。

## 按实际功能补充来源

```bash
python3 s02_fetch_issues.py --forms cli \
  --repos restic/restic rclone/rclone --max-issues 100
python3 s02_fetch_issues.py --forms desktop \
  --repos electron-userland/electron-builder --max-issues 100
```

显式来源不依赖 topic 热度筛选，仍使用已完成、有关联 PR 的 issue 查询。每个来源记录实际抓取量和截断状态，仓库名单会写回 `data/repos_*.json`。已经抓取的仓库默认跳过；重新运行 `s01_pick_repos.py` 会重新生成 topic 名单，因此需要保留显式来源命令。

本次补充 restic 的恢复案例、rclone 的文件操作案例，以及 electron-builder 的安装和更新案例，每个来源先取 100 条。它们与功能相关，但不表示其中每条都适用于 rclean 或你的桌面应用。

## 发布前：运行已采纳的测试

[本次 rclean 实测](../out/expansion-20261003/README.md)展示了从历史建议到执行结果的完整记录。可对自己构建的 rclean 重跑：

```bash
python3 experiments/rclean_acceptance.py \
  --binary /absolute/path/to/rclean --out /tmp/rclean-acceptance.json
```

脚本在临时目录内创建测试文件，并隔离 HOME、配置、缓存和 graveyard。它实际执行受控恢复操作，不扫描工作目录或用户文件。当前脚本支持 macOS/Linux；传入的二进制必须可信。

每次验收分别记录：不适用、已有覆盖、补充边界、执行通过、实际缺陷。一个场景通过，说明当前夹具没有触发错误；不能据此证明产品没有其他问题。
