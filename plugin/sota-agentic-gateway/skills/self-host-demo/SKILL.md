---
name: self-host-demo
description: Run a local demo of the SOTA Agentic Gateway SaaS (FastAPI API + Next.js web app) on SQLite, without Docker or Postgres, and create a demo workspace. Use when the user has the SOTA Agentic Gateway source code (self-host / source license) and asks to run, start, try or demo the platform on localhost.
---

# Local demo of the SOTA Agentic Gateway SaaS (SQLite)

**Needs the source checkout** of SOTA Agentic Gateway (its `saas/` folder holds `app/saas/`, `web/`, `pyproject.toml`) — it comes
with a self-host / source license, not with this plugin. If the user has no checkout, say so and point them to the hosted
web app (plugin setting `api_url`) instead. Do not try to download the source yourself.

This is a **demo only**: SQLite file, no migrations, no background worker, billing off. For production self-hosting
use Postgres + `alembic upgrade head` as in the repo's `README.md` / `docs/saas/`.

## Safety

- Never point `DATABASE_URL` at an existing or production database. Use a new file in a scratch/temp folder.
- Pass settings as environment variables of the commands. Do not create or edit `.env` in the repo.
- Keep `INGESTION_ENABLED=false AGENT_WORKER_ENABLED=false` (they start the single-tenant workers).
- The demo password below is for localhost only; tell the user not to reuse it.

## Steps

Requirements: Python 3.12 + `uv`, Node 20+ with `npm`. Ports 8000 (API) and 3000 (web) must be free.
Let `REPO` be the **`saas/` folder** of the checkout (the folder that holds `pyproject.toml` and `app/saas/`; older
checkouts have these at the top level — then `REPO` is the checkout itself) and `DB` a new file such as `<temp>/agw_demo.db`.

1. Install dependencies (can run in parallel): `uv sync` in `REPO`, and `npm install` in `REPO/web`.
2. Create the tables with the helper next to this file:
   `uv run --project REPO python -X utf8 <this skill folder>/init_sqlite.py REPO DB` → prints `ok: N tables`.
3. Start the API **in the background** from `REPO`:
   - bash: `PYTHONPATH=$PWD DATABASE_URL="sqlite:///DB" INGESTION_ENABLED=false AGENT_WORKER_ENABLED=false SAAS_BILLING_ENABLED=false SAAS_CORS_ORIGINS=http://localhost:3000 SAAS_WEB_URL=http://localhost:3000 uv run uvicorn app.saas.server:app --port 8000`
   - PowerShell: set the same variables with `$env:NAME = "value"` first, then the same `uv run uvicorn …`.
   - On Windows write `DB` with forward slashes, e.g. `sqlite:///C:/Temp/agw_demo.db`.
   - The entry point is `app.saas.server:app` (not `app.main`).
4. Start the web app **in the background** from `REPO/web`: `AGW_API_URL=http://localhost:8000 AGW_COOKIE_SECURE=false npm run dev`.
5. Wait until `http://localhost:8000/docs` and `http://localhost:3000` both answer 200 (poll; do not sleep blindly).
6. Create the demo workspace through the web route (it sets httpOnly cookies, the token never reaches page JS):
   `POST http://localhost:3000/api/auth/signup` with JSON
   `{"email":"demo@example.com","password":"Demo@12345","full_name":"Demo User","workspace_name":"Demo Workspace","account_type":"business","industry_pack":"logistics"}`.
   If the email already exists, log in instead with `POST /api/auth/login` `{"email","password"}`.
7. Check it really works: log in with a cookie jar, then `GET http://localhost:3000/inbox` → 200 and
   `GET http://localhost:3000/api/bff/approvals` → `[]`.

## Report to the user

- Web: http://localhost:3000 · API docs: http://localhost:8000/docs · the demo email + password.
- What is not set up: no LLM key (BYOK), no mailbox/chat connection, no background jobs — inbox and AI stay empty until
  the user adds a model in **Cài đặt → Model** and a connection in **Kết nối** in the web app.
- How to stop: stop the two background processes. Deleting `DB` resets the demo.

## Common problems

- `ModuleNotFoundError: app` → run from `REPO` with `PYTHONPATH` set to `REPO`.
- Port already in use → another server is running; ask before stopping it, or use `--port` / `next dev -p` and
  update `AGW_API_URL`, `SAAS_CORS_ORIGINS`, `SAAS_WEB_URL` to match.
- Web shows login errors → the API is not up yet or `AGW_API_URL` is wrong.
