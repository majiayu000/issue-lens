"""第七步:给语料分层(core / usable / low / excluded),原始记录不删除。

规则只看已入库字段(标签、标题、正文长度、👍、评论、作者),结果写入 issue_quality 表,
每次全量重算。分层是检索过滤用的启发式,不等于人工确认 bug 或根因。

  core      bug(标签或 bug 模板),👍>=10 或评论>=10,正文>=200 字符,不是依赖/构建/风格类
  usable    bug 或类型未知,👍>=1 或评论>=3;或 bug 且写了复现步骤
  low       bug 或类型未知,但没有热度和讨论信号;或 CI 自动开的测试失败单
  excluded  功能请求 / 提问 / 任务 / 机器人 / 重复标题 / 无讨论的个人清单 / 过短

用法:
  python3 s07_quality.py                 # 重算并打印各形态分层统计
  python3 s07_quality.py --json out/quality.json
"""
import argparse
import json
import re
import sqlite3
from collections import Counter

import config
from s02_fetch_issues import init_db

TIERS = ["core", "usable", "low", "excluded"]

# 标签按 / : 空格等切成词再匹配,避免 "debug" 命中 "bug"
KIND_LABELS = [
    ("bug", {"bug", "defect", "regression", "crash", "c-bug"}),
    ("feature", {"feature", "enhancement", "request", "proposal", "rfc", "idea", "improvement"}),
    ("question", {"question", "support", "discussion", "help"}),
    ("task", {"task", "chore", "refactor", "docs", "documentation", "flake", "test", "ci", "cleanup"}),
]
KIND_TITLES = [
    ("bug", re.compile(r"^\s*(\[bug\]|bug\s*[:：]|\[regression\]|regression\s*[:：])", re.I)),
    ("feature", re.compile(r"^\s*(\[(feature|fr|feat|enhancement)[^\]]*\]|feat(ure)?\s*(request)?\s*[(:：]|fr\s*[:：]|rfc\b)", re.I)),
    ("question", re.compile(r"^\s*(\[question\]|question\s*[:：]|how (to|do|can)\b)", re.I)),
]
# 正文模板:无标签时判类型;bug 模板可推翻 docs/task/question 标签;复现步骤算具体触发条件
FEATURE_BODY = re.compile(r"(^|\n)\s*#*\s*(feature request|is your feature request|describe the (feature|solution you'?d like))", re.I)
BUG_BODY = re.compile(r"(^|\n)\s*#*\s*(bug report|describe the bug|steps to reproduce|expected behaviou?r|actual behaviou?r)", re.I)
REPRO_BODY = re.compile(r"(steps to reproduce|to reproduce|reproduc(e|tion) steps|minimal repro)", re.I)
# CI 自动开的测试失败单(如 cockroach-teamcity 的 roachtest):抽样 3 条里 2 条是测试自身问题,
# 1 条是真实 raft 缺陷(cockroach#104709),所以只降到 low,不排除
TEST_FAILURE = {"test-failure", "roachtest", "flaky-test", "flake", "o-roachtest", "c-test-failure"}
# 带 bug 标签也不进 core:依赖、构建、代码风格类
NON_PRODUCT = {"dependencies", "deps", "dependency", "build", "style", "lint", "code-quality", "packaging"}
SOLO_SHARE = 0.2   # 同一作者占该仓库入库量的比例
CORE_SIGNAL = 10


def label_words(labels: str) -> set[str]:
    words = set()
    for label in (labels or "").lower().split(","):
        label = label.strip()
        words.add(label)
        words.update(w for w in re.split(r"[\s/:_\-.]+", label) if w)
    return words


def classify_kind(labels: str, title: str, body: str = "") -> str:
    words = label_words(labels)
    for kind, names in KIND_LABELS:
        if words & names:
            if kind in ("question", "task") and BUG_BODY.search(body or ""):
                return "bug"
            return kind
    for kind, pattern in KIND_TITLES:
        if pattern.search(title or ""):
            return kind
    if FEATURE_BODY.search(body or ""):
        return "feature"
    if BUG_BODY.search(body or ""):
        return "bug"
    return "unknown"


def grade(issue: dict, author_share: float, duplicate: bool) -> tuple[str, str, list[str]]:
    """返回 (kind, tier, reasons)。issue 需含 labels/title/body/reactions/comments/author。"""
    kind = classify_kind(issue["labels"], issue["title"], issue["body"])
    reactions, comments = issue["reactions"] or 0, issue["comments"] or 0
    body_len = len(issue["body"] or "")
    author = (issue["author"] or "").lower()
    reasons = []
    if kind in ("feature", "question", "task"):
        reasons.append(kind)
    if author.endswith("[bot]") or author.endswith("-bot"):
        reasons.append("bot")
    if duplicate:
        reasons.append("duplicate_title")
    if reactions == 0 and comments <= 1 and author_share >= SOLO_SHARE:
        reasons.append("solo_no_discussion")
    if body_len < 100 and kind != "bug":
        reasons.append("short_body")
    if reasons:
        return kind, "excluded", reasons
    if label_words(issue["labels"]) & TEST_FAILURE:
        return kind, "low", []
    if (kind == "bug" and max(reactions, comments) >= CORE_SIGNAL and body_len >= 200
            and not label_words(issue["labels"]) & NON_PRODUCT):
        return kind, "core", []
    if reactions >= 1 or comments >= 3 or (kind == "bug" and REPRO_BODY.search(issue["body"] or "")):
        return kind, "usable", []
    return kind, "low", []


def rebuild(db: sqlite3.Connection) -> None:
    db.row_factory = sqlite3.Row
    rows = db.execute("""SELECT id, repo_full_name, title, body, labels, reactions, comments,
                                author, created_at FROM issues ORDER BY created_at, id""").fetchall()
    per_repo = Counter(r["repo_full_name"] for r in rows)
    per_author = Counter((r["repo_full_name"], r["author"]) for r in rows)
    seen_titles = set()
    out = []
    for r in rows:
        key = (r["repo_full_name"], (r["title"] or "").strip().lower())
        duplicate = key in seen_titles   # 按创建时间保留最早一条
        seen_titles.add(key)
        share = per_author[(r["repo_full_name"], r["author"])] / per_repo[r["repo_full_name"]]
        kind, tier, reasons = grade(dict(r), share, duplicate)
        out.append((r["id"], kind, tier, ",".join(reasons)))
    db.execute("DELETE FROM issue_quality")
    db.executemany("INSERT INTO issue_quality (issue_id, kind, tier, reasons) VALUES (?,?,?,?)", out)
    db.commit()


def summary(db: sqlite3.Connection) -> dict:
    by_form = {}
    for form, tier, n in db.execute("""SELECT i.form, q.tier, COUNT(*) FROM issues i
                                       JOIN issue_quality q ON q.issue_id = i.id GROUP BY 1, 2"""):
        by_form.setdefault(form, dict.fromkeys(TIERS, 0))[tier] = n
    reasons = Counter()
    for (value,) in db.execute("SELECT reasons FROM issue_quality WHERE reasons <> ''"):
        reasons.update(value.split(","))
    return {"by_form": by_form, "excluded_reasons": dict(reasons.most_common())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", help="另存统计 JSON")
    args = ap.parse_args()
    db = sqlite3.connect(config.DB_PATH)
    try:
        init_db(db)
        rebuild(db)
        result = summary(db)
    finally:
        db.close()
    print(f"| 形态 | {' | '.join(TIERS)} |")
    print("|---|" + "---:|" * len(TIERS))
    for form, counts in sorted(result["by_form"].items()):
        print(f"| {form} | " + " | ".join(str(counts[t]) for t in TIERS) + " |")
    print("\n排除原因(可重叠):", ", ".join(f"{k} {v}" for k, v in result["excluded_reasons"].items()))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
