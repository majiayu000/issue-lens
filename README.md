# issue-lens

[![CI](https://github.com/majiayu000/issue-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/majiayu000/issue-lens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Mine **real-world GitHub issues** from peer products — indexed by **product form** (desktop app, CLI, …) — to fuel test design for your own product. When you are about to test a new desktop app and run out of test ideas, look up what users of comparable desktop apps actually reported, and turn those into test charters.

Design rationale and the full feasibility research (data sources, prior art, academic evidence) live in [docs/research.md](docs/research.md) (Chinese).

## Try the reports before rebuilding

**[Browse all 30,784 collected issues from 79 repositories](out/corpus/README.md)**
or **[download the corpus snapshot from GitHub Releases](https://github.com/majiayu000/issue-lens/releases/tag/corpus-2026-09-23)**.
The online directory lists every collected issue with its original GitHub link;
the downloadable SQLite and JSONL files include issue bodies.

Start with the committed [desktop report](out/report_desktop.md) or
[CLI report](out/report_cli.md), then follow the
[worked issue-to-test-charter example](docs/issue-to-test-charter.md).
Reading these files needs no credentials or local database. Fetching a new corpus
is a separate step. For automatic extraction and planning, see
[Generate a test plan with Codex CLI](#generate-a-test-plan-with-codex-cli).

## How it works

```
s01_pick_repos.py     pick top repos per form via GitHub topics (stars threshold, dedup, rank by stars)
s02_fetch_issues.py   fetch high-quality closed issues into SQLite + FTS5
s03_report.py         generate a value-check report per form (top issues by 👍 reactions)
s04_search.py         query the corpus: keyword (FTS) or popularity ranking
extract.py            Codex CLI extraction (symptom → supported cause → test ideas), cached in SQLite
s05_plan.py           PRD → conjunctive FTS + relevance review → test plan + existing-test comparison
```

Quality bar for an issue to enter the corpus (see research §4.4):

- `is:closed` **and** `linked:pr` — closed issue with a linked pull request
- `reason:completed` — closed as completed; this can include implemented feature requests and does not establish a bug or its root cause
- top N by 👍 reactions per repo (reactions ≈ how many people hit the problem); hard Search-API cap at 1000 results per query is recorded per repo in `repos.truncated` instead of being silently dropped

Current corpus snapshot (2026-09-23): **79 repos, 30,784 issues** — desktop: 40 repos / 14,730 issues; CLI: 39 repos / 16,054 issues. Sample reports: [out/report_desktop.md](out/report_desktop.md) · [out/report_cli.md](out/report_cli.md).

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

The [complete online directory](out/corpus/README.md) groups all **79 repositories
and 30,784 issues** by source repository. Unlike the top-50 sample reports, it
lists every collected issue. Click a title to read the original GitHub issue.

The [2026-09-23 corpus release](https://github.com/majiayu000/issue-lens/releases/tag/corpus-2026-09-23)
provides compressed SQLite and JSONL snapshots, a manifest and SHA-256 checksums.
The SQLite file works with the existing search and planning scripts through
`ISSUE_LENS_DB`; [download and query instructions](out/corpus/README.md#下载后查询)
are included. The large database remains outside Git history, but is now hosted
on GitHub as a release asset instead of existing only on the local machine.

All records are retained. In the public copy, 24 issue bodies containing
credential-like text are replaced with a redaction notice; their original URLs
remain available. These matches may include inert examples. Local model caches
are excluded. The [manifest](out/corpus/manifest.json) lists the affected records
and exact snapshot scope. Original issue text remains attributable to its
authors; this project's MIT license does not relicense third-party content.

The snapshot contains issue bodies and comment counts, not comment text, and
15 repositories were capped at 1,000 issues. Run the fetch pipeline to create a
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
```

The plan command accepts a PRD or a coherent README scope of up to 80,000 characters. It extracts at most eight requirement themes with verbatim source quotes. Each theme has 1–3 alternative queries with 2–4 terms combined using AND; each query contributes up to eight matches. Codex is asked to include a broad two-word query before more-specific alternatives, avoiding descriptive phrases that rarely occur verbatim. Up to 60 candidates, distributed across themes, are reviewed by Codex for shared failure mechanisms. The reviewer must supply a verbatim excerpt and may reject every candidate. Only selected issues are extracted, in batches of five, reusing cached extractions. This retrieval change applies to `s05_plan.py`; standalone search retains its existing behavior.

The plan can also contain PRD-derived baseline cases with no historical source, so empty retrieval no longer forces a requirement to be skipped. Outputs are a new Markdown file and a matching JSON file with source links, evidence quotes, input hash, usage, and Codex thread IDs. Existing output files are never overwritten.

`--tests` accepts explicit UTF-8 source files, up to 120,000 characters total; it does not scan a repository or run tests. The model compares triggers and assertions, then groups cases into potential omissions, partial coverage, and existing coverage (last). Existing/partial coverage requires an exact, unique source quote; file paths and line numbers are computed locally. JSON records the supplied text hashes. Without files, coverage is marked not reviewed. These are model assessments of the supplied files, not proof that a test is missing from the whole product.

`--with-pr-evidence` fetches PR cross-references for issues cited by the first draft, then reviews that draft again if PRs were found. Per issue, it scans the first three timeline pages (up to 300 events) and selects up to three most recently encountered distinct PR references. Per PR, it retains the first 100 changed files, up to 6,000 body characters and 12,000 patch characters, prioritizing filenames containing test/spec within those files. JSON records timestamps, commit IDs and truncation/missing-patch flags. Details and files are separate API reads, not an atomic revision snapshot. Cross-references do not establish that a PR fixes an issue, and unmerged PRs are proposals. Missing patches or absent cross-references do not establish absent tests or fixes. Fetch failures fail the command rather than being reported as no PRs found. The mechanism uses GitHub's documented [timeline API](https://docs.github.com/en/rest/issues/timeline), [cross-reference events](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types), and [pull request APIs](https://docs.github.com/en/rest/pulls/pulls).

The selected product text, issue excerpts, supplied test files and optional PR excerpts are sent to Codex using its existing login. Each call runs in a temporary directory with user config ignored, read-only sandboxing, project instructions excluded, and tools/hooks/memory features disabled. Calls time out after 300 seconds; failed calls or invalid/unattributed output fail the command. Earlier validated extraction batches remain cached. Plans prioritize 8–12 useful cases (at most 24) and short, unique test-source quotes. Model-generated test cases are **drafts, not executed results or proof of a product defect**.

The [updated five-product samples](out/five-products-20261002/README.md) contain 60 draft cases generated with fixed product documents, selected test-source snapshots and live PR evidence. The [rclean same-model comparison](out/five-products-20261002/comparison/README.md) found some additional boundary detail, but did not establish overall superiority to directly reading the PRD; the main risks appeared in both arms. The original [`2026-10-01` samples](out/five-products-20261001/) remain available for historical context. Input manifests record repository revisions and hashes; `remem` uses selected README sections rather than the entire document. No product test cases were executed.

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
- Issue extraction uses titles, bodies and labels; at most 12,000 body characters are sent, with truncation recorded and unknown causes left null. PR bodies/patches are optional, bounded supplements to planning, not corpus-wide collection. Comments are not collected.
- The existing corpus snapshot is not refreshed by the plan command. Extraction caches can be reused across model choices; each cached record retains its original generation provenance.

## Roadmap

1. Extend the same-model comparison beyond rclean and measure which suggestions survive review and actual execution
2. Improve PR evidence selection: recent cross-references can include unrelated forks or package updates
3. More forms: web frontend, backend, mobile (mobile already has a ready-made taxonomy: DroidDefects, see research §2.1)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Commits must be signed off (`git commit -s`, DCO). This project is not looking for AI-generated contributions — please write your own code and descriptions.
