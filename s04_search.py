"""第四步:检索语料——按关键词(FTS)或纯热度查 issue,输出 markdown 到 stdout。

用法:
  python3 s04_search.py --form desktop --q "crash startup"
  python3 s04_search.py --form cli --q "encoding utf-8" --sort relevance
  python3 s04_search.py --form all --top 30
"""
import argparse
import sqlite3

import config
from s03_report import excerpt, md_escape


def search(db: sqlite3.Connection, forms: list[str], terms: list[str], top: bool,
           sort: str, limit: int, min_reactions: int) -> list:
    if top or not terms:
        sql = """SELECT i.reactions, i.title, i.url, i.repo_full_name, i.labels, i.body
                 FROM issues i WHERE i.form IN ({})
                 AND i.reactions >= ? ORDER BY i.reactions DESC LIMIT ?""".format(
            ",".join("?" * len(forms)))
        return db.execute(sql, (*forms, min_reactions, limit)).fetchall()

    fts_q = " OR ".join(f'"{t.replace(chr(34), "")}"' for t in terms if t)
    inner_order = "ORDER BY rank" if sort == "relevance" else "ORDER BY i.reactions DESC"
    sql = f"""SELECT i.reactions, i.title, i.url, i.repo_full_name, i.labels, i.body
              FROM issues_fts f JOIN issues i ON i.id = f.issue_id
              WHERE issues_fts MATCH ?
                AND i.form IN ({",".join("?" * len(forms))})
                AND i.reactions >= ?
              {inner_order} LIMIT ?"""
    return db.execute(sql, (fts_q, *forms, min_reactions, limit)).fetchall()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--form", default="all",
                    help="desktop / cli / all(默认 all)")
    ap.add_argument("--q", default="", help="关键词,空格分隔多个词(OR 语义)")
    ap.add_argument("--top", nargs="?", const=20, type=int, default=None,
                    help="忽略关键词按 reaction 排,可带数量(如 --top 30,默认 20)")
    ap.add_argument("--sort", choices=["reactions", "relevance"], default="reactions")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--min-reactions", type=int, default=0)
    args = ap.parse_args()

    forms = list(config.FORMS) if args.form == "all" else [args.form]
    for f in forms:
        if f not in config.FORMS:
            ap.error(f"未知形态:{f}(可选:{', '.join(config.FORMS)} / all)")

    top_mode = args.top is not None
    if top_mode:
        args.limit = args.top

    db = sqlite3.connect(config.DB_PATH)
    try:
        rows = search(db, forms, args.q.split(), top_mode, args.sort,
                      args.limit, args.min_reactions)
    finally:
        db.close()

    if not rows:
        print("(无匹配结果)")
        return
    print(f"| 👍 | 标题 | 仓库 | 标签 | 摘录 |")
    print(f"|---|---|---|---|---|")
    for reactions, title, url, repo, labels, body in rows:
        print(f"| {reactions} | [{md_escape(title)}]({url}) | {repo} "
              f"| {md_escape(labels)[:50]} | {md_escape(excerpt(body, 160))} |")


if __name__ == "__main__":
    main()
