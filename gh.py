"""GitHub REST API 客户端:仅用标准库,限速感知。

凭据优先级:环境变量 GITHUB_TOKEN > `gh auth token`。
凭据只保存在进程内,不写入日志与任何输出。
"""
import http.client
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
UA = "issue-lens/0.1 (testing-research)"
# Search API 认证后 30 次/分钟,全局保持最小间隔
SEARCH_MIN_INTERVAL = 2.05
_last_search_at = [0.0]


def get_token() -> str:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and tok.strip():
        return tok.strip()
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError("未找到 GitHub 凭据:请设置 GITHUB_TOKEN 或先执行 gh auth login")
    return r.stdout.strip()


class GitHub:
    def __init__(self, token: str | None = None):
        self.token = token or get_token()

    # ---- 内部 ----

    def _request(self, url: str) -> urllib.request.Request:
        return urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": UA,
        })

    def _throttle_search(self) -> None:
        wait = SEARCH_MIN_INTERVAL - (time.monotonic() - _last_search_at[0])
        if wait > 0:
            time.sleep(wait)
        _last_search_at[0] = time.monotonic()

    def get(self, path: str, params: dict | None = None, _retry: int = 0) -> dict:
        url = f"{API}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        if path.startswith("/search"):
            self._throttle_search()
        try:
            with urllib.request.urlopen(self._request(url), timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 限速与瞬断重试;4xx 语义错误(如 404/422)直接抛出
            if e.code in (403, 429) and _retry < 5:
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    time.sleep(int(retry_after) + 1)
                else:
                    reset = e.headers.get("X-RateLimit-Reset")
                    time.sleep(max(1.0, float(reset) - time.time()) + 1 if reset else 5.0)
                return self.get(path, params, _retry + 1)
            if 500 <= e.code < 600 and _retry < 3:
                time.sleep(2 * (_retry + 1))
                return self.get(path, params, _retry + 1)
            raise
        except (http.client.HTTPException, OSError):
            # 网络瞬断与响应截断(IncompleteRead/ConnectionReset/超时等):退避重试。
            # 注:URLError 继承自 OSError,已包含在内。
            if _retry < 3:
                time.sleep(2 * (_retry + 1))
                return self.get(path, params, _retry + 1)
            raise

    # ---- 业务封装 ----

    def search_repositories(self, query: str, per_page: int = 100) -> tuple[list, int]:
        """单页仓库搜索(每形态只需头部仓库,100 条足够)。"""
        data = self.get("/search/repositories", {
            "q": query, "sort": "stars", "order": "desc", "per_page": per_page, "page": 1,
        })
        return data.get("items", []), data.get("total_count", 0)

    def search_issues(self, query: str, max_results: int = 1000,
                      sort: str = "reactions", order: str = "desc") -> tuple[list, int]:
        """issue 搜索,自动翻页(Search API 硬顶 1000 条/查询)。

        返回 (items, total_count)。total > len(items) 即发生截断,调用方须记录。
        """
        out: list = []
        page, total = 1, 0
        while len(out) < max_results and page <= 10:
            data = self.get("/search/issues", {
                "q": query, "sort": sort, "order": order,
                "per_page": 100, "page": page,
            })
            total = data.get("total_count", 0)
            items = data.get("items", [])
            out.extend(items)
            if len(items) < 100:
                break
            page += 1
        return out[:max_results], total
