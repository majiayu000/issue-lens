"""Backtest: can cross-project history help a model propose a test that catches a real, fixed bug?

Protocol and stop conditions: docs/evaluation.md. Stages are resumable; every model result is cached.

  python3 experiments/backtest.py select --out out/backtest-20261022 --n 50
  python3 experiments/backtest.py run    --out out/backtest-20261022 --workers 4
  python3 experiments/backtest.py run    --out out/backtest-20261022 --only-complete   # add arm C
  python3 experiments/backtest.py report --out out/backtest-20261022
"""
import argparse
import base64
import concurrent.futures
import json
import math
import os
from pathlib import Path
import random
import re
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config
from evidence import EvidenceError, fetch_pr_evidence
from gh import GitHub
from llm import ModelError, generate_json

CUTOFF = "2026-04-01"
SEED = 20261022
PER_REPO = 3
# Used to tune the protocol in two pilot rounds; never part of the scored set
PILOT_IDS = {4366252497, 4451203886, 4585203321, 4631014400, 4836398562, 5221070941}
K = 5
FILE_CHARS = 30000
WINDOW_LINES = 80
NON_CODE = re.compile(
    r"(^|/)(tests?|spec|specs|__tests__|testdata|fixtures|docs?|e2e|integration)(/|$)|"
    r"(_test\.go|\.test\.[jt]sx?|\.spec\.[jt]sx?|_test\.py|test_[^/]*\.py|_spec\.rb)$|"
    r"\.(md|rst|txt|json|ya?ml|toml|lock|snap|svg|png|jpg|gif|csv|ini|cfg|css|scss|less|sass|html)$|"
    r"(^|/)(CHANGELOG|changelog)", re.I)

GEN_PROMPT = """你是测试工程师。下面是某个开源项目的一部分源码（某次提交时的版本）和项目简介。
提出恰好 5 条最可能发现真实缺陷的测试。每条要具体到能写成测试：前置条件、触发步骤（输入、时序、故障注入）、
可观察的预期结果。优先考虑边界、状态转换、并发、错误路径和恢复，不要写泛泛的“检查功能正常”。
{history_note}
返回 JSON：{{"tests":[{{"title":"一句话","preconditions":"...","steps":"...","expected":"...",
"source_ids":[引用的历史 issue id，没有则空数组]}}]}}，tests 恰好 5 条。"""
HISTORY_NOTE = """另外给出若干其他项目的历史 issue（history）。只在故障机制确实可能出现在这段代码里时借鉴，
并在 source_ids 写出引用的 id；词面相似但机制不同的不要用。"""
PATTERN_NOTE = """另外给出若干故障模式（patterns），是从其他系统的真实缺陷中整理出的机制和测试思路。
只在模式描述的机制确实可能出现在这段代码里时借鉴，并在 source_ids 写出引用的模式 id（字符串）；不相关的不要用。"""
LESSONS = sorted((ROOT / "out" / "quality-20261021").glob("lessons_*.md"))
ISSUE_URL = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)")
QUERY_PROMPT = """下面是某个开源项目的一部分源码和项目简介。为了从其他项目的历史 bug 中找可借鉴的故障，
提出 6 组英文检索词。每组 1-3 个词，组内是 AND 关系，描述这段代码可能出现的故障机制或场景
（例如 ["lease","expire"]、["retry","duplicate"]），不要用本项目特有的类名或函数名。
返回 JSON：{"queries":[["word","word"]]}。"""
JUDGE_PROMPT = """你是严格的评审。bug 是真实已修复的缺陷，下面给出它的 issue 和修复补丁，以及别人在修复前提出的 5 条测试。
逐条判断：
hit = 按这条测试在修复前的代码上执行，会因为这个 bug 失败（触发条件和可观察结果都对得上）；
mechanism = 指出了同一个故障机制（为什么会错），但步骤或断言不足以稳定触发；只是测同一个函数或区域、机制不同，不算；
miss = 其他。
只依据给出的资料；拿不准时降一级。
返回 JSON：{"judgments":[{"index":0,"verdict":"hit|mechanism|miss","reason":"一句话"}]}，覆盖全部 5 条。"""


def task_dir(out: Path) -> Path:
    return out / "tasks"


def code_file(name: str) -> bool:
    return not NON_CODE.search(name)


def hunk_starts(patch: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(r"^@@ -(\d+)", patch or "", re.M)]


def excerpt_file(text: str, starts: list[int]) -> tuple[str, bool]:
    """Windows around the changed regions: a "review this code" scenario, same for both arms.

    Whole files spread five tests across unrelated functions and both arms scored zero in the pilot.
    """
    lines = text.splitlines()
    if len(lines) <= 2 * WINDOW_LINES:
        return text[:FILE_CHARS], False
    keep = set()
    for start in starts or [1]:
        keep.update(range(max(0, start - WINDOW_LINES), min(len(lines), start + WINDOW_LINES)))
    out, last = [], -2
    for i in sorted(keep):
        if i != last + 1:
            out.append(f"... (line {i + 1})")
        out.append(lines[i])
        last = i
    return "\n".join(out)[:FILE_CHARS], True


def candidates(db: sqlite3.Connection) -> list[dict]:
    db.row_factory = sqlite3.Row
    rows = [dict(r) for r in db.execute(
        """SELECT i.id, i.repo_full_name, i.number, i.form, i.url, i.title, i.body, i.created_at,
                  i.closed_at, q.tier FROM issues i JOIN issue_quality q ON q.issue_id=i.id
           WHERE q.kind='bug' AND i.created_at>=? AND (q.tier='core' OR (q.tier='usable' AND i.comments>=3))
           ORDER BY i.id""", (CUTOFF,))]
    rng = random.Random(SEED)
    rng.shuffle(rows)
    rows.sort(key=lambda r: r["tier"] != "core")  # core first, random within tier
    by_form = {}
    for row in rows:
        by_form.setdefault(row["form"], []).append(row)
    ordered = []   # round-robin across forms so desktop (most rows) does not dominate
    for rank in range(max(map(len, by_form.values()), default=0)):
        ordered.extend(group[rank] for group in by_form.values() if rank < len(group))
    return ordered


def prepare(gh: GitHub, issue: dict) -> dict | None:
    """Return a task, or None with no network side effects beyond reads."""
    try:
        evidence = fetch_pr_evidence(issue, gh)
    except EvidenceError:
        return None
    pulls = [p for p in evidence["pulls"]
             if p["relation"] == "closed_by_pull_request" and p["merged"] and p["merge_commit_sha"]]
    if not pulls or pulls[0]["files_truncated"]:
        return None
    pr = pulls[0]
    owner_repo = issue["repo_full_name"]
    pr_repo = "/".join(pr["url"].split("/")[3:5])
    if pr_repo.lower() != owner_repo.lower():
        return None
    files = [f for f in pr["files"] if code_file(f["filename"]) and f["status"] == "modified"]
    if not 1 <= len(files) <= 6 or any(f["patch_unavailable"] or f["patch_truncated"] for f in pr["files"]):
        return None
    commit = gh.get(f"/repos/{owner_repo}/commits/{pr['merge_commit_sha']}")
    parent = commit["parents"][0]["sha"]
    code = []
    for f in files:
        blob = gh.get(f"/repos/{owner_repo}/contents/{f['filename']}", {"ref": parent})
        if not isinstance(blob, dict) or blob.get("encoding") != "base64":
            return None
        text = base64.b64decode(blob["content"]).decode("utf-8", "replace")
        content, windowed = excerpt_file(text, hunk_starts(f["patch"]))
        code.append({"path": f["filename"], "content": content, "windowed": windowed})
    repo = gh.get(f"/repos/{owner_repo}")
    return {
        "id": issue["id"], "repo": owner_repo, "form": issue["form"], "tier": issue["tier"],
        "created_at": issue["created_at"], "pre_fix_commit": parent,
        "visible": {"project": {"name": owner_repo, "description": repo.get("description"),
                                "language": repo.get("language"), "topics": repo.get("topics")},
                    "code": code},
        "hidden": {"issue_url": issue["url"], "issue_title": issue["title"],
                   "issue_body": (issue["body"] or "")[:6000], "pr_url": pr["url"],
                   "pr_title": pr["title"], "pr_body": pr["body"][:3000],
                   "patch": [{"filename": f["filename"], "patch": f["patch"]} for f in pr["files"]]},
    }


def select(out: Path, n: int) -> None:
    task_dir(out).mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(config.DB_PATH)
    gh = GitHub()
    have = {int(p.stem) for p in task_dir(out).glob("*.json")}
    per_repo = {}
    for p in task_dir(out).glob("*.json"):
        repo = json.loads(p.read_text())["repo"]
        per_repo[repo] = per_repo.get(repo, 0) + 1
    log = out / "select.log"
    for issue in candidates(db):
        if len(have) >= n:
            break
        if (issue["id"] in have or issue["id"] in PILOT_IDS
                or per_repo.get(issue["repo_full_name"], 0) >= PER_REPO):
            continue
        try:
            task = prepare(gh, issue)
        except Exception as error:  # network/API shape; record type only
            task = None
            reason = type(error).__name__
        else:
            reason = "ok" if task else "rejected"
        with log.open("a") as f:
            f.write(f"{issue['url']}\t{reason}\n")
        if task:
            (task_dir(out) / f"{task['id']}.json").write_text(json.dumps(task, ensure_ascii=False, indent=1))
            have.add(task["id"])
            per_repo[task["repo"]] = per_repo.get(task["repo"], 0) + 1
            print(f"[{len(have)}/{n}] {issue['url']}", flush=True)


def retrieve_history(db: sqlite3.Connection, task: dict, queries: list[list[str]], limit: int = 20) -> list[dict]:
    """Only issues created before the bug, from other repositories, in tiers core/usable.

    Same product form first (the Issue Lens design); other forms only fill remaining slots.
    """
    same = _retrieve(db, task, queries, "=")
    other = _retrieve(db, task, queries, "<>") if len(same) < limit else []
    return (same + [h for h in other if h["id"] not in {x["id"] for x in same}])[:limit]


def _retrieve(db: sqlite3.Connection, task: dict, queries: list[list[str]], form_op: str) -> list[dict]:
    found = {}
    for terms in queries[:6]:
        terms = [t for t in terms if isinstance(t, str) and t.strip()][:3]
        if not terms:
            continue
        query = " AND ".join('"' + t.replace('"', '""') + '"' for t in terms)
        rows = db.execute(
            """SELECT i.id, i.repo_full_name, i.title, i.labels,
                      snippet(issues_fts, 1, '', '', ' … ', 48) AS excerpt
               FROM issues_fts JOIN issues i ON i.id=issues_fts.issue_id
               JOIN issue_quality q ON q.issue_id=i.id
               WHERE issues_fts MATCH ? AND i.created_at < ? AND lower(i.repo_full_name) <> lower(?)
                 AND q.tier IN ('core','usable') AND i.form {form_op} ?
               ORDER BY rank LIMIT 5""".replace("{form_op}", form_op),
            (query, task["created_at"], task["repo"], task["form"])).fetchall()
        for iid, repo, title, labels, excerpt in rows:
            found.setdefault(iid, {"id": iid, "repo": repo, "title": title, "labels": labels,
                                   "excerpt": excerpt})
    return list(found.values())


def load_patterns(db: sqlite3.Connection) -> list[dict]:
    """Numbered sections of the curated lessons files, with the issues each one cites."""
    patterns = []
    for path in LESSONS:
        group = path.stem.removeprefix("lessons_distributed_")
        for section in re.split(r"\n(?=## )", path.read_text(encoding="utf-8")):
            heading = re.match(r"## (\d+)\. (.+)", section)
            if not heading:
                continue   # title, decision and unclassified sections
            cited = []
            for repo, number in ISSUE_URL.findall(section):
                row = db.execute("SELECT created_at FROM issues WHERE lower(repo_full_name)=lower(?) AND number=?",
                                 (repo, int(number))).fetchone()
                cited.append({"repo": repo, "number": int(number), "created_at": row[0] if row else None})
            body = section.split("\n", 1)[1].strip()
            patterns.append({"id": f"{group}-{heading.group(1)}", "title": heading.group(2).strip(),
                             "text": body, "cited": cited})
    return patterns


def patterns_for(task: dict, patterns: list[dict]) -> list[dict]:
    """Same leakage rule as history: drop a pattern that cites the same repo at or after the bug,
    and keep it only if at least one cited issue is known to predate the bug."""
    kept = []
    for pattern in patterns:
        cited = pattern["cited"]
        leaks = any(c["repo"].lower() == task["repo"].lower()
                    and (c["created_at"] is None or c["created_at"] >= task["created_at"]) for c in cited)
        earlier = any(c["created_at"] and c["created_at"] < task["created_at"] for c in cited)
        if earlier and not leaks:
            kept.append({"id": pattern["id"], "title": pattern["title"], "text": pattern["text"]})
    return kept


def tests_of(result: dict) -> list[dict]:
    tests = result.get("tests")
    if not isinstance(tests, list) or len(tests) != K or not all(isinstance(t, dict) for t in tests):
        raise ModelError("Expected exactly 5 tests.")
    return tests


def judge(task: dict, tests: list[dict]) -> tuple[dict, dict]:
    shown = [{"index": i, **{k: t.get(k) for k in ("title", "preconditions", "steps", "expected")}}
             for i, t in enumerate(tests)]
    result, prov = generate_json(JUDGE_PROMPT, {"bug": task["hidden"], "tests": shown})
    judgments = result.get("judgments")
    if (not isinstance(judgments, list) or sorted(j.get("index") for j in judgments) != list(range(K))
            or any(j.get("verdict") not in ("hit", "mechanism", "miss") for j in judgments)):
        raise ModelError("Invalid judgments.")
    return result, prov


def run_task(path: Path, out: Path) -> str:
    task = json.loads(path.read_text())
    target = out / "runs" / path.name
    record = json.loads(target.read_text()) if target.exists() else {"id": task["id"]}
    timing = record.setdefault("seconds", {})
    def step(name, fn):
        if name not in record:
            start = time.time()
            record[name] = fn()
            timing[name] = round(time.time() - start, 1)
            target.write_text(json.dumps(record, ensure_ascii=False, indent=1))
        return record[name]
    try:
        a = step("a", lambda: dict(zip(("result", "provenance"), generate_json(
            GEN_PROMPT.format(history_note=""), task["visible"]))))
        tests_of(a["result"])
        q = step("queries", lambda: dict(zip(("result", "provenance"), generate_json(
            QUERY_PROMPT, task["visible"]))))
        def history():
            db = sqlite3.connect(config.DB_PATH)
            try:
                queries = q["result"].get("queries") or []
                return retrieve_history(db, task, queries if isinstance(queries, list) else [])
            finally:
                db.close()
        hist = step("history", history)
        b = step("b", lambda: dict(zip(("result", "provenance"), generate_json(
            GEN_PROMPT.format(history_note=HISTORY_NOTE), {**task["visible"], "history": hist}))))
        tests_of(b["result"])
        def patterns():
            db = sqlite3.connect(config.DB_PATH)
            try:
                return patterns_for(task, load_patterns(db))
            finally:
                db.close()
        pats = step("patterns", patterns)
        c = step("c", lambda: dict(zip(("result", "provenance"), generate_json(
            GEN_PROMPT.format(history_note=PATTERN_NOTE), {**task["visible"], "patterns": pats}))))
        tests_of(c["result"])
        for arm in ("a", "b", "c"):
            step(f"judge_{arm}", lambda arm=arm: dict(zip(("result", "provenance"), judge(
                task, tests_of(record[arm]["result"])))))
    except ModelError as error:
        record.setdefault("errors", []).append(str(error))
        target.write_text(json.dumps(record, ensure_ascii=False, indent=1))
        return f"{task['id']} error: {error}"
    return f"{task['id']} done"


def run(out: Path, workers: int, only_complete: bool = False) -> None:
    if os.environ.get("ISSUE_LENS_LLM_ENGINE") != "codex" or not os.environ.get("ISSUE_LENS_MODEL"):
        sys.exit("Set ISSUE_LENS_LLM_ENGINE=codex and an explicit ISSUE_LENS_MODEL")
    (out / "runs").mkdir(parents=True, exist_ok=True)
    paths = sorted(task_dir(out).glob("*.json"))
    if only_complete:   # add an arm to the already-scored set without changing it
        paths = [p for p in paths if "judge_b" in json.loads((out / "runs" / p.name).read_text())]
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for message in pool.map(lambda p: run_task(p, out), paths):
            print(message, flush=True)


def verdict(judge_record: dict) -> str:
    verdicts = {j["verdict"] for j in judge_record["result"]["judgments"]}
    return "hit" if "hit" in verdicts else "mechanism" if "mechanism" in verdicts else "miss"


def mcnemar_p(b_only: int, a_only: int) -> float:
    """Exact two-sided McNemar (binomial on discordant pairs)."""
    n = b_only + a_only
    if n == 0:
        return 1.0
    k = min(b_only, a_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def bootstrap_ci(pairs: list[tuple[int, int]], rounds: int = 10000, seed: int = SEED) -> tuple[float, float]:
    rng = random.Random(seed)
    diffs = []
    for _ in range(rounds):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        diffs.append(sum(b - a for a, b in sample) / len(sample))
    diffs.sort()
    return diffs[int(0.025 * rounds)], diffs[int(0.975 * rounds) - 1]


def compare(rows: list[dict], base: str, arm: str) -> dict:
    """Paired comparison on the primary metric (hit or same failure mechanism)."""
    pairs = [(int(x[base] != "miss"), int(x[arm] != "miss")) for x in rows]
    if not pairs:
        return {"n": 0}
    only_arm = sum(1 for a, b in pairs if b and not a)
    only_base = sum(1 for a, b in pairs if a and not b)
    low, high = bootstrap_ci(pairs)
    return {"n": len(pairs), base: sum(a for a, _ in pairs), arm: sum(b for _, b in pairs),
            "lift_pp": round(100 * sum(b - a for a, b in pairs) / len(pairs), 1),
            "ci95_pp": [round(100 * low, 1), round(100 * high, 1)],
            f"{arm}_only": only_arm, f"{base}_only": only_base,
            "mcnemar_p": round(mcnemar_p(only_arm, only_base), 4)}


def report(out: Path) -> dict:
    rows = []
    for path in sorted((out / "runs").glob("*.json")):
        r = json.loads(path.read_text())
        if "judge_a" not in r or "judge_b" not in r:
            continue
        task = json.loads((task_dir(out) / path.name).read_text())
        b_tests = r["b"]["result"]["tests"]
        b_hit_cites = [bool(b_tests[j["index"]].get("source_ids"))
                       for j in r["judge_b"]["result"]["judgments"] if j["verdict"] != "miss"]
        usage = lambda key: (r[key]["provenance"].get("usage") or {}).get("input_tokens", 0)
        rows.append({"id": r["id"], "repo": task["repo"], "form": task["form"], "url": task["hidden"]["issue_url"],
                     "a": verdict(r["judge_a"]), "b": verdict(r["judge_b"]),
                     "history_count": len(r["history"]), "b_hit_cites_history": any(b_hit_cites),
                     "a_input_tokens": usage("a"),
                     "b_input_tokens": usage("queries") + usage("b"),
                     "a_seconds": r["seconds"].get("a"), "b_seconds": (r["seconds"].get("queries") or 0) + (r["seconds"].get("b") or 0)})
        if "judge_c" in r:
            c_tests = r["c"]["result"]["tests"]
            rows[-1].update({
                "c": verdict(r["judge_c"]), "pattern_count": len(r["patterns"]),
                "c_tests_citing": sum(bool(t.get("source_ids")) for t in c_tests),
                "c_hit_cites_pattern": any(bool(c_tests[j["index"]].get("source_ids"))
                                           for j in r["judge_c"]["result"]["judgments"] if j["verdict"] != "miss"),
                "c_input_tokens": usage("c"), "c_seconds": r["seconds"].get("c")})
    n = len(rows)
    if not n:
        return {"n": 0}
    # Primary (fixed after the pilot, see docs/evaluation.md): hit or same failure mechanism
    pairs = [(int(x["a"] != "miss"), int(x["b"] != "miss")) for x in rows]
    a_hit, b_hit = sum(a for a, _ in pairs), sum(b for _, b in pairs)
    b_only = sum(1 for a, b in pairs if b and not a)
    a_only = sum(1 for a, b in pairs if a and not b)
    low, high = bootstrap_ci(pairs)
    summary = {
        "n": n, "primary": "hit_or_mechanism", "a_primary": a_hit, "b_primary": b_hit,
        "a_strict_hit": sum(x["a"] == "hit" for x in rows),
        "b_strict_hit": sum(x["b"] == "hit" for x in rows),
        "lift_pp": round(100 * (b_hit - a_hit) / n, 1), "ci95_pp": [round(100 * low, 1), round(100 * high, 1)],
        "b_only": b_only, "a_only": a_only, "mcnemar_p": round(mcnemar_p(b_only, a_only), 4),
        "b_only_citing_history": sum(1 for x in rows if x["b"] != "miss" and x["a"] == "miss" and x["b_hit_cites_history"]),
        "tasks_with_no_history": sum(1 for x in rows if not x["history_count"]),
        "input_tokens": {"a": sum(x["a_input_tokens"] for x in rows), "b": sum(x["b_input_tokens"] for x in rows)},
        "rows": rows,
    }
    with_c = [x for x in rows if "c" in x]
    if with_c:
        summary["c"] = {
            "vs_a": compare(with_c, "a", "c"), "vs_b": compare(with_c, "b", "c"),
            "distributed_vs_a": compare([x for x in with_c if x["form"] == "distributed"], "a", "c"),
            "c_strict_hit": sum(x["c"] == "hit" for x in with_c),
            "c_only_citing_pattern": sum(1 for x in with_c if x["c"] != "miss" and x["a"] == "miss"
                                         and x["c_hit_cites_pattern"]),
            "tests_citing_pattern": [sum(x["c_tests_citing"] for x in with_c), K * len(with_c)],
            "tasks_with_no_pattern": sum(1 for x in with_c if not x["pattern_count"]),
            "input_tokens": sum(x["c_input_tokens"] for x in with_c)}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False, indent=1))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["select", "run", "report"])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only-complete", action="store_true", help="run: only tasks already scored for A/B")
    args = ap.parse_args()
    if args.stage == "select":
        select(args.out, args.n)
    elif args.stage == "run":
        run(args.out, args.workers, args.only_complete)
    else:
        report(args.out)


if __name__ == "__main__":
    main()
