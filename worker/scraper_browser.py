"""
Browser-based GitHub repository scraper using Playwright + stealth.

Searches https://github.com/search?type=repositories with a real Chromium,
rotating proxies and randomizing fingerprints. Writes JSONL output.

Setup:
    pip install -r requirements.txt
    playwright install chromium

Usage:
    python scraper_browser.py "shopify app"
    python scraper_browser.py "stripe webhook" "discord bot" --max-pages 3
    python scraper_browser.py --config config.json
    python scraper_browser.py "react dashboard" --headed   # debug visually
"""

import argparse
import asyncio
import itertools
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth


HERE = Path(__file__).parent
DEFAULT_CONFIG = HERE / "config.json"
DEFAULT_OUTPUT = HERE / "repos.jsonl"
STATE_FILE = HERE / ".scraper_browser_state.json"


# Realistic UA strings — recent Chrome versions on Win/Mac/Linux desktop.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1680, "height": 1050},
]

LOCALES = ["en-US", "en-GB", "en-CA", "en-AU"]
TIMEZONES = ["America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/London", "Europe/Berlin"]


# ---- proxy + config --------------------------------------------------------

def normalize_proxy(line: str) -> dict | None:
    """Return Playwright-style proxy dict, or None to skip."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    user = pwd = None
    server = line

    if "://" in line:
        # http://user:pass@host:port
        scheme, rest = line.split("://", 1)
        if "@" in rest:
            creds, hostport = rest.rsplit("@", 1)
            if ":" in creds:
                user, pwd = creds.split(":", 1)
            server = f"{scheme}://{hostport}"
        else:
            server = line
    else:
        parts = line.split(":")
        if len(parts) == 4:
            host, port, user, pwd = parts
            server = f"http://{host}:{port}"
        elif len(parts) == 2:
            server = f"http://{line}"
        else:
            print(f"  [warn] unrecognized proxy format: {line!r}")
            return None

    proxy: dict = {"server": server}
    if user:
        proxy["username"] = user
    if pwd:
        proxy["password"] = pwd
    return proxy


def load_proxies(cfg: dict) -> list[dict]:
    proxies: list[dict] = []
    for p in cfg.get("proxies") or []:
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


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON in {path}: {e}")
        sys.exit(2)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---- model -----------------------------------------------------------------

@dataclass
class Repo:
    query: str
    full_name: str
    url: str
    description: str | None
    language: str | None
    stars: int | None
    updated: str | None


# ---- scraping --------------------------------------------------------------

async def new_context(browser: Browser, proxy: dict | None) -> BrowserContext:
    """Build a context with randomized fingerprint. Proxy is set per-context."""
    locale = random.choice(LOCALES)
    return await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport=random.choice(VIEWPORTS),
        locale=locale,
        timezone_id=random.choice(TIMEZONES),
        proxy=proxy,
        java_script_enabled=True,
        # Match Accept-Language to locale so headers don't betray us.
        extra_http_headers={
            "Accept-Language": f"{locale},{locale.split('-')[0]};q=0.9",
        },
        # Slight color/scale variance — common real-world values.
        device_scale_factor=random.choice([1, 1, 1, 2]),
        color_scheme=random.choice(["light", "light", "dark"]),
    )


async def human_pause(min_s: float = 1.5, max_s: float = 4.0) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


# ---- human-like interactions ----------------------------------------------

async def human_mouse_move(page: Page, steps: int = 0) -> None:
    """Drift the mouse to a random point in small increments."""
    vp = page.viewport_size or {"width": 1280, "height": 800}
    target_x = random.randint(50, vp["width"] - 50)
    target_y = random.randint(50, vp["height"] - 50)
    # `steps` argument to mouse.move smooths the path; randomize so timing varies.
    await page.mouse.move(target_x, target_y, steps=steps or random.randint(15, 40))


async def human_scroll(page: Page) -> None:
    """Scroll down in 3–6 chunks with reading pauses, sometimes scroll back up."""
    chunks = random.randint(3, 6)
    for _ in range(chunks):
        delta = random.randint(200, 600)
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.4, 1.4))
    # Occasionally scroll back up — humans skim, lose place, re-read.
    if random.random() < 0.3:
        await page.mouse.wheel(0, -random.randint(150, 400))
        await asyncio.sleep(random.uniform(0.3, 0.9))


async def human_type(page: Page, selector: str, text: str) -> None:
    """Type with per-character delay; occasionally pause longer (thinking)."""
    el = await page.wait_for_selector(selector, timeout=10_000)
    await el.click()
    await asyncio.sleep(random.uniform(0.2, 0.6))
    for ch in text:
        await page.keyboard.type(ch, delay=random.randint(60, 180))
        if random.random() < 0.04:  # ~4% chance of a "thinking" pause
            await asyncio.sleep(random.uniform(0.3, 0.9))


async def submit_search(page: Page, query: str) -> bool:
    """Type the query into GitHub's header search box and submit. Returns True on success."""
    # GitHub's header has a button that opens the search modal in newer UIs,
    # or an inline input in older ones. Try the modal flow first.
    try:
        # Open the search dialog (the "/" shortcut works on github.com).
        await page.keyboard.press("/")
        await asyncio.sleep(random.uniform(0.4, 1.0))

        # Modal input (newer UI) or header input (older UI).
        selectors = [
            '#query-builder-test',                       # newer search modal
            'input[aria-label="Search GitHub"]',          # legacy header
            'input[name="q"]',                            # fallback
            'input[placeholder*="Search" i]',
        ]
        target = None
        for sel in selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=2_500)
                if el:
                    target = sel
                    break
            except Exception:
                continue
        if not target:
            return False

        await human_type(page, target, query)
        await asyncio.sleep(random.uniform(0.3, 0.8))
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("domcontentloaded", timeout=30_000)
        return True
    except Exception as e:
        print(f"  [warn] typed search failed ({e}); falling back to URL")
        return False


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([kKmM]?)$", text)
    if not m:
        try:
            return int(text)
        except ValueError:
            return None
    n = float(m.group(1))
    suffix = m.group(2).lower()
    if suffix == "k":
        n *= 1_000
    elif suffix == "m":
        n *= 1_000_000
    return int(n)


async def parse_results(page: Page, query: str) -> list[Repo]:
    """Parse the current /search?type=repositories page. Resilient to GitHub UI churn."""
    items = await page.evaluate(
        """() => {
            const out = [];
            // Each repo card has a heading link to /<owner>/<repo>
            const headings = document.querySelectorAll('div[data-testid="results-list"] h3 a, .search-title a, [data-testid="results-list"] a[href^="/"]');
            const seen = new Set();
            for (const a of headings) {
                const href = a.getAttribute('href') || '';
                // Match owner/repo, no extra path
                const m = href.match(/^\\/([^/]+)\\/([^/?#]+)$/);
                if (!m) continue;
                const full = m[1] + '/' + m[2];
                if (seen.has(full)) continue;
                seen.add(full);

                // Walk up to the result card to grab metadata
                let card = a.closest('div.Box-row, div[data-testid="results-list"] > div, li');
                if (!card) card = a.parentElement?.parentElement?.parentElement;
                const cardText = card ? card.innerText : '';

                // Description: usually first <p> in card, or element with class containing 'description'
                let desc = null;
                if (card) {
                    const p = card.querySelector('p, [class*="description"]');
                    if (p) desc = p.innerText.trim();
                }

                // Language: span next to a circle swatch, or [itemprop="programmingLanguage"]
                let lang = null;
                if (card) {
                    const langEl = card.querySelector('[itemprop="programmingLanguage"], span[aria-label*="language"]');
                    if (langEl) lang = langEl.innerText.trim();
                }

                // Stars: link ending with /stargazers, or aria-label like "stars"
                let starsText = null;
                if (card) {
                    const starEl = card.querySelector('a[href$="/stargazers"], a[href*="/stargazers"]');
                    if (starEl) starsText = starEl.innerText.trim();
                }

                // Updated time: <relative-time> element
                let updated = null;
                if (card) {
                    const t = card.querySelector('relative-time, time-ago, time');
                    if (t) updated = t.getAttribute('datetime') || t.innerText.trim();
                }

                out.push({
                    full_name: full,
                    url: 'https://github.com' + href,
                    description: desc,
                    language: lang,
                    stars_text: starsText,
                    updated: updated,
                });
            }
            return out;
        }"""
    )

    return [
        Repo(
            query=query,
            full_name=it["full_name"],
            url=it["url"],
            description=it.get("description"),
            language=it.get("language"),
            stars=_parse_int(it.get("stars_text")),
            updated=it.get("updated"),
        )
        for it in items
    ]


async def goto_results(page: Page, query: str) -> None:
    """Land on the repositories search results for `query`, preferring the typed flow."""
    typed = await submit_search(page, query)
    if not typed:
        # Fallback: direct navigation (still a valid path, just less human).
        url = f"https://github.com/search?q={quote_plus(query)}&type=repositories"
        await page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        return

    # Typed search lands on type=code by default. Switch to Repositories tab.
    if "type=repositories" not in page.url:
        try:
            tab = await page.wait_for_selector(
                'a[href*="type=repositories"], nav a:has-text("Repositories")',
                timeout=8_000,
            )
            await human_mouse_move(page)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await tab.click()
            await page.wait_for_load_state("domcontentloaded", timeout=30_000)
        except Exception:
            # Tab not found — bail to URL.
            url = f"https://github.com/search?q={quote_plus(query)}&type=repositories"
            await page.goto(url, wait_until="domcontentloaded", timeout=45_000)


async def click_next_page(page: Page) -> bool:
    """Click the pagination 'Next' link. Returns False if not present (end of results)."""
    try:
        # GitHub's pagination uses an <a> with rel="next" or text "Next".
        nxt = await page.query_selector('a[rel="next"], a:has-text("Next")')
        if not nxt:
            return False
        # Some pages render a disabled span instead of a link on the last page.
        is_disabled = await nxt.evaluate("el => el.tagName !== 'A' || el.getAttribute('aria-disabled') === 'true'")
        if is_disabled:
            return False
        await human_mouse_move(page)
        await asyncio.sleep(random.uniform(0.4, 1.1))
        await nxt.click()
        await page.wait_for_load_state("domcontentloaded", timeout=30_000)
        return True
    except Exception as e:
        print(f"  [warn] next-page click failed: {e}")
        return False


async def scrape_query(
    browser: Browser,
    proxy_cycle,
    stealth: Stealth,
    query: str,
    max_pages: int,
    seen: set[str],
) -> list[Repo]:
    results: list[Repo] = []
    proxy = next(proxy_cycle) if proxy_cycle else None
    ctx = await new_context(browser, proxy)
    await stealth.apply_stealth_async(ctx)

    page = await ctx.new_page()

    try:
        # Warm-up: visit homepage, look around briefly. Real users don't deep-link cold.
        await page.goto("https://github.com/", wait_until="domcontentloaded", timeout=45_000)
        await human_pause(1.2, 2.8)
        await human_mouse_move(page)
        await human_scroll(page)
        await human_pause(0.8, 1.8)

        # Type the query into the search box; falls back to URL nav if the input isn't found.
        await goto_results(page, query)

        for page_num in range(1, max_pages + 1):
            print(f"  [page {page_num}] {page.url}")

            try:
                await page.wait_for_selector(
                    'div[data-testid="results-list"], div[data-testid="empty-results"], h3:has-text("We couldn\'t find any")',
                    timeout=20_000,
                )
            except Exception:
                debug = HERE / f"debug_{int(time.time())}.html"
                debug.write_text(await page.content(), encoding="utf-8")
                print(f"  [warn] no results selector; dumped {debug.name}")
                break

            # Skim the page like a human: small mouse move, scroll through results.
            await human_pause(0.8, 1.6)
            await human_mouse_move(page)
            await human_scroll(page)

            page_results = await parse_results(page, query)
            if not page_results:
                print("  [info] no results on page — stopping")
                break

            new = 0
            for r in page_results:
                if r.full_name in seen:
                    continue
                seen.add(r.full_name)
                results.append(r)
                new += 1
                print(f"    {r.full_name}  ★{r.stars or '?'}  [{r.language or '?'}]")
            print(f"  -> {new} new ({len(page_results)} on page)")

            if new == 0:
                break
            if page_num >= max_pages:
                break

            # Reading pause before paginating.
            await human_pause(2.5, 5.0)
            if not await click_next_page(page):
                print("  [info] no next page")
                break
    finally:
        await ctx.close()

    return results


async def run(args, cfg: dict) -> int:
    queries: list[str] = args.queries or cfg.get("queries") or []
    if not queries:
        print("error: no queries — pass as args or add to config.json")
        return 2

    proxies = load_proxies(cfg)
    proxy_cycle = itertools.cycle(proxies) if proxies else None
    max_pages = args.max_pages or int(cfg.get("max_pages_per_query", 3))
    output = Path(args.output or DEFAULT_OUTPUT)

    # CLI --headed wins; otherwise fall back to config; default headless.
    headless = False if args.headed else bool(cfg.get("headless", True))

    print(f"queries: {len(queries)}")
    print(f"proxies: {len(proxies)} loaded" if proxies else "proxies: none (direct)")
    print(f"output: {output}")
    print(f"headless: {headless}")

    state = load_state()
    seen: set[str] = set(state.get("seen", []))

    stealth = Stealth()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Append-mode JSONL: safe to stop and resume.
        with output.open("a", encoding="utf-8") as out:
            for query in queries:
                print(f"\n[+] {query}")
                try:
                    repos = await scrape_query(
                        browser, proxy_cycle, stealth, query, max_pages, seen
                    )
                except Exception as e:
                    print(f"  [error] query failed: {e}")
                    continue

                for r in repos:
                    out.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
                out.flush()

                # Persist state after every query so a crash doesn't lose dedup info.
                state["seen"] = sorted(seen)
                save_state(state)

                await asyncio.sleep(random.uniform(4, 8))

        await browser.close()

    print(f"\ndone. {len(seen)} unique repos in {output}")
    return 0


# ---- cli -------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Browser-based GitHub repo scraper")
    p.add_argument("queries", nargs="*", help="search queries")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--max-pages", type=int, help="pages per query (default: 3)")
    p.add_argument("-o", "--output", help="output JSONL path")
    p.add_argument("--headed", action="store_true", help="show browser window")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(Path(args.config))
    return asyncio.run(run(args, cfg))


if __name__ == "__main__":
    sys.exit(main())
