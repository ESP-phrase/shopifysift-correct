# gh-scraper

Browser-based GitHub repository scraper with a small Flask dashboard.

Searches `github.com/search?type=repositories` using a real Chromium (Playwright + stealth), rotating proxies and randomizing browser fingerprints. Submitted searches run in a background thread and stream results into a SQLite-backed dashboard.

## What it does

- Login-gated dashboard (single-user via env vars)
- Submit a keyword search; the scraper opens a real browser, types the query into GitHub's search box, switches to the Repositories tab, and paginates with click-throughs
- Results stream live into a table — repo, description, language, stars, last updated
- Optional proxy rotation per job
- Persists everything in a local SQLite file (`scraper.db`)

## Quick start

```powershell
# 1. install
pip install -r requirements.txt
playwright install chromium

# 2. configure
copy .env.example .env
# edit .env: set DASH_USER, DASH_PASS, and a 64-char SECRET_KEY

# 3. run
python app.py
# open http://127.0.0.1:8000
```

For production, use waitress instead of the dev server:

```powershell
waitress-serve --host=0.0.0.0 --port=8000 app:app
```

## Layout

```
gh-scraper/
├── app.py            # Flask app — routes, auth, jobs, DB
├── scraper.py        # Playwright scraper — async, callable from app
├── templates/
│   ├── login.html
│   └── dashboard.html
├── static/
│   └── style.css
├── requirements.txt
├── .env.example
└── proxies.txt       # (optional, gitignored)
```

## Proxies

Set `PROXIES_FILE=proxies.txt` in `.env` and create `proxies.txt` with one proxy per line:

```
http://user:pass@host:port
host:port:user:pass
host:port
```

The scraper picks one per job (round-robin across the process lifetime).

## Env vars

| Name | Required | Default | Notes |
|---|---|---|---|
| `SECRET_KEY` | yes | — | 64-char hex; signs session cookies |
| `DASH_USER` | no | `admin` | dashboard username |
| `DASH_PASS` | no | `admin` | **change this** before public exposure |
| `PROXIES_FILE` | no | (none) | path to proxy list |
| `PORT` | no | `8000` | dev server port |

Generate a `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

## Notes / limitations

- Anonymous browser scraping; no GitHub login. Hits a real-browser rate limit faster than the API does — proxies help with the network-level cap.
- Synchronous Playwright instance per job. Concurrent jobs share the OS but each spawns its own Chromium — be mindful on small machines.
- Flask dev server isn't production-grade. Use `waitress` (already in requirements) behind a reverse proxy if you expose this externally.
