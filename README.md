# ShopifySift

GitHub code-search lead-gen tool. Two parts:

- **`web/`** — Next.js 16 dashboard, deploys to **Vercel**.
- **`worker/`** — Python scraper that hits the GitHub API. Run locally (or on Railway/Fly later); writes results that the web app reads.

> Searches public code only. Not a credential harvester.

## Layout

```
shopifysift/
├── web/                    # Next.js — Vercel deployment target
│   ├── src/app/            # routes (login, dashboard, /api/login, /api/logout, /api/rows)
│   ├── src/lib/            # auth, results loader
│   ├── src/components/     # ResultsTable
│   ├── data/results.json   # populated by the scraper, read by the dashboard
│   └── .env.example
└── worker/                 # Python scraper
    ├── scraper.py          # CLI scraper
    ├── config.json         # queries, path filters, proxy settings
    ├── proxies.txt         # gitignored — paste your residential proxies
    └── requirements.txt
```

## Deploy to Vercel

1. Connect this repo to Vercel.
2. **Root Directory:** `web` (Project Settings → General).
3. Add env vars (Project Settings → Environment Variables):
   - `SHOPIFYSIFT_USER`
   - `SHOPIFYSIFT_PASS`
   - `SHOPIFYSIFT_SECRET` — at least 32 chars; generate with `python -c "import secrets; print(secrets.token_hex(32))"`
4. Deploy.

Each scraper run produces fresh `web/data/results.json`; commit and push to redeploy with new data.

## Local dev — web

```powershell
cd web
copy .env.example .env.local
# edit .env.local
npm install
npm run dev   # http://localhost:3000
```

## Local dev — scraper

```powershell
cd worker
pip install -r requirements.txt
$env:GITHUB_TOKEN = "ghp_xxx"
python scraper.py "myshopify.com" "powered by stripe"
```

`config.json` controls queries, path filters, and proxy file location. GitHub code-search dorks (`filename:`, `extension:`, `language:`, `path:`, `repo:`, `org:`) work in queries.

The scraper currently writes `results.csv`; convert to `web/data/results.json` (e.g. with `python -c "import csv,json,sys; print(json.dumps([dict(r) for r in csv.DictReader(open('worker/results.csv'))]))" > web/data/results.json`) before committing.

## Auth

Single-user shim — credentials in env vars, JWT-signed cookie. Real auth (Supabase, OAuth) comes next.
