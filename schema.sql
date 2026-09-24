CREATE TABLE IF NOT EXISTS repos (
    full_name     TEXT PRIMARY KEY,
    form          TEXT NOT NULL,
    stars         INTEGER,
    language      TEXT,
    description   TEXT,
    topics        TEXT,
    issues_total  INTEGER,
    issues_fetched INTEGER,
    truncated     INTEGER DEFAULT 0,
    fetched_at    TEXT
);

CREATE TABLE IF NOT EXISTS issues (
    id              INTEGER PRIMARY KEY,
    repo_full_name  TEXT NOT NULL,
    number          INTEGER NOT NULL,
    form            TEXT NOT NULL,
    title           TEXT,
    body            TEXT,
    reactions       INTEGER DEFAULT 0,
    comments        INTEGER,
    labels          TEXT,
    author          TEXT,
    created_at      TEXT,
    closed_at       TEXT,
    url             TEXT,
    extract_json    TEXT,
    UNIQUE(repo_full_name, number)
);

CREATE INDEX IF NOT EXISTS idx_issues_form_reactions ON issues(form, reactions DESC);
CREATE INDEX IF NOT EXISTS idx_issues_repo ON issues(repo_full_name);

CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING fts5(
    title, body,
    issue_id UNINDEXED
);
