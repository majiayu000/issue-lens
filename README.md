# issue-lens

[![CI](https://github.com/majiayu000/issue-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/majiayu000/issue-lens/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Mine **real-world GitHub issues** from peer products — indexed by **product form** (desktop app, CLI, …) — to fuel test design for your own product. When you are about to test a new desktop app and run out of test ideas, look up what users of comparable desktop apps actually reported, and turn those into test charters.

Design rationale and the full feasibility research (data sources, prior art, academic evidence) live in [docs/research.md](docs/research.md) (Chinese).

## Try the reports before rebuilding

Start with the committed [desktop report](out/report_desktop.md) or
[CLI report](out/report_cli.md), then follow the
[worked issue-to-test-charter example](docs/issue-to-test-charter.md).
Reading these files needs no credentials or local database. Fetching a new corpus
is a separate step, and automatic LLM extraction is not implemented yet.

## How it works

```
s01_pick_repos.py     pick top repos per form via GitHub topics (stars threshold, dedup, rank by stars)
s02_fetch_issues.py   fetch high-quality closed issues into SQLite + FTS5
s03_report.py         generate a value-check report per form (top issues by 👍 reactions)
s04_search.py         query the corpus: keyword (FTS) or popularity ranking
extract.py            pluggable LLM extraction interface (symptom → root cause → test ideas); engine not wired yet
```

Quality bar for an issue to enter the corpus (see research §4.4):

- `is:closed` **and** `linked:pr` — connected to the pull request that fixed it
- `reason:completed` — maintainers confirmed it as a real, resolved problem
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

## The corpus is not in this repo — rebuild it

`data/issues.db` (~176 MB of full issue bodies) is intentionally excluded: it exceeds GitHub's 100 MB file limit, and redistributing issue text at scale sits in an uncertain licensing zone with real PII risk (see research §5). The pipeline rebuilds it from public APIs in roughly 30 minutes; `data/repos_*.json` (repo lists, no user content) are tracked for reproducibility.

## Configuration

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | GitHub credential (falls back to `gh auth token`) |
| `ISSUE_LENS_DB` | SQLite path (default `data/issues.db`) |
| `ISSUE_LENS_MAX_REPOS` / `ISSUE_LENS_MAX_ISSUES` | per-form repo cap / per-repo issue cap |
| `ISSUE_LENS_LLM_ENGINE` | extraction engine (`none` = skip; contract in `extract.py`) |

Product forms, topic seeds and the initial bug taxonomies live in `config.py`. Current forms: `desktop` (Electron/Tauri/desktop-app) and `cli` (cli/command-line/terminal) — adding a form is one dict entry.

## Known limitations

- "Implemented feature requests" pass the quality bar (high-reaction items are often exactly that, e.g. terminal hotkey dropdowns). Separating bugs from features is the job of the LLM classification step — interface ready, engine not wired.
- Topic seeds leak across forms (e.g. Electron-based terminal emulators land in both lists).
- FTS5 tokenizes on whitespace; GitHub issues are mostly English so this is fine for now (no CJK support yet).

## Roadmap

1. Wire an LLM engine into `extract.py` (symptom / root-cause category / environment / test ideas) and store as `issues.extract_json`
2. PRD → test-checklist generator: embed your product description, retrieve similar issues, produce a grouped checklist with real issue links
3. More forms: web frontend, backend, mobile (mobile already has a ready-made taxonomy: DroidDefects, see research §2.1)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Commits must be signed off (`git commit -s`, DCO). This project is not looking for AI-generated contributions — please write your own code and descriptions.
