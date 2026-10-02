"""Explicit local test inputs and bounded GitHub discussion/PR snapshots."""
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


ISSUE_EVIDENCE_QUERY = """query($owner:String!,$name:String!,$number:Int!) {
  repository(owner:$owner,name:$name) { issue(number:$number) {
    state closedAt
    timelineItems(last:1,itemTypes:[CLOSED_EVENT]) { nodes { ... on ClosedEvent {
      createdAt closer { __typename ... on PullRequest { url } }
    } } }
    closedByPullRequestsReferences(first:3,includeClosedPrs:true) {
      totalCount nodes { url merged }
    }
    comments(last:8) { totalCount nodes {
      url body authorAssociation createdAt updatedAt
    } }
  } }
}"""


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
    """Prefer the actual closing event, then explicit closing references."""
    path = github_path(source["url"], "issues")
    _, _, owner, name, _, number = path.split("/")
    issue = client.graphql(ISSUE_EVIDENCE_QUERY, {
        "owner": owner, "name": name, "number": int(number)})["repository"]["issue"]
    if not isinstance(issue, dict):
        raise EvidenceError("GitHub issue evidence is unavailable.")
    links = {}
    for event in issue["timelineItems"]["nodes"]:
        closer = event.get("closer") or {}
        if (issue["state"] == "CLOSED" and event["createdAt"] == issue["closedAt"]
                and closer.get("__typename") == "PullRequest"):
            links[closer["url"]] = "closed_by_pull_request"
    refs = issue["closedByPullRequestsReferences"]
    for ref in sorted(refs["nodes"], key=lambda ref: not ref["merged"]):
        links.setdefault(ref["url"], "closing_reference_not_verified_fix")
    for url in links:
        github_path(url, "pull")
    pulls = []
    for url in list(links)[:3]:
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
                      "relation": links[url], "files": patches,
                      "files_truncated": pr["changed_files"] > len(files)})
    comments = []
    for comment in issue["comments"]["nodes"]:
        body = comment["body"]
        comments.append({**comment, "body": body[:1000], "body_truncated": len(body) > 1000})
    return {"fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "selection": "current closing event, then explicit closing references; latest 8 comments",
            "pulls_truncated": refs["totalCount"] > len(refs["nodes"]) or len(links) > 3,
            "pulls": pulls, "comments": comments,
            "comments_total": issue["comments"]["totalCount"],
            "comments_truncated": issue["comments"]["totalCount"] > len(comments)}


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
