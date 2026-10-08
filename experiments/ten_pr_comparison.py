"""Run the frozen ten-PR A/B experiment with existing Issue Lens model/evidence code.

Inputs and native checks are recorded separately; this never executes model suggestions.
A and B receive identical requirements, code, diff, tests and prompt; only sources differ.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence import EvidenceError, attach_pr_evidence
from extract import extract_batch
from llm import ModelError, generate_json
from retrieval import retrieve
from s05_plan import PLAN_PROMPT, get_requirements, validate_plan


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_sample(sample, db_path, output):
    output.mkdir(parents=True, exist_ok=False)
    record = {"sample": sample["id"], "head_sha": sample["head_sha"],
              "diff_sha256": sample["diff_sha256"], "requested_model": os.environ.get("ISSUE_LENS_MODEL"),
              "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "status": "running", "stages": {}}
    save(output / "status.json", record)

    def stage(name, fn):
        start = time.monotonic()
        try:
            value = fn()
        except Exception as error:
            # Keep existing model/evidence error contracts, never accept failed output.
            record["stages"][name] = {"status": "failed", "seconds": time.monotonic() - start,
                                       "error_type": type(error).__name__}
            if isinstance(error, (ModelError, EvidenceError)):
                record["stages"][name]["error"] = str(error)
            save(output / "status.json", record)
            raise
        record["stages"][name] = {"status": "completed", "seconds": time.monotonic() - start}
        save(output / "status.json", record)
        return value

    try:
        # PR title/body establish the actual requested change, supplemented by product docs.
        prd = sample["pr"]["title"] + "\n" + sample["pr"]["body"] + "\n\n" + "\n\n".join(
            doc["content"] for doc in sample["docs"])
        requirements, questions, query_run = stage("requirements", lambda: get_requirements(prd, "cli", sample["diff"]))
        save(output / "requirements.json", {"requirements": requirements, "open_questions": questions,
                                            "generation": query_run, "prd_sha256": hashlib.sha256(prd.encode()).hexdigest()})
        with sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
            # TEMP view excludes the target project and issues newer than the PR.
            # The original corpus remains read-only. Both restrictions are saved explicitly.
            db.execute("CREATE TEMP TABLE experiment_boundary(repo TEXT, cutoff TEXT)")
            db.execute("INSERT INTO experiment_boundary VALUES (?, ?)",
                       (sample["repo"], sample["pr"]["mergedAt"]))
            db.execute("CREATE TEMP VIEW issues AS SELECT * FROM main.issues WHERE "
                       "repo_full_name <> (SELECT repo FROM experiment_boundary) AND "
                       "created_at < (SELECT cutoff FROM experiment_boundary)")
            issues, retrieval_run = stage("retrieval", lambda: retrieve(db, "cli", requirements, 3))
        extracted = stage("extraction", lambda: extract_batch(issues, "cli"))
        by_id = {row["id"]: row for row in extracted}
        sources = [{"id": issue["id"], "title": issue["title"], "url": issue["url"],
                    "repo": issue["repo_full_name"], "extraction": by_id[issue["id"]]} for issue in issues]
        stage("pr_evidence", lambda: attach_pr_evidence(sources, {s["id"] for s in sources}))
        save(output / "history.json", {"sources": sources, "generation": retrieval_run,
                                      "target_repo_excluded": sample["repo"],
                                      "issue_creation_cutoff": sample["pr"]["mergedAt"],
                                      "pr_evidence_note": "Current bounded GitHub snapshots, not time-travel evidence."})
        common = {"prd": prd, "form": "cli", "requirements": requirements,
                  "open_questions": questions, "tests": sample["tests"], "diff": sample["diff"],
                  "code": sample["code"]}
        # Retrieval-specific fields are not allowed to leak into the baseline.
        common["requirements"] = [{k: v for k, v in r.items() if k not in
                                   ("candidate_ids", "retrieved_source_ids", "retrieval_evidence")}
                                  for r in requirements]
        record.update(common_input_sha256=digest(common), prompt_sha256=hashlib.sha256(PLAN_PROMPT.encode()).hexdigest(),
                      sources_count=len(sources), requirements_count=len(requirements),
                      order=["A", "B"] if sample["pr"]["number"] % 2 else ["B", "A"])
        for arm in record["order"]:
            history = [] if arm == "A" else sources
            inputs = {**common, "sources": history}
            save(output / (arm + ".input.json"), inputs)
            if not requirements:
                # Existing s05 behavior: an unrelated/unspecified diff has no synthesized cases.
                plan, provenance = {"cases": [], "coverage_gaps": []}, {}
            else:
                plan, provenance = stage(arm, lambda: generate_json(PLAN_PROMPT, inputs))
                stage(arm + "_validation", lambda: validate_plan(plan, requirements, history, sample["tests"]))
            save(output / (arm + ".json"), {"status": "draft_not_executed", "plan": plan,
                                          "generation": provenance, "input_sha256": digest(inputs),
                                          "common_input_sha256": digest(common),
                                          "prompt_sha256": record["prompt_sha256"]})
        record["status"] = "paired_drafts_not_executed"
    except Exception:
        record["status"] = "failed_no_pair_accepted"
        save(output / "status.json", record)
        raise
    save(output / "status.json", record)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="New output directory; never overwrites a run")
    ap.add_argument("--sample", help="Exact sample id for a deliberate retry in a new directory")
    args = ap.parse_args()
    if os.environ.get("ISSUE_LENS_LLM_ENGINE") != "codex" or not os.environ.get("ISSUE_LENS_MODEL"):
        ap.error("Set ISSUE_LENS_LLM_ENGINE=codex and an explicit ISSUE_LENS_MODEL")
    manifest = json.loads((args.inputs / "manifest.json").read_text())
    selected = [s for s in manifest["samples"] if not args.sample or s["id"] == args.sample]
    if not selected:
        ap.error("No matching frozen sample")
    args.out.mkdir(parents=True, exist_ok=False)
    failed = []
    for row in selected:
        try:
            result = run_sample(json.loads((args.inputs / row["input"]).read_text()), args.db, args.out / row["id"])
            print(row["id"], result["status"], flush=True)
        except Exception as error:
            failed.append(row["id"])
            print(row["id"], "failed:", type(error).__name__, flush=True)
    save(args.out / "run.json", {"sample_count": len(selected), "failed": failed,
                                "status": "failed" if failed else "paired_drafts_not_executed"})
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
