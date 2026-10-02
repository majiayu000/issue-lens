# issue-lens

[![CI](https://github.com/majiayu000/issue-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/majiayu000/issue-lens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Mine **real-world GitHub issues** from peer products — indexed by **product form** (desktop app, CLI, …) — to fuel test design for your own product. When you are about to test a new desktop app and run out of test ideas, look up what users of comparable desktop apps actually reported, and turn those into test charters.

Design rationale and the full feasibility research (data sources, prior art, academic evidence) live in [docs/research.md](docs/research.md) (Chinese).

## Try the reports before rebuilding

**[Browse all 31,084 collected issues from 82 repositories](out/corpus/README.md)**
or **[download the corpus snapshot from GitHub Releases](https://github.com/majiayu000/issue-lens/releases/tag/corpus-2026-10-03)**.
The online directory lists every collected issue with its original GitHub link;
the downloadable SQLite and JSONL files include issue bodies.

Start with the committed [desktop report](out/report_desktop.md) or
[CLI report](out/report_cli.md), then follow the
[worked issue-to-test-charter example](docs/issue-to-test-charter.md).
Reading these files needs no credentials or local database. Fetching a new corpus
is a separate step. For automatic extraction and planning, see
[Generate a test plan with Codex CLI](#generate-a-test-plan-with-codex-cli).

For change-focused reviews, task-based issue grouping, explicit source expansion
and executable acceptance checks, see [the usage workflows](docs/using-issue-lens.md).

## How it works

```
s01_pick_repos.py     pick top repos per form via GitHub topics (stars threshold, dedup, rank by stars)
s02_fetch_issues.py   fetch high-quality closed issues into SQLite + FTS5
s03_report.py         generate a value-check report per form (top issues by 👍 reactions)
s04_search.py         query the corpus: keyword (FTS) or popularity ranking
extract.py            Codex CLI extraction (symptom → supported cause → test ideas), cached in SQLite
s05_plan.py           PRD → conjunctive FTS + relevance review → test plan + existing-test comparison
s06_curate.py         task query → issue classification → scenario groups with every source retained
```

Quality bar for an issue to enter the corpus (see research §4.4):

- `is:closed` **and** `linked:pr` — closed issue with a linked pull request
- `reason:completed` — closed as completed; this can include implemented feature requests and does not establish a bug or its root cause
- top N by 👍 reactions per repo (reactions ≈ how many people hit the problem); hard Search-API cap at 1000 results per query is recorded per repo in `repos.truncated` instead of being silently dropped

Current corpus snapshot (updated 2026-10-03): **82 repos, 31,084 issues** — desktop:
41 repos / 14,830 issues; CLI: 41 repos / 16,254 issues. The original 79 repositories
retain their 2026-09-23 snapshot; restic, rclone and electron-builder add 100 issues
each. The top-50 sample reports still show the original snapshot:
[desktop](out/report_desktop.md) · [CLI](out/report_cli.md).

## Quick start

Zero third-party dependencies: Python 3.12 standard library + an authenticated `gh` CLI (or `GITHUB_TOKEN`).

```bash
git clone https://github.com/majiayu000/issue-lens.git
cd issue-lens
gh auth login                          # or: export GITHUB_TOKEN=...
python3 s01_pick_repos.py              # 1. pick repos for every form in config.py
python3 s02_fetch_issues.py            # 2. fetch issues (~80 repos, throttled by Search API 30 req/min)
python3 s03_report.py                  # 3. value-check reports -> out/report_{form}.md
python3 s04_search.py --form desktop --q "crash startup"
python3 s04_search.py --form cli --q "utf-8 encoding" --sort relevance
python3 s04_search.py --form all --top 30
```

Smoke test the whole pipeline in under a minute:

```bash
python3 s01_pick_repos.py --forms cli --limit 3
python3 s02_fetch_issues.py --forms cli --limit-repos 2 --max-issues 100
python3 s03_report.py --forms cli
python3 s04_search.py --form cli --top 5
```

## Browse or download the corpus

The [complete online directory](out/corpus/README.md) groups all **82 repositories
and 31,084 issues** by source repository. Unlike the top-50 sample reports, it
lists every collected issue. Click a title to read the original GitHub issue.

The [2026-10-03 corpus release](https://github.com/majiayu000/issue-lens/releases/tag/corpus-2026-10-03)
provides compressed SQLite and JSONL snapshots, a manifest and SHA-256 checksums.
The SQLite file works with the existing search and planning scripts through
`ISSUE_LENS_DB`; [download and query instructions](out/corpus/README.md#下载后查询)
are included. The large database remains outside Git history, but is now hosted
on GitHub as a release asset instead of existing only on the local machine.

All records are retained. In the public copy, 25 issue bodies containing
credential-like text are replaced with a redaction notice; their original URLs
remain available. These matches may include inert examples. Local model caches
are excluded. The [manifest](out/corpus/manifest.json) lists the affected records
and exact snapshot scope. Original issue text remains attributable to its
authors; this project's MIT license does not relicense third-party content.

The snapshot contains issue bodies and comment counts, not comment text, and
15 original repositories were capped at 1,000 issues and the three new sources
at 100 each. Run the fetch pipeline to create a
new snapshot; `data/repos_*.json` records the source repository lists.

## Generate a test plan with Codex CLI

Use an installed, authenticated Codex CLI (verified with 0.160.0). No separate model API key or Python package is required. The commands below use the CLI's default model; an explicit model must be supported by your CLI account.

The Codex integration currently targets macOS/Linux and uses a separate process group so a timeout also stops the launcher's child processes.

```bash
export ISSUE_LENS_LLM_ENGINE=codex
python3 extract.py --form cli --q "permission" --limit 5
python3 s05_plan.py --form cli --prd product.md --out out/product-tests.md
# Optional: --limit 20 (default 12, maximum 30 candidate issues)
# Compare selected existing tests and supplement cited issues with PR evidence:
python3 s05_plan.py --form cli --prd product.md --tests tests/test_paths.py \
  --tests tests/test_permissions.py --with-pr-evidence --out out/product-reviewed.md
# Focus on an explicit code change:
python3 s05_plan.py --form cli --prd product.md --diff change.diff \
  --tests tests/test_paths.py --with-pr-evidence --out out/change-review.md
# Group historical cases by trigger, retaining bug/feature/question distinctions:
python3 s06_curate.py --form cli --q "restore" --repo restic/restic \
  --limit 6 --with-pr-evidence --out out/restore-review.md
```

The plan command accepts a PRD or a coherent README scope of up to 80,000 characters. It extracts at most eight requirement themes with verbatim source quotes. Each theme has 1–3 alternative queries with 2–4 terms combined using AND; each query contributes up to eight matches. Codex is asked to include a broad two-word query before more-specific alternatives, avoiding descriptive phrases that rarely occur verbatim. Up to 60 candidates, distributed across themes, are reviewed by Codex for shared failure mechanisms. The reviewer must supply a verbatim excerpt and may reject every candidate. Only selected issues are extracted, in batches of five, reusing cached extractions. This retrieval change applies to `s05_plan.py`; standalone search retains its existing behavior.

The plan can also contain PRD-derived baseline cases with no historical source, so empty retrieval no longer forces a requirement to be skipped. Outputs are a new Markdown file and a matching JSON file with source links, evidence quotes, input hash, usage, and Codex thread IDs. Existing output files are never overwritten.

`--diff` accepts an explicit UTF-8 diff of up to 60,000 characters. Both requirement
selection and plan generation focus on the changed behavior, with a requested
3–5 priority cases. Requirement quotes must still come from the PRD; the diff
does not establish new product requirements. Its SHA-256 is recorded in JSON.

`--tests` accepts explicit UTF-8 source files, up to 120,000 characters total; it does not scan a repository or run tests. The model compares triggers and assertions, then groups cases into potential omissions, partial coverage, and existing coverage (last). Existing/partial coverage requires an exact, unique source quote; file paths and line numbers are computed locally. JSON records the supplied text hashes. Without files, coverage is marked not reviewed. These are model assessments of the supplied files, not proof that a test is missing from the whole product.

`--with-pr-evidence` fetches evidence for issues cited by the first draft, then
reviews it again when PRs or comments are available. It prioritizes the current
GitHub closing event's PR, then explicit closing references, with at most three
distinct PRs. It also reads the latest eight comments, up to 1,000 characters
each. Arbitrary timeline cross-references are no longer selected. Per PR, it
retains the first 100 changed files, up to 6,000 body characters and 12,000 patch
characters, prioritizing filenames containing test/spec. JSON records timestamps,
commit IDs and truncation/missing-patch flags. A closing event establishes a
relationship, not a verified root cause or applicability to the target product;
an unmerged PR remains a proposal. Details and files are separate API reads,
not an atomic revision snapshot. Fetch errors, including GraphQL errors returned
with HTTP 200, fail the command. See GitHub's [issue GraphQL fields](https://docs.github.com/en/graphql/reference/issues)
and [pull request REST APIs](https://docs.github.com/en/rest/pulls/pulls).

The selected product text, issue excerpts, supplied test files and optional PR excerpts are sent to Codex using its existing login. Each call runs in a temporary directory with user config ignored, read-only sandboxing, project instructions excluded, and tools/hooks/memory features disabled. Calls time out after 300 seconds; failed calls or invalid/unattributed output fail the command. Earlier validated extraction batches remain cached. Plans prioritize 8–12 useful cases (at most 24) and short, unique test-source quotes. Model-generated test cases are **drafts, not executed results or proof of a product defect**.

The [updated five-product samples](out/five-products-20261002/README.md) contain 60 draft cases generated with fixed product documents, selected test-source snapshots and live PR evidence. The [rclean same-model comparison](out/five-products-20261002/comparison/README.md) found some additional boundary detail, but did not establish overall superiority to directly reading the PRD; the main risks appeared in both arms. The original [`2026-10-01` samples](out/five-products-20261001/) remain available for historical context. Input manifests record repository revisions and hashes; `remem` uses selected README sections rather than the entire document. Those October 1–2 samples did not execute product tests. The [October 3 follow-up](out/expansion-20261003/README.md) records actual rclean execution and regression-test additions.

## Configuration

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | GitHub credential (falls back to `gh auth token`) |
| `ISSUE_LENS_DB` | SQLite path (default `data/issues.db`) |
| `ISSUE_LENS_MAX_REPOS` / `ISSUE_LENS_MAX_ISSUES` | per-form repo cap / per-repo issue cap |
| `ISSUE_LENS_LLM_ENGINE` | `codex` enables extraction and planning; default `none` keeps `extract_issue()` disabled |
| `ISSUE_LENS_MODEL` | optional Codex model override; unset uses the CLI default |

Product forms, topic seeds and the initial bug taxonomies live in `config.py`. Current forms: `desktop` (Electron/Tauri/desktop-app) and `cli` (cli/command-line/terminal) — adding a form is one dict entry.

## Known limitations

- "Implemented feature requests" pass the quality bar. Extraction classifies bug / feature / question / unclear, but this is a model judgment requiring review.
- Topic seeds leak across forms (e.g. Electron-based terminal emulators land in both lists).
- FTS5 tokenizes on whitespace; GitHub issues are mostly English so this is fine for now (no CJK support yet).
- Retrieval uses English keywords and phrases followed by model selection, not embeddings. AND queries can miss alternative wording; model selection can still make semantic mistakes. The eight-theme and candidate limits prevent claims of complete PRD coverage.
- Issue extraction uses titles, bodies and labels; at most 12,000 body characters are sent, with truncation recorded and unknown causes left null. PR bodies/patches and recent comments are optional, bounded supplements to planning and curation, not corpus-wide collection.
- The existing corpus snapshot is not refreshed by the plan command. Extraction caches can be reused across model choices; each cached record retains its original generation provenance.

## Roadmap

1. Extend the same-model comparison beyond rclean and measure which suggestions survive review and actual execution
2. Measure the relevance of closing-PR and comment evidence through further reviewed examples
3. More forms: web frontend, backend, mobile (mobile already has a ready-made taxonomy: DroidDefects, see research §2.1)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Commits must be signed off (`git commit -s`, DCO). This project is not looking for AI-generated contributions — please write your own code and descriptions.
