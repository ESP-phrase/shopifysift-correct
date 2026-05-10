"""
GitHub code scraper — searches public code for keywords/phrases (tech stack
indicators, brand mentions, domains, etc). Not for credential harvesting.

Configuration priority (later overrides earlier):
  1. config.json next to this script
  2. --config PATH
  3. CLI args (queries, --path-filter, --no-path-filter, -o)

Usage:
    set GITHUB_TOKEN=ghp_xxx
    python scraper.py
    python scraper.py "powered by shopify" "stripe language:python"
    python scraper.py --config my-config.json
    python scraper.py --no-path-filter "myshopify.com"
"""

import argparse
import csv
import itertools
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests


HERE = Path(__file__).parent
DEFAULT_CONFIG = HERE / "config.json"


# ---- config loading --------------------------------------------------------

def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"error: config file not found: {path}")
        sys.exit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}")
        sys.exit(2)


def normalize_proxy(line: str) -> str | None:
    """Accept several common proxy formats; return a requests-compatible URL."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "://" in line:
        return line
    parts = line.split(":")
    if len(parts) == 4:
        host, port, user, pwd = parts
        return f"http://{user}:{pwd}@{host}:{port}"
    if len(parts) == 2:
        host, port = parts
        return f"http://{host}:{port}"
    print(f"  [warn] unrecognized proxy format: {line!r}")
    return None


def load_proxies(cfg: dict) -> list[str]:
    proxies: list[str] = []
    inline = cfg.get("proxies") or []
    for p in inline:
        n = normalize_proxy(p)
        if n:
            proxies.append(n)

    pfile = cfg.get("proxies_file")
    if pfile:
        path = Path(pfile)
        if not path.is_absolute():
            path = HERE / path
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                n = normalize_proxy(raw)
                if n:
                    proxies.append(n)
    return proxies


# ---- core ------------------------------------------------------------------

@dataclass(frozen=True)
class Hit:
    query: str
    repo: str
    path: str
    url: str
    repo_url: str


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gh-keyword-scraper",
    }


class Client:
    def __init__(self, token: str, proxies: list[str]):
        self.headers = _headers(token)
        self.session = requests.Session()
        self._proxy_cycle = itertools.cycle(proxies) if proxies else None
        self.proxies_enabled = bool(proxies)

    def _next_proxies(self) -> dict | None:
        if not self._proxy_cycle:
            return None
        url = next(self._proxy_cycle)
        return {"http": url, "https": url}

    def get(self, url: str, params: dict | None = None) -> dict | None:
        for attempt in range(4):
            try:
                r = self.session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    proxies=self._next_proxies(),
                    timeout=30,
                )
            except requests.RequestException as e:
                print(f"  [net] {e}; retry {attempt + 1}")
                time.sleep(5 * (attempt + 1))
                continue

            if r.status_code == 200:
                return r.json()

            if r.status_code in (403, 429):
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    wait = int(retry_after)
                elif r.headers.get("X-RateLimit-Remaining") == "0":
                    reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                    wait = max(5, reset - int(time.time()))
                else:
                    wait = 30 * (attempt + 1)
                print(f"  [rate-limit] sleeping {wait}s (status {r.status_code})")
                time.sleep(min(wait, 120))
                continue

            if r.status_code == 422:
                print(f"  [skip] unprocessable query: {r.json().get('message')}")
                return None

            print(f"  [error] {r.status_code}: {r.text[:200]}")
            return None

        print("  [error] exhausted retries")
        return None


def search(client: Client, query: str, per_page: int, max_pages: int) -> Iterable[Hit]:
    for page in range(1, max_pages + 1):
        data = client.get(
            "https://api.github.com/search/code",
            params={"q": query, "per_page": per_page, "page": page},
        )
        if not data:
            return
        items = data.get("items", [])
        if not items:
            return
        for item in items:
            repo = item["repository"]
            yield Hit(
                query=query,
                repo=repo["full_name"],
                path=item["path"],
                url=item["html_url"],
                repo_url=repo["html_url"],
            )
        if len(items) < per_page:
            return


def make_keeper(filters: list[str] | None):
    if not filters:
        return lambda _hit: True
    lowered = [f.lower() for f in filters]
    return lambda hit: any(f in hit.path.lower() for f in lowered)


# ---- cli -------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GitHub code keyword scraper")
    p.add_argument("queries", nargs="*", help="search queries (overrides config)")
    p.add_argument("--config", default=str(DEFAULT_CONFIG), help="config.json path")
    p.add_argument("--path-filter", help="comma-separated path substrings to keep")
    p.add_argument("--no-path-filter", action="store_true", help="keep all paths")
    p.add_argument("-o", "--output", help="output CSV path (overrides config)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: set GITHUB_TOKEN environment variable")
        return 1

    cfg = load_config(Path(args.config))

    queries = args.queries or cfg.get("queries") or []
    if not queries:
        print("error: no queries — add some to config.json or pass as args")
        return 2

    if args.no_path_filter:
        filters = None
    elif args.path_filter:
        filters = [s.strip() for s in args.path_filter.split(",") if s.strip()]
    else:
        filters = cfg.get("path_filters") or None
    keep = make_keeper(filters)

    output = args.output or cfg.get("output", "results.csv")
    per_page = int(cfg.get("per_page", 50))
    max_pages = int(cfg.get("max_pages_per_query", 4))
    sleep_between = float(cfg.get("sleep_between_queries", 4))

    proxies = load_proxies(cfg)

    print(f"queries: {len(queries)}")
    print(f"path filter: {filters if filters else 'none'}")
    print(f"proxies: {len(proxies)} loaded" if proxies else "proxies: none (direct)")
    print(f"output: {output}")

    client = Client(token, proxies)
    seen: set[tuple[str, str]] = set()
    rows: list[Hit] = []

    for query in queries:
        print(f"\n[+] {query}")
        count = 0
        for hit in search(client, query, per_page, max_pages):
            key = (hit.repo, hit.path)
            if key in seen:
                continue
            seen.add(key)
            if not keep(hit):
                continue
            rows.append(hit)
            count += 1
            print(f"    {hit.repo}  {hit.path}")
        print(f"  -> {count} kept")
        time.sleep(sleep_between)

    with open(output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["query", "repo", "path", "url", "repo_url"])
        for h in rows:
            w.writerow([h.query, h.repo, h.path, h.url, h.repo_url])

    print(f"\nwrote {len(rows)} rows to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
