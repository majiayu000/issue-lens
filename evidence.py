"""Explicit local test inputs and bounded GitHub PR snapshots; no code execution."""
import datetime
import hashlib
import http.client
from pathlib import Path
import re
from urllib.parse import urlsplit
import urllib.error

from gh import GitHub


class EvidenceError(RuntimeError):
    pass


def load_tests(paths: list[Path]) -> list[dict]:
    result, seen, size = [], set(), 0
    for path in paths:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        content = path.read_text(encoding="utf-8")
        size += len(content)
        if size > 120000:
            raise EvidenceError("Test inputs exceed 120,000 characters; select a narrower set of files.")
        if not content.strip():
            raise EvidenceError(f"Empty test input: {path}")
        result.append({"id": f"T{len(result) + 1}", "path": str(path), "content": content,
                       "sha256": hashlib.sha256(content.encode()).hexdigest()})
    return result


def github_path(url: str, kind: str) -> str:
    parsed = urlsplit(url)
    match = re.fullmatch(r"/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/" + kind + r"/(\d+)", parsed.path)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not match:
        raise EvidenceError("Invalid GitHub evidence URL.")
    owner, repo, number = match.groups()
    if owner in (".", "..") or repo in (".", ".."):
        raise EvidenceError("Invalid GitHub evidence repository.")
    return f"/repos/{owner}/{repo}/{'pulls' if kind == 'pull' else 'issues'}/{number}"


def fetch_pr_evidence(source: dict, client: GitHub) -> dict:
    """Cross-references are relationships, never automatic proof of a fix."""
    path = github_path(source["url"], "issues")
    links = {}
    for page in range(1, 4):
        events = client.get(path + "/timeline", {"per_page": 100, "page": page})
        if not isinstance(events, list):
            raise EvidenceError("Invalid GitHub timeline response.")
        for event in events:
            linked = (event.get("source") or {}).get("issue") or {}
            if event.get("event") == "cross-referenced" and linked.get("pull_request"):
                url = linked["html_url"]
                github_path(url, "pull")
                links[url] = None
        if len(events) < 100:
            break
    pulls = []
    # Latest observed references first; explicitly record both kinds of cap.
    for url in list(links)[-3:][::-1]:
        pr_path = github_path(url, "pull")
        pr = client.get(pr_path)
        files = client.get(pr_path + "/files", {"per_page": 100, "page": 1})
        if not isinstance(pr, dict) or not isinstance(files, list):
            raise EvidenceError("Invalid GitHub pull-request response.")
        body = pr.get("body") or ""
        budget, patches = 12000, []
        # Filename hints affect excerpt order only, not coverage judgments.
        for file in sorted(files, key=lambda f: not any(
                word in f["filename"].lower() for word in ("test", "spec"))):
            raw = file.get("patch")
            patch = (raw or "")[:budget]
            budget -= len(patch)
            patches.append({"filename": file["filename"], "status": file["status"],
                            "patch": patch, "patch_unavailable": raw is None,
                            "patch_truncated": raw is not None and len(patch) < len(raw)})
        pulls.append({"url": url, "title": pr["title"], "body": body[:6000],
                      "body_truncated": len(body) > 6000, "state": pr["state"],
                      "merged": pr["merged"], "head_sha": pr["head"]["sha"],
                      "base_sha": pr["base"]["sha"], "merge_commit_sha": pr.get("merge_commit_sha"),
                      "relation": "cross_reference_not_verified_fix", "files": patches,
                      "files_truncated": pr["changed_files"] > len(files)})
    return {"fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timeline_may_be_truncated": len(events) == 100,
            "pulls_truncated": len(links) > 3, "pulls": pulls}


def attach_pr_evidence(sources: list[dict], cited_ids: set[int]) -> None:
    if not cited_ids:
        return
    try:
        client = GitHub()
        for source in sources:
            if source["id"] in cited_ids:
                source["pr_evidence"] = fetch_pr_evidence(source, client)
    except urllib.error.HTTPError as error:
        raise EvidenceError(f"PR evidence fetch failed (HTTP {error.code}); no report was accepted.") from None
    except (http.client.HTTPException, OSError, RuntimeError, KeyError, TypeError, ValueError, AttributeError):
        raise EvidenceError("PR evidence fetch failed; check GitHub access and response format.") from None
