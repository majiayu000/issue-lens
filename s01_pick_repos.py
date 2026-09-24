"""第一步:按形态的 topics 圈定头部仓库,写入 data/repos_{form}.json。

用法:
  python3 s01_pick_repos.py                    # 全部形态,每形态取 config.MAX_REPOS 个
  python3 s01_pick_repos.py --forms cli desktop --limit 40
"""
import argparse
import json
import os

import config
from gh import GitHub


def pick(gh: GitHub, form: str, limit: int) -> list[dict]:
    cfg = config.FORMS[form]
    seen: dict[str, dict] = {}
    for topic in cfg["topics"]:
        q = f"topic:{topic} stars:>={cfg['min_stars']}"
        items, total = gh.search_repositories(q)
        print(f"[{form}] {q} -> 命中 {total} 个仓库,本页取 {len(items)}", flush=True)
        for it in items:
            name = it["full_name"]
            if name not in seen:
                seen[name] = {
                    "full_name": name,
                    "stars": it["stargazers_count"],
                    "language": it.get("language"),
                    "description": it.get("description") or "",
                    "topics": it.get("topics") or [],
                    "matched_topics": set(),
                }
            seen[name]["matched_topics"].add(topic)
    ranked = sorted(seen.values(), key=lambda r: -r["stars"])[:limit]
    for r in ranked:
        r["matched_topics"] = sorted(r["matched_topics"])
    return ranked


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--forms", nargs="+", default=list(config.FORMS), choices=list(config.FORMS))
    ap.add_argument("--limit", type=int, default=config.MAX_REPOS)
    args = ap.parse_args()

    os.makedirs(config.DATA_DIR, exist_ok=True)
    gh = GitHub()
    for form in args.forms:
        repos = pick(gh, form, args.limit)
        path = config.repos_path(form)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(repos, f, ensure_ascii=False, indent=2)
        print(f"[{form}] 已选出 {len(repos)} 个仓库 -> {path}", flush=True)
        for r in repos[:10]:
            print(f"    {r['stars']:>7}  {r['full_name']:<40} {r['description'][:60]}", flush=True)


if __name__ == "__main__":
    main()
