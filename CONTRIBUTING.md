# Contributing to issue-lens

Thanks for considering a contribution.

## Setup

```bash
git clone https://github.com/majiayu000/issue-lens.git
cd issue-lens
gh auth login        # or export GITHUB_TOKEN=...
```

No virtualenv needed — the project uses only the Python 3.12 standard library.

## Build / test

```bash
python3 -m compileall -q .            # build check (what CI runs)
python3 -m unittest test_units -v     # unit tests (no network needed)
```

End-to-end smoke test (hits the GitHub API, ~1 minute):

```bash
python3 s01_pick_repos.py --forms cli --limit 3
python3 s02_fetch_issues.py --forms cli --limit-repos 2 --max-issues 100
python3 s03_report.py --forms cli
python3 s04_search.py --form cli --top 5
```

## Rules

- **DCO**: every commit must include a `Signed-off-by` line — commit with `git commit -s`. By signing off you certify you have the right to submit the work under the MIT license (see [DCO](https://developercertificate.org/)).
- **History**: prefer rebase-based, focused commits; first line of the message should say *why*, not just *what*.
- Run the unit tests before opening a PR; CI must pass.
- Keep new dependencies out — standard library only is a feature here.
