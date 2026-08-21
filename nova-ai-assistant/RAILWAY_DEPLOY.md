# NOVA Railway Deployment Guide

## Architecture

```
Railway Project
├── nova-backend      (FastAPI — uvicorn)
└── nova-worker       (Celery — browser + task queue)

External Services
├── Supabase          (Postgres + Auth + pgvector)
└── Upstash Redis     (Celery broker + result backend)
```

---

## Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli) installed (`npm i -g @railway/cli`)
- Supabase project created with pgvector enabled
- Upstash Redis database created (free tier works)
- All API keys ready (see `.env.example`)

---

## Step 1 — Run the database migration

Before deploying, run the schema migration against your Supabase Postgres instance.
This creates all tables and the `match_memories` RPC function.

```bash
cd nova-ai-assistant/backend
# Install deps in a venv if you haven't already
pip install psycopg2-binary python-dotenv

# Set DATABASE_URL to your Supabase direct connection string, then:
python -m app.db.migrate
```

Verify output shows all four tables (`users`, `tasks`, `receipts`, `memory_vectors`) created.

---

## Step 2 — Create the Railway project

```bash
cd nova-ai-assistant
railway login
railway init   # create a new project
```

---

## Step 3 — Deploy the FastAPI Backend service

```bash
# From repo root, create the backend service
railway up --service nova-backend --dockerfile backend/Dockerfile
```

Or via the Railway dashboard:
1. New Service → GitHub Repo → select your repo
2. Set **Root Directory** to `/nova-ai-assistant/backend`
3. Railway auto-detects the `Dockerfile`
4. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`

### Backend environment variables (add in Railway dashboard → Variables)

| Variable | Where to get it |
|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_ANON_KEY` | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API |
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string |
| `REDIS_URL` | Upstash Console → Redis → Connect → `rediss://...` |
| `GEMINI_API_KEY` | Google AI Studio |
| `ANTHROPIC_API_KEY` | Anthropic Console |
| `OPENAI_API_KEY` | OpenAI Platform |
| `TAVILY_API_KEY` | Tavily Dashboard |
| `ELEVENLABS_API_KEY` | ElevenLabs Dashboard |
| `ELEVENLABS_VOICE_ID` | ElevenLabs → Voices |
| `ENCRYPTION_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ALLOWED_ORIGINS` | Your frontend Railway URL + any Vercel URL |
| `GROQ_API_KEY` | Groq Console (optional) |

Railway automatically injects `PORT` — do not set it manually.

---

## Step 4 — Deploy the Celery Worker service

```bash
railway up --service nova-worker --dockerfile worker/Dockerfile
```

Or via Railway dashboard:
1. New Service → GitHub Repo → same repo
2. Set **Root Directory** to `/nova-ai-assistant`  
   (worker imports from both `worker/` and `backend/`)
3. Set **Dockerfile Path** to `worker/Dockerfile`
4. Set **Start Command**: `celery -A worker.celery_app worker --loglevel=info --concurrency=${CELERYD_CONCURRENCY:-2}`

### Worker environment variables

The worker needs all the same vars as the backend **plus**:

| Variable | Value |
|---|---|
| `REDIS_URL` | Same Upstash `rediss://` URL as backend |
| `CELERYD_CONCURRENCY` | `2` (increase for heavier workloads) |

> **Tip:** Use Railway's **Shared Variables** feature to define `REDIS_URL`,
> `SUPABASE_*`, and API keys once and reference them in both services.

---

## Step 5 — Verify deployment

### 1. FastAPI starts
```
railway logs --service nova-backend
# Should show:
# [NOVA] Supabase connection: OK
# [NOVA] Application ready.
# Uvicorn running on http://0.0.0.0:<PORT>
```

### 2. Celery worker starts
```
railway logs --service nova-worker
# Should show:
# [config] .> app:         nova_worker
# [queues] .> celery       exchange=celery(direct)
# [tasks]  . browser.fetch_page_content
#          . worker.tasks.ping
# [2024-xx] celery@... ready.
```

### 3. Redis connection works
```bash
# Hit the ping task via curl (replace with your Railway backend URL)
curl https://your-backend.up.railway.app/health
# Expected: {"status":"ok","service":"nova-backend","database":"connected"}
```

### 4. Database connection works
The `/health` endpoint calls `check_supabase_connection()` — a `"connected"` response
confirms Supabase is reachable.

### 5. Frontend can communicate with backend
Set these environment variables in your frontend Railway/Vercel service:

```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

Then add your frontend URL to the backend's `CORS_ALLOWED_ORIGINS`:
```
CORS_ALLOWED_ORIGINS=https://your-frontend.up.railway.app,https://your-app.vercel.app
```

---

## Security checklist

- [ ] `.env` is in `.gitignore` (already configured)
- [ ] `ENCRYPTION_SECRET_KEY` is a unique 64-char hex string (never the Supabase key)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is only set on backend/worker, never in frontend env
- [ ] `CORS_ALLOWED_ORIGINS` only lists your actual frontend domains
- [ ] Railway environment variables are set per-service, not committed to the repo

---

## Troubleshooting

**Worker can't connect to Redis**
- Ensure `REDIS_URL` starts with `rediss://` (TLS) for Upstash
- Verify the Upstash password is correct (no URL-encoding issues)

**`ModuleNotFoundError: No module named 'app'`** in worker
- The worker Dockerfile sets `PYTHONPATH=/app:/app/backend`
- Confirm `COPY backend/ ./backend/` and `COPY worker/ ./worker/` are both in the worker Dockerfile

**Playwright browser fails to launch**
- The worker Dockerfile installs all Chromium system deps via apt
- If still failing, add `ENV PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright` and run
  `playwright install chromium` in the Dockerfile

**`vector(1536)` dimension mismatch**
- The schema was corrected to `vector(384)` to match `all-MiniLM-L6-v2`
- If you already ran the old migration, run:
  `ALTER TABLE memory_vectors ALTER COLUMN embedding TYPE vector(384);`
