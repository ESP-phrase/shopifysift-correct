"""
Browser-based GitHub repository scraper using Playwright + stealth.

Searches https://github.com/search?type=repositories with a real Chromium,
rotating proxies and randomizing fingerprints. Designed to be called from
the Flask app as a background task.

Public entrypoint:
    scrape(query, max_pages=3, on_result=callback) -> int  (count of results)
"""

from __future__ import annotations

import asyncio
import itertools
import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth


HERE = Path(__file__).parent


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
]
LOCALES = ["en-US", "en-GB", "en-CA", "en-AU"]
TIMEZONES = ["America/New_York", "America/Chicago", "America/Los_Angeles", "Europe/London"]


# ---- model -----------------------------------------------------------------

@dataclass
class Repo:
    full_name: str
    url: str
    description: str | None
    language: str | None
    stars: int | None
    updated: str | None


# ---- proxy loading ---------------------------------------------------------

def _normalize_proxy(line: str) -> dict | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    user = pwd = None
    if "://" in line:
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
            return None

    proxy: dict = {"server": server}
    if user:
        proxy["username"] = user
    if pwd:
        proxy["password"] = pwd
    return proxy


def load_proxies() -> list[dict]:
    path_str = os.environ.get("PROXIES_FILE")
    if not path_str:
        return []
    path = Path(path_str)
    if not path.is_absolute():
        path = HERE / path
    if not path.exists():
        return []
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        n = _normalize_proxy(raw)
        if n:
            out.append(n)
    return out


# ---- human-like behavior ---------------------------------------------------

async def _human_pause(min_s: float = 1.0, max_s: float = 2.5) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


async def _human_mouse_move(page: Page) -> None:
    vp = page.viewport_size or {"width": 1280, "height": 800}
    x = random.randint(50, vp["width"] - 50)
    y = random.randint(50, vp["height"] - 50)
    await page.mouse.move(x, y, steps=random.randint(15, 40))


async def _human_scroll(page: Page) -> None:
    for _ in range(random.randint(3, 6)):
        await page.mouse.wheel(0, random.randint(200, 600))
        await asyncio.sleep(random.uniform(0.4, 1.2))
    if random.random() < 0.3:
        await page.mouse.wheel(0, -random.randint(150, 400))
        await asyncio.sleep(random.uniform(0.3, 0.8))


async def _human_type(page: Page, selector: str, text: str) -> None:
    el = await page.wait_for_selector(selector, timeout=10_000)
    await el.click()
    await asyncio.sleep(random.uniform(0.2, 0.5))
    for ch in text:
        await page.keyboard.type(ch, delay=random.randint(60, 180))
        if random.random() < 0.04:
            await asyncio.sleep(random.uniform(0.3, 0.9))


async def _submit_search(page: Page, query: str) -> bool:
    try:
        await page.keyboard.press("/")
        await _human_pause(0.4, 1.0)
        for sel in [
            "#query-builder-test",
            'input[aria-label="Search GitHub"]',
            'input[name="q"]',
            'input[placeholder*="Search" i]',
        ]:
            try:
                if await page.wait_for_selector(sel, timeout=2_500):
                    await _human_type(page, sel, query)
                    await _human_pause(0.3, 0.8)
                    await page.keyboard.press("Enter")
                    await page.wait_for_load_state("domcontentloaded", timeout=30_000)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# ---- parsing ---------------------------------------------------------------

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
    s = m.group(2).lower()
    if s == "k":
        n *= 1_000
    elif s == "m":
        n *= 1_000_000
    return int(n)


async def _parse_results(page: Page) -> list[Repo]:
    items = await page.evaluate(
        """() => {
            const out = [];
            const headings = document.querySelectorAll(
                'div[data-testid="results-list"] h3 a, [data-testid="results-list"] a[href^="/"]'
            );
            const seen = new Set();
            for (const a of headings) {
                const href = a.getAttribute('href') || '';
                const m = href.match(/^\\/([^/]+)\\/([^/?#]+)$/);
                if (!m) continue;
                const full = m[1] + '/' + m[2];
                if (seen.has(full)) continue;
                seen.add(full);

                let card = a.closest('div.Box-row, div[data-testid="results-list"] > div, li');
                if (!card) card = a.parentElement?.parentElement?.parentElement;

                let desc = null;
                if (card) {
                    const p = card.querySelector('p, [class*="description"]');
                    if (p) desc = p.innerText.trim();
                }
                let lang = null;
                if (card) {
                    const langEl = card.querySelector('[itemprop="programmingLanguage"], span[aria-label*="language"]');
                    if (langEl) lang = langEl.innerText.trim();
                }
                let starsText = null;
                if (card) {
                    const starEl = card.querySelector('a[href$="/stargazers"], a[href*="/stargazers"]');
                    if (starEl) starsText = starEl.innerText.trim();
                }
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
            full_name=it["full_name"],
            url=it["url"],
            description=it.get("description"),
            language=it.get("language"),
            stars=_parse_int(it.get("stars_text")),
            updated=it.get("updated"),
        )
        for it in items
    ]


# ---- scraping flow ---------------------------------------------------------

async def _new_context(browser: Browser, proxy: dict | None) -> BrowserContext:
    locale = random.choice(LOCALES)
    return await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport=random.choice(VIEWPORTS),
        locale=locale,
        timezone_id=random.choice(TIMEZONES),
        proxy=proxy,
        java_script_enabled=True,
        extra_http_headers={
            "Accept-Language": f"{locale},{locale.split('-')[0]};q=0.9",
        },
        device_scale_factor=random.choice([1, 1, 1, 2]),
        color_scheme=random.choice(["light", "light", "dark"]),
    )


async def _click_next(page: Page) -> bool:
    try:
        nxt = await page.query_selector('a[rel="next"], a:has-text("Next")')
        if not nxt:
            return False
        disabled = await nxt.evaluate(
            "el => el.tagName !== 'A' || el.getAttribute('aria-disabled') === 'true'"
        )
        if disabled:
            return False
        await _human_mouse_move(page)
        await _human_pause(0.4, 1.0)
        await nxt.click()
        await page.wait_for_load_state("domcontentloaded", timeout=30_000)
        return True
    except Exception:
        return False


async def _go_to_results(page: Page, query: str) -> None:
    if await _submit_search(page, query):
        if "type=repositories" not in page.url:
            try:
                tab = await page.wait_for_selector(
                    'a[href*="type=repositories"], nav a:has-text("Repositories")',
                    timeout=8_000,
                )
                await _human_mouse_move(page)
                await _human_pause(0.3, 0.8)
                await tab.click()
                await page.wait_for_load_state("domcontentloaded", timeout=30_000)
                return
            except Exception:
                pass
    # Fallback: direct URL.
    url = f"https://github.com/search?q={quote_plus(query)}&type=repositories"
    await page.goto(url, wait_until="domcontentloaded", timeout=45_000)


async def _scrape_async(
    query: str,
    max_pages: int,
    headless: bool,
    on_result: Callable[[Repo], None] | None,
) -> int:
    proxies = load_proxies()
    proxy_cycle = itertools.cycle(proxies) if proxies else None
    seen: set[str] = set()
    count = 0

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
        proxy = next(proxy_cycle) if proxy_cycle else None
        ctx = await _new_context(browser, proxy)
        await stealth.apply_stealth_async(ctx)
        page = await ctx.new_page()

        try:
            await page.goto("https://github.com/", wait_until="domcontentloaded", timeout=45_000)
            await _human_pause(1.0, 2.0)
            await _human_mouse_move(page)
            await _human_scroll(page)

            await _go_to_results(page, query)

            for page_num in range(1, max_pages + 1):
                try:
                    await page.wait_for_selector(
                        'div[data-testid="results-list"], div[data-testid="empty-results"]',
                        timeout=20_000,
                    )
                except Exception:
                    debug = HERE / f"debug_{int(time.time())}.html"
                    debug.write_text(await page.content(), encoding="utf-8")
                    break

                await _human_pause(0.6, 1.4)
                await _human_mouse_move(page)
                await _human_scroll(page)

                results = await _parse_results(page)
                if not results:
                    break

                new_on_page = 0
                for r in results:
                    if r.full_name in seen:
                        continue
                    seen.add(r.full_name)
                    if on_result:
                        on_result(r)
                    count += 1
                    new_on_page += 1

                if new_on_page == 0 or page_num >= max_pages:
                    break
                await _human_pause(2.0, 4.0)
                if not await _click_next(page):
                    break
        finally:
            await ctx.close()
            await browser.close()

    return count


def scrape(
    query: str,
    max_pages: int = 3,
    headless: bool = True,
    on_result: Callable[[Repo], None] | None = None,
) -> int:
    """Sync wrapper — runs the async scraper in a fresh event loop."""
    return asyncio.run(_scrape_async(query, max_pages, headless, on_result))
