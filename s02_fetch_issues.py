"""第二步:逐仓库抓取高质量已关闭 issue(closed + linked:pr + reason:completed)入 SQLite。

按 reaction 数降序取前 N 条;Search API 单查询硬顶 1000 条,超出即截断并在 repos 表记录
truncated=1(不静默丢弃)。已抓过的仓库默认跳过(--refresh 重抓)。

用法:
  python3 s02_fetch_issues.py                          # 全部形态
  python3 s02_fetch_issues.py --forms cli --limit-repos 2 --max-issues 100   # 冒烟
"""
import argparse
import datetime
import json
import os
import re
import sqlite3

import config
from gh import GitHub

SCHEMA_PATH = os.path.join(config.BASE, "schema.sql")


def init_db(db: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        db.executescript(f.read())


def fetch_form(gh: GitHub, db: sqlite3.Connection, form: str,
               limit_repos: int | None, max_issues: int | None, refresh: bool,
               repos: list[dict] | None = None) -> None:
    if repos is None:
        with open(config.repos_path(form), encoding="utf-8") as f:
            repos = json.load(f)
    if limit_repos:
        repos = repos[:limit_repos]
    cap = max_issues or config.MAX_ISSUES

    # 跨形态去重:同一仓库只需抓一次(edex-ui 这类 Electron 终端会同时命中两个清单)
    done = {row[0] for row in db.execute(
        "SELECT full_name FROM repos WHERE fetched_at IS NOT NULL")}

    for i, r in enumerate(repos, 1):
        name = r["full_name"]
        if not refresh and name in done:
            print(f"[{form}] {i}/{len(repos)} {name}: 已抓过,跳过(--refresh 重抓)", flush=True)
            continue
        query = f"repo:{name} {config.ISSUE_QUERY}"
        items, total = gh.search_issues(query, max_results=cap)
        truncated = 1 if total > len(items) else 0
        for it in items:
            # 先查再插:FTS5 虚拟表不支持 OR IGNORE 去重,重复抓取会让 issues_fts 出现重复行
            if db.execute("SELECT 1 FROM issues WHERE id=?", (it["id"],)).fetchone():
                continue
            db.execute(
                """INSERT INTO issues
                   (id, repo_full_name, number, form, title, body, reactions, comments,
                    labels, author, created_at, closed_at, url)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    it["id"], name, it["number"], form,
                    it.get("title") or "", it.get("body") or "",
                    it.get("reactions", {}).get("total_count", 0),
                    it.get("comments", 0),
                    ",".join(l.get("name", "") for l in it.get("labels", [])),
                    (it.get("user") or {}).get("login"),
                    it.get("created_at"), it.get("closed_at"), it.get("html_url"),
                ))
            db.execute(
                "INSERT OR IGNORE INTO issues_fts (title, body, issue_id) VALUES (?,?,?)",
                (it.get("title") or "", it.get("body") or "", it["id"]))
        db.execute(
            """INSERT INTO repos
               (full_name, form, stars, language, description, topics,
                issues_total, issues_fetched, truncated, fetched_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(full_name) DO UPDATE SET
                 stars=excluded.stars, language=excluded.language,
                 description=excluded.description, topics=excluded.topics,
                 issues_total=excluded.issues_total, issues_fetched=excluded.issues_fetched,
                 truncated=excluded.truncated, fetched_at=excluded.fetched_at""",
            (
                name, form, r["stars"], r["language"], r["description"],
                json.dumps(r.get("topics", []), ensure_ascii=False),
                total, len(items), truncated,
                datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            ))
        db.commit()
        note = f",截断(共 {total},仅取 reaction 最高的 {len(items)})" if truncated else ""
        print(f"[{form}] {i}/{len(repos)} {name}: 入库 {len(items)} 条{note}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--forms", nargs="+", default=list(config.FORMS), choices=list(config.FORMS))
    ap.add_argument("--limit-repos", type=int, default=None)
    ap.add_argument("--max-issues", type=int, default=None)
    ap.add_argument("--refresh", action="store_true", help="重抓已完成的仓库")
    ap.add_argument("--repos", nargs="+", help="显式补充 owner/repo；须指定一种 --forms")
    args = ap.parse_args()
    if args.repos and (len(args.forms) != 1 or any(
            not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", name)
            or name.split("/")[1] in (".", "..") for name in args.repos)):
        ap.error("--repos requires valid owner/repo names and exactly one --forms value")
    if args.max_issues is not None and not 1 <= args.max_issues <= 1000:
        ap.error("--max-issues must be between 1 and 1000")

    os.makedirs(config.DATA_DIR, exist_ok=True)
    db = sqlite3.connect(config.DB_PATH)
    try:
        init_db(db)
        gh = GitHub()
        for form in args.forms:
            selected = None
            if args.repos:
                selected = []
                for name in dict.fromkeys(args.repos):
                    repo = gh.get(f"/repos/{name}")
                    selected.append({"full_name": repo["full_name"], "stars": repo["stargazers_count"],
                                     "language": repo["language"], "description": repo["description"],
                                     "topics": repo["topics"]})
            fetch_form(gh, db, form, args.limit_repos, args.max_issues, args.refresh, selected)
            if selected:
                with open(config.repos_path(form), encoding="utf-8") as f:
                    saved = {repo["full_name"]: repo for repo in json.load(f)}
                saved.update((repo["full_name"], repo) for repo in selected)
                with open(config.repos_path(form), "w", encoding="utf-8") as f:
                    json.dump(list(saved.values()), f, ensure_ascii=False, indent=2)
                    f.write("\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
