# ShopifySift

GitHub code scraper for finding tech-stack mentions, brand references, and other public-metadata leads. Pairs a Python scraper with a Flask dashboard.

> Searches public code only. Not a credential harvester.

## Layout

```
scraper.py          # CLI scraper, reads config.json + queries
dashboard.py        # Flask UI (login-gated)
config.json         # queries, path filters, proxy settings
proxies.txt         # one proxy per line (gitignored)
templates/          # login + dashboard HTML
```

## Quick start

```powershell
# 1. install
pip install -r requirements.txt

# 2. configure
copy .env.example .env
# edit .env and set GITHUB_TOKEN + dashboard creds

# 3. (optional) edit config.json to change what you're searching for
# 4. (optional) paste residential proxies into proxies.txt

# 5. run scraper directly...
python scraper.py "myshopify.com" "powered by stripe"

# ...or run the dashboard
python dashboard.py --port 3010
# open http://127.0.0.1:3010
```

## Config

Edit `config.json` to change what's searched:

```json
{
  "queries": ["\"myshopify.com\"", "\"powered by shopify\""],
  "path_filters": [".env", "config", "readme"],
  "proxies_file": "proxies.txt"
}
```

GitHub code-search dorks work in queries: `filename:`, `extension:`, `language:`, `path:`, `repo:`, `org:`.

## Proxies

`proxies.txt` accepts `http://user:pass@host:port`, `host:port:user:pass`, or `host:port`. The scraper rotates round-robin per request. Note: GitHub rate-limits per **token**, not IP — proxies help with network-level blocking only.

## Auth

The dashboard reads credentials from env vars:
- `SHOPIFYSIFT_USER` (default: `admin`)
- `SHOPIFYSIFT_PASS` (default: `admin` — change this!)
- `SHOPIFYSIFT_SECRET` — long random hex for session signing

OAuth buttons (Google/GitHub/Microsoft) are styled but not wired.

## Known limitations

- Flask dev server, not production-ready (use waitress/gunicorn behind a reverse proxy for hosting).
- Single shared GitHub token — multi-user setups will rate-limit.
- Scraper runs synchronously inside the dashboard request; long jobs block.
- Not deployable to Vercel as-is (subprocess + filesystem writes don't fit the serverless model).
