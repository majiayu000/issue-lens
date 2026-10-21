"""Export fixed random samples for manual review; seed recorded so the sample can be redrawn."""
import json
from pathlib import Path
import random
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config

HERE = Path(__file__).parent
SEED = 20261021
GROUPS = {
    "consensus": ["etcd-io/etcd", "hashicorp/consul", "hashicorp/nomad", "hashicorp/raft",
                  "databendlabs/openraft", "nats-io/nats-server"],
    "databases": ["cockroachdb/cockroach", "tikv/tikv", "pingcap/tidb", "facebook/rocksdb",
                  "vitessio/vitess", "yugabyte/yugabyte-db", "scylladb/scylladb"],
    "orchestration": ["kubernetes/kubernetes", "containerd/containerd", "moby/moby",
                      "temporalio/temporal"],
}
FIELDS = "i.id, i.repo_full_name, i.form, i.url, i.title, i.labels, i.reactions, i.comments, i.author, i.author_association, i.created_at, q.kind, q.tier, q.reasons, i.body"


def rows(db, where, params, n, rng):
    found = [dict(r) for r in db.execute(
        f"SELECT {FIELDS} FROM issues i JOIN issue_quality q ON q.issue_id=i.id WHERE {where} ORDER BY i.id", params)]
    picked = rng.sample(found, min(n, len(found)))
    for r in picked:
        r["body"] = (r["body"] or "")[:4000]
    return picked, len(found)


def main():
    rng = random.Random(SEED)
    db = sqlite3.connect(config.DB_PATH)
    db.row_factory = sqlite3.Row
    plan = {
        "baseline_random": ("i.form <> 'distributed'", (), 30),
        "baseline_core": ("i.form <> 'distributed' AND q.tier='core'", (), 30),
        "baseline_excluded": ("i.form <> 'distributed' AND q.tier='excluded'", (), 30),
    }
    for name, repos in GROUPS.items():
        marks = ",".join("?" * len(repos))
        plan[f"distributed_{name}"] = (
            f"i.form='distributed' AND q.tier IN ('core','usable') AND i.repo_full_name IN ({marks})", tuple(repos), 30)
    manifest = {"seed": SEED, "db": "data/issues.db", "samples": {}}
    for name, (where, params, n) in plan.items():
        picked, population = rows(db, where, params, n, rng)
        (HERE / f"sample_{name}.json").write_text(json.dumps(picked, ensure_ascii=False, indent=2) + "\n")
        manifest["samples"][name] = {"where": where, "params": params, "population": population, "n": len(picked)}
    (HERE / "samples.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest["samples"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
