# Security Policy

## Reporting a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/majiayu000/issue-lens/security/advisories/new) for security issues. Do not open a public issue for anything you believe is exploitable.

## Scope notes

- issue-lens reads only public GitHub data through the official REST/Search APIs and honors rate limits; it does not bypass authentication or scrape HTML.
- Credentials (`GITHUB_TOKEN` / `gh auth token`) are kept in process memory only — they are never logged, persisted, or included in reports. Reports mentioning a credential leak should be treated as security issues.
- Generated reports (`out/report_*.md`) contain excerpts of and links to public issue content; if you believe a report exposes private data, report it here rather than editing it yourself.
