# TechMart Multi-Agent AI Customer Support Assistant

A working prototype of the multi-agent customer support system described in
the project brief: an **Intent Detection Agent** routes each customer message
through an **Agent Router** to one or more **specialized agents** (Billing,
Technical, Product, Complaint, FAQ), each of which pulls relevant context from
a company knowledge base via **RAG** (FAISS + sentence-transformers) and
generates a reply using a **Hugging Face**-hosted LLM. A **Response
Aggregator** merges multi-agent replies into one coherent answer, and a
SQLite-backed **Conversation Memory** stores every turn.

```
Customer → Chat UI → FastAPI → Intent Detection → Agent Router
                                                       │
                              ┌────────────┬───────────┼────────────┬───────────┐
                              ▼            ▼            ▼            ▼           ▼
                          Billing      Technical     Product     Complaint     FAQ
                              │            │            │            │           │
                              └────────────┴─────RAG (FAISS)────────┴───────────┘
                                                       │
                                            Response Aggregator → Reply
```

## Project layout

```
customer-support-ai/
├── backend/
│   ├── main.py                 FastAPI app (auth + chat + history routes)
│   ├── config.py                All settings, overridable via .env
│   ├── models.py                 Pydantic request/response schemas
│   ├── auth/
│   │   ├── user_store.py          MongoDB user collection + bcrypt password hashing
│   │   └── jwt_handler.py         Issues/validates JWTs, FastAPI auth dependency
│   ├── agents/
│   │   ├── intent_detection.py   Module 3 — classifies message into intents
│   │   ├── router.py             Module 4 — routes + aggregates (Response Aggregator)
│   │   ├── billing.py            Module 5 — Billing Agent
│   │   ├── technical.py          Module 5 — Technical Support Agent
│   │   ├── product.py            Module 5 — Product Agent
│   │   ├── complaint.py          Module 5 — Complaint Agent (+ escalation flag)
│   │   ├── faq.py                Module 5 — FAQ Agent
│   │   └── base_agent.py         Shared RAG + LLM call logic
│   ├── rag/
│   │   ├── ingest.py             Module 7 — chunk + embed + build FAISS index
│   │   └── retriever.py          Module 7 — load index, semantic search
│   ├── llm/hf_client.py          Hugging Face Inference API wrapper
│   ├── analytics/
│   │   └── service.py             Module 9 — aggregation queries for the dashboard
│   ├── memory/conversation_memory.py   Module 8 — SQLite conversation history
│   └── vectorstore/              FAISS index + metadata (generated on first run)
├── knowledge_base/               Module 6 — sample TechMart Electronics docs
├── frontend/                     Module 2 & 9 — React + Vite app (see frontend/README.md)
│   ├── components/                 Sidebar, ChatWindow, Composer, MessageBubble, etc.
│   ├── pages/                       LoginPage, ChatPage, AnalyticsPage
│   ├── hooks/                        useAuth, useChat, useSessions, useAnalytics
│   ├── services/                      Thin fetch wrappers around the backend API
│   └── styles/                         Theme tokens + global rules
├── Dockerfile                    Backend container image (used by Railway)
├── railway.json                  Railway deploy config
├── docker-compose.yml             Local dev: backend + MongoDB together
├── .dockerignore
├── .env.example
└── README.md
```

## 1. Prerequisites

- Python 3.11+
- A free Hugging Face account + access token: https://huggingface.co/settings/tokens
  (needs at least "Make calls to Inference Providers" permission)
- MongoDB, for user accounts — either:
  - **Local**: install MongoDB Community Server and run `mongod` (default
    `mongodb://localhost:27017`, no auth needed for local dev), or
  - **Docker**: skip installing Mongo entirely and use
    `docker compose up --build` (see Deployment section) — it starts Mongo
    for you.
  - **Atlas** (also works locally): a free-tier cluster's connection string
    works everywhere, including your laptop — see Deployment below.

## 2. Backend setup

```bash
cd customer-support-ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r backend/requirements.txt

cp .env.example .env
# edit .env: paste your HF_TOKEN, and set MONGODB_URI if not using the
# mongodb://localhost:27017 default
```

Build the vector store from the sample knowledge base (this also happens
automatically on first API call if you skip this step):

```bash
python -m backend.rag.ingest
```

Start the API:

```bash
uvicorn backend.main:app --reload --port 8000
```

Check it's alive: open http://localhost:8000/api/health — should return
`{"status": "ok"}`. Interactive API docs are at http://localhost:8000/docs.
If `MONGODB_URI` isn't reachable, you'll see a startup warning in the
terminal and `/api/auth/signup` and `/api/auth/login` will fail until it's
fixed — everything else (chat, RAG) still works.

## 3. Frontend

A React (Vite) app styled after ChatGPT/Gemini — dark theme, collapsible
conversation-history sidebar, centered chat column, pill-shaped composer.
See `frontend/README.md` for the full breakdown of the folder structure.

```bash
cd frontend
npm install
npm run dev
# then visit http://localhost:5500
```

It talks to the backend at `http://localhost:8000` by default (override with
`VITE_API_BASE_URL` in `frontend/.env.local`; CORS is open by default on the
backend — tighten `ALLOWED_ORIGINS` in the backend's `.env` before deploying).

> A previous single-file HTML/vanilla-JS version of the frontend is kept at
> `frontend-legacy-html/` for reference — it's no longer maintained and isn't
> wired up to run; the React app in `frontend/` is the one to use.

**Module 2 — Chat Interface features:**

- **Chat window** — scrolling message log, ChatGPT-style (user messages as
  bubbles, assistant replies as plain text with an avatar), escalation
  styling, and per-reply agent-routing badges.
- **Send message** — auto-growing textarea + send button, `Enter` to send
  (`Shift+Enter` for a newline), disabled while a reply is in flight.
- **Conversation history** — a sidebar lists every past conversation for the
  logged-in user (`GET /api/sessions`), most recent first, with a preview and
  relative timestamp. Clicking one loads its full transcript
  (`GET /api/history/{session_id}`). **+ New conversation** starts a fresh
  thread; the sidebar refreshes automatically as new messages come in. The
  sidebar is collapsible for a narrower layout.
- **Typing indicator** — an animated three-dot indicator shown while waiting
  on the backend, replaced by the real reply when it arrives.

Login persists across page refreshes (the JWT is kept in `localStorage` and
re-validated against `GET /api/auth/me` on load).

## 4. Trying it out

Example messages to test routing:

- `"I paid yesterday but Premium is still locked"` → routes to **Billing +
  Technical**, aggregated into one reply.
- `"How long does a refund take?"` → **Billing**, grounded in
  `refund_policy.md`.
- `"My app keeps crashing after the update"` → **Technical**.
- `"This is the worst service I've ever had, I want a refund now"` →
  **Complaint**, flagged `escalated: true`.
- `"What are your support hours?"` → **FAQ**.

Send a couple of messages, click **+ New conversation**, send a different
message, then use the sidebar to switch back — the full transcript (with
routing badges) reloads from `GET /api/history/{session_id}`.

## 5. Swapping in your own knowledge base

Drop `.md`, `.txt`, or `.pdf` files into `knowledge_base/`, then rebuild the
index:

```bash
python -m backend.rag.ingest
```

## 5.5 Authentication

Every chat session belongs to a signed-up, logged-in user. User accounts are
stored in **MongoDB** (`backend/auth/user_store.py`) — locally that's a
`mongod` on `localhost:27017` with no auth required; in production it's a
MongoDB Atlas cluster (free tier is enough — see Deployment below). Set
`MONGODB_URI` and `MONGODB_DB_NAME` in `.env`.

Auth endpoints:

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/auth/signup` | `{email, name, password}` | `{access_token, user}` |
| POST | `/api/auth/login` | `{email, password}` | `{access_token, user}` |
| GET | `/api/auth/me` | — (send `Authorization: Bearer <token>`) | `{id, email, name}` |

`/api/session`, `/api/chat`, and `/api/history/{session_id}` all require an
`Authorization: Bearer <token>` header. A session created by one user returns
`404` if a different user's token tries to access it.

Passwords are hashed with `bcrypt` directly (not via `passlib`, which has a
long-standing, unresolved compatibility bug with modern `bcrypt` releases).
Email uniqueness is enforced with a unique index on the `users` collection
(so two concurrent signups with the same email can't both succeed) as well
as an application-level check. Tokens are signed JWTs (HS256) that expire
after `JWT_EXPIRE_MINUTES` (24h by default). Set a real `JWT_SECRET` in
`.env` — see the generation command there — or the server will print a
warning and use a random key that invalidates every token on restart.

If `MONGODB_URI` is unreachable when the backend starts, it prints a warning
instead of crashing — auth endpoints will return errors until it's fixed, but
the rest of the app (chat, RAG) is unaffected since conversation memory
still runs on its own local SQLite file, independent of Mongo.

The React app (`frontend/`) has a built-in login/signup screen; open it and
create an account to try the full flow.

## 5.6 Analytics dashboard

`GET /api/analytics/summary?days=14` (admin-only) returns aggregate metrics
across every conversation: total conversations/messages/customers, escalation
rate, average messages per conversation, intent and agent-routing
distributions, a messages-per-day series, and the most recent escalated
conversations. `GET /api/analytics/me` returns the same shape scoped to just
the logged-in user's own conversations — no special access required.

"Admin" is anyone whose email is listed in `ADMIN_EMAILS` in `.env`
(comma-separated). Sign up with one of those emails; a link to
**Analytics** appears at the bottom of the sidebar in the React app
(`/analytics` route, charts via Recharts).

## 6. Customizing the LLM

Any chat model listed under **Inference Providers** on its Hugging Face model
page works — change `HF_MODEL` in `.env` to its exact repo ID (always in the
form `namespace/repo-name`, no spaces). The default,
`Qwen/Qwen2.5-7B-Instruct`, is ungated and served by multiple providers so
`HF_PROVIDER=auto` routing is reliable. Gated models (most `meta-llama/*`
models) require clicking "Agree" on the model's HF page with the same account
as your token, or requests will fail with a 403. Larger models give
noticeably better routing and aggregation quality if your provider credits
allow it, for example:

```
HF_MODEL=meta-llama/Llama-3.1-70B-Instruct
HF_MODEL=deepseek-ai/DeepSeek-R1
HF_MODEL=Qwen/Qwen2.5-72B-Instruct
```

### Troubleshooting: `Failed to resolve api-inference.huggingface.co`

This means an old version of `huggingface_hub` is calling a domain Hugging
Face has retired. Fix:

```bash
pip install -U "huggingface_hub>=0.35"
```

and make sure `backend/llm/hf_client.py` passes `provider=config.HF_PROVIDER`
to `InferenceClient` (already the case in this repo). Requests now go through
`router.huggingface.co`, which picks a provider (Together, Groq, Cerebras,
etc.) for you.

## 7. Deployment

Deploy config included: **Railway** for the backend (Dockerfile), **Vercel**
for the frontend (static Vite build), **MongoDB Atlas** for user accounts.
Conversation memory and the FAISS vector store stay on local files by
design (see the note on persistence below) — no other services required.

### 9.1 MongoDB Atlas (user accounts)

1. Create a free cluster at https://www.mongodb.com/cloud/atlas/register.
2. Add a database user (Database Access) and allow access from anywhere —
   `0.0.0.0/0` — under Network Access (fine for this project; tighten to
   Railway's static IPs if you're on a paid Railway plan that provides them).
3. Copy the connection string (Database → Connect → Drivers), which looks
   like `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority`.
   That's your `MONGODB_URI`.

### 9.2 Backend on Railway

1. https://railway.app → New Project → Deploy from GitHub repo (push this
   project to GitHub first). Railway detects `Dockerfile` and `railway.json`
   automatically.
2. Under Variables, set: `MONGODB_URI` (from 9.1), `MONGODB_DB_NAME`,
   `HF_TOKEN`, `HF_MODEL`, `JWT_SECRET` (generate with
   `python -c "import secrets; print(secrets.token_hex(32))"`), `ADMIN_EMAILS`,
   and `ALLOWED_ORIGINS` (set this to your Vercel frontend URL once you have
   it, e.g. `https://your-app.vercel.app`).
3. Railway assigns a public URL and injects `$PORT` — the Dockerfile's CMD
   already reads it, no changes needed.
4. Confirm `https://<your-app>.up.railway.app/api/health` returns
   `{"status": "ok"}`.

### 9.3 Frontend on Vercel

1. https://vercel.com → New Project → import the same GitHub repo.
2. Set **Root Directory** to `frontend`. Vercel auto-detects the Vite
   preset; `frontend/vercel.json` handles SPA routing (so refreshing
   `/analytics` doesn't 404).
3. Add an environment variable `VITE_API_BASE_URL` = your Railway backend
   URL from 9.2 (e.g. `https://your-app.up.railway.app`) — this is baked in
   at build time, so redeploy after changing it.
4. Deploy. Go back to Railway and update `ALLOWED_ORIGINS` to this Vercel
   URL if you hadn't yet, and redeploy the backend.

### 9.4 Local full-stack testing with Docker

```bash
cp .env.example .env   # fill in HF_TOKEN, JWT_SECRET, etc.
docker compose up --build
```

This starts a local MongoDB container and the backend together (frontend
still runs separately via `npm run dev` — Compose only covers the backend +
its database here). Useful for confirming the Dockerfile/Mongo wiring works
before pushing to Railway.

### 9.5 A note on persistence

Conversation history (SQLite, `backend/memory/`) and the FAISS vector index
(`backend/vectorstore/`) are local files. That's fine for `docker compose`
with the volumes it defines, but **most PaaS free tiers (including Railway's
default filesystem) are ephemeral** — a redeploy or restart can wipe them.
The vector store rebuilds itself automatically from `knowledge_base/` on
next startup, so that's low-stakes. Conversation history is not automatically
rebuilt, though — if you need it to survive redeploys on Railway, either
attach a Railway Volume mounted at `/app/backend/memory`, or migrate
`conversation_memory.py` to MongoDB as well (same pattern as
`user_store.py` — this is a natural next step if you want it).

## 8. What's simplified vs. the full spec (and why)

This is a runnable prototype, not the full production build described in the
brief. Left as extension points:

- **Conversation memory and the vector store on managed services** — these
  still use local SQLite/FAISS (see 9.5 above on ephemeral storage);
  swapping in MongoDB for conversation memory and a managed vector DB
  (Pinecone/Chroma Cloud) would make the whole stack redeploy-safe.
- **Voice, multilingual, human handoff, ticketing** (bonus enhancements) —
  not built.

## 9. Known limitations

- Intent classification and response aggregation depend on the HF model
  reliably following instructions; smaller free-tier models occasionally
  produce malformed output. `intent_detection.py` has a keyword-based
  fallback so the pipeline doesn't break, but this fallback is intentionally
  simple.
- The FAISS index rebuilds from scratch each time `ingest.py` runs (fine at
  this scale — a few dozen documents). For a large knowledge base, consider
  incremental indexing.
