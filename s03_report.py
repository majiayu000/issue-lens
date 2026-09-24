"""第三步:生成阶段 0 价值验证报告——按形态汇总语料统计 + reaction 最高的 issue 清单。

产物:out/report_{form}.md。用途:人工通读,判断"同类产品的真实 issue 是否给了你测试角度"。

用法:
  python3 s03_report.py                # 全部形态
  python3 s03_report.py --forms cli --top 50
"""
import argparse
import os
import re
import sqlite3
from collections import Counter

import config

WS = re.compile(r"\s+")


def excerpt(body: str, n: int = 220) -> str:
    text = WS.sub(" ", (body or "").strip())
    return text[:n] + ("…" if len(text) > n else "")


def md_escape(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def report_form(db: sqlite3.Connection, form: str, top: int) -> str:
    cfg = config.FORMS[form]
    name = cfg["name"]

    repo_count, fetched, trunc = db.execute(
        """SELECT COUNT(*),
                  COALESCE(SUM(issues_fetched), 0),
                  COALESCE(SUM(truncated), 0)
           FROM repos WHERE form=?""", (form,)).fetchone()
    issue_count = db.execute("SELECT COUNT(*) FROM issues WHERE form=?", (form,)).fetchone()[0]

    label_counter: Counter = Counter()
    for (labels,) in db.execute(
            "SELECT labels FROM issues WHERE form=? AND labels != ''", (form,)):
        for lb in labels.split(","):
            lb = lb.strip()
            if lb and lb.lower() not in ("bug",):
                label_counter[lb] += 1

    top_labels = "\n".join(
        f"| {md_escape(lb)} | {n} |" for lb, n in label_counter.most_common(15))

    rows = []
    for (title, repo, reactions, labels, url, body) in db.execute(
            """SELECT title, repo_full_name, reactions, labels, url, body
               FROM issues WHERE form=?
               ORDER BY reactions DESC LIMIT ?""", (form, top)):
        rows.append(
            f"| {reactions} | [{md_escape(title)}]({url}) "
            f"| {repo} | {md_escape(labels)[:60]} | {md_escape(excerpt(body))} |")

    return f"""# {name}——真实 issue 测试灵感报告(阶段 0 价值验证材料)

## 语料概况

- 仓库:{repo_count} 个(已抓 {fetched} 条高质量 issue;{trunc} 个仓库因超量截断,只保留 reaction 最高的部分)
- issue 语料:{issue_count} 条
- 筛选口径:`is:closed` + `linked:pr`(与修复 PR 关联)+ `reason:completed`(维护者确认为已解决的真实问题)
- 用法:通读下表,自问"这些问题我的产品会不会有?"——回答不上来的行,就是你缺的测试角度。

## 高频标签(除 bug 外)

| 标签 | 出现次数 |
|---|---|
{top_labels}

## Reaction 最高的 {len(rows)} 个问题

> reaction 数 = 该问题被多少用户点 👍,即"多少人曾经踩到"。

| 👍 | 标题(链接) | 仓库 | 标签 | 摘录 |
|---|---|---|---|---|
{chr(10).join(rows)}

## 初始分类法(待用数据修正)

{chr(10).join(f"- {c}" for c in cfg['taxonomy'])}
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--forms", nargs="+", default=list(config.FORMS), choices=list(config.FORMS))
    ap.add_argument("--top", type=int, default=50)
    args = ap.parse_args()

    os.makedirs(config.OUT_DIR, exist_ok=True)
    db = sqlite3.connect(config.DB_PATH)
    try:
        for form in args.forms:
            text = report_form(db, form, args.top)
            path = config.report_path(form)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[{form}] 报告 -> {path}({len(text)} 字符)", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
