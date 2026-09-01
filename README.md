# AI Video Slicer

AI-powered editor that turns a long-form video into multiple ready-to-post short-form clips (YouTube Shorts / Instagram Reels / Facebook). Submit a video by URL or upload; the pipeline transcribes it, has `gpt-4o-mini` scan the **entire** transcript for the strongest standalone moments, scores each candidate across nine engagement dimensions, generates B-roll suggestions with auto-fetched stock footage, and renders finished 9:16 vertical clips with burned-in subtitles.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the App](#running-the-app)
- [API Overview](#api-overview)
- [Configuration Reference](#configuration-reference)
- [Development](#development)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Credentials-only auth** — email/password with JWT access + refresh tokens (no OAuth/social login by design)
- **Video ingestion** — submit by URL (YouTube and hundreds of other sites via `yt-dlp`, or a direct file link) or upload a file directly
- **AI moment analysis** — `gpt-4o-mini` scans the full transcript (not just the opening) and identifies 30–60s candidate clips with clean sentence boundaries and a complete idea (hook → payoff)
- **9-dimension scoring** — hook strength, standalone value, engagement, retention, payoff, clarity, shareability, viral potential, B-roll quality
- **B-roll generation** — AI-suggested visual cutaways with auto-fetched stock footage/photos from Pexels
- **Rendering** — 9:16 (1080×1920) H.264/AAC MP4 output with burned-in subtitles, B-roll compositing, and speaker-focused cropping via `ffmpeg`
- **Async pipeline** — the whole flow (transcribe → analyze → score → B-roll → render) runs on Celery/Redis, never inline in a web request
- **Analytics & Admin** — per-user usage overview; admin panel for user management and platform stats
- **Email notifications** — completion/failure emails (best-effort; never blocks the pipeline)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.11 |
| Frontend | React + TypeScript + Vite + Chakra UI v3 + framer-motion |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| Auth | JWT (HS256) + bcrypt, credentials-only |
| Background jobs | Celery + Redis |
| AI | OpenAI `gpt-4o-mini` (analysis/scoring/B-roll keywords) + Whisper (transcription) |
| Video download | `yt-dlp` |
| Rendering | `ffmpeg` (via `ffmpeg-python`) |
| Stock B-roll | Pexels API |
| Deployment | Docker Compose (multi-stage backend image) |

---

## Architecture

```
                 ┌─────────────┐        ┌──────────────┐
   Browser  ───► │  frontend   │  ───►  │   backend    │  ───►  PostgreSQL
                 │ (nginx/SPA) │        │  (FastAPI)   │
                 └─────────────┘        └──────┬───────┘
                                                │ dispatches
                                                ▼
                                         ┌──────────────┐
                                         │    Redis     │◄──── broker/backend
                                         └──────┬───────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │    worker    │  (Celery)
                                         │              │
                                         │ yt-dlp ──────┼──► downloads/
                                         │ Whisper ─────┼──► OpenAI
                                         │ gpt-4o-mini ─┼──► OpenAI
                                         │ Pexels ──────┼──► stock B-roll
                                         │ ffmpeg ──────┼──► renders/
                                         └──────────────┘
```

**Pipeline state machine** (`VideoJob.status`, driven by `app/tasks/pipeline.py`):

```
pending → transcribing → analyzing → [rendering per clip] → completed
                                   ╲→ partial   (fewer than MIN_SHORTS valid candidates)
   (video unreachable at any stage) → failed
```

- `backend` (FastAPI, handles HTTP requests) and `worker` (Celery, runs the actual pipeline) are **separate containers built from the same image**. They share three Docker named volumes (`uploads_data`, `downloads_data`, `renders_data`) so a file written by one is visible to the other — without these, an uploaded file would never be visible to the worker that processes it.
- Long-running work (download, transcription, AI calls, rendering) always happens in the `worker`/Celery process — never inline in a FastAPI request handler.

---

## Project Structure

```
ai-video-slicer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, routers, exception handlers
│   │   ├── config.py             # Settings (env vars)
│   │   ├── database.py           # SQLAlchemy engine/session
│   │   ├── dependencies.py       # get_db, get_current_user
│   │   ├── exceptions.py         # AppException hierarchy
│   │   ├── rate_limit.py         # slowapi limiter (auth endpoints)
│   │   ├── models/                # User, VideoJob, ShortClip, BRollSuggestion
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── routers/               # auth, videos, shorts, analytics, admin
│   │   ├── services/              # transcription, moment_analysis, broll,
│   │   │                          # render, email, admin, analytics
│   │   ├── auth/jwt.py            # token creation/verification, password hashing
│   │   └── tasks/                 # Celery app + pipeline.py (the orchestrator)
│   ├── alembic/                   # DB migrations
│   ├── requirements.txt
│   └── Dockerfile                 # multi-stage: build deps, then slim runtime
├── frontend/
│   ├── src/
│   │   ├── pages/                 # Login, Register, Dashboard, NewVideo,
│   │   │                          # VideoStatus, ShortDetail, Analytics, Admin*
│   │   ├── components/            # ui/ (GlassCard, GradientButton, ...),
│   │   │                          # layout/ (AppHeader, AppLayout, PageWrapper),
│   │   │                          # auth/, admin/, video/, analytics/
│   │   ├── hooks/                 # React Query hooks (useVideos, useAdmin, ...)
│   │   ├── services/               # thin axios wrappers per backend module
│   │   ├── context/AuthContext.tsx
│   │   └── types/index.ts
│   └── Dockerfile                 # multi-stage: vite build → nginx
├── docker-compose.yml             # db, redis, backend, worker, frontend
├── docker-compose.dev.yml         # dev override (live-reload mounts)
├── .env.example
├── PRPs/ai-video-slicer-prp.md    # implementation blueprint
└── INITIAL.md                     # full product spec
```

---

## Prerequisites

- Docker Desktop (with Docker Compose)
- An [OpenAI API key](https://platform.openai.com/api-keys) with access to `gpt-4o-mini` and Whisper
- A [Pexels API key](https://www.pexels.com/api/) (free) — optional, only needed for auto-fetched B-roll
- **Windows + WSL2 users:** see [Troubleshooting](#troubleshooting) — large file uploads to OpenAI can stall under WSL2's default NAT networking mode

---

## Setup

1. **Copy the environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Fill in `.env`:**

   | Variable | Required | Notes |
   |---|---|---|
   | `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Yes | Any values you choose — Postgres creates this user/db on first start |
   | `SECRET_KEY` | Yes | Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `OPENAI_API_KEY` | Yes | From platform.openai.com — required for transcription and analysis |
   | `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini` |
   | `PEXELS_API_KEY` | No | Leave blank to skip auto-fetched B-roll (keyword suggestions still generate) |
   | `SMTP_*` | No | Leave all blank to skip email notifications entirely (logged, never fails the pipeline) |
   | `VITE_API_URL` | Yes | `http://localhost:8000` for local Docker Compose |

3. **Build and start everything:**
   ```bash
   docker-compose up -d --build
   ```

4. **Apply database migrations:**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

---

## Running the App

| Service | URL |
|---|---|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| Interactive API docs (Swagger) | http://localhost:8000/docs |

Register an account at `/register`, then log in — you'll land on the dashboard where you can submit a video by URL or upload.

**Making a user an admin** (unlocks `/admin` and `/admin/users` in the nav):
```bash
docker-compose exec db psql -U postgres -d ai_video_slicer \
  -c "UPDATE users SET is_admin = true WHERE email = 'you@example.com';"
```
(Log out and back in afterward — the frontend caches `is_admin` from login.)

---

## API Overview

All endpoints are prefixed `/api/v1`. Full interactive docs at `/docs`.

| Module | Endpoints |
|---|---|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET/PUT /auth/me` |
| **Videos** | `POST /videos` (URL or upload), `GET /videos`, `GET/DELETE /videos/{id}`, `POST /videos/{id}/generate-shorts`, `GET /videos/{id}/shorts` |
| **Shorts** | `GET /shorts/{id}`, `GET /shorts/{id}/broll`, `POST /shorts/{id}/render`, `GET /shorts/{id}/download` |
| **Analytics** | `GET /analytics/overview` |
| **Admin** | `GET /admin/users`, `PUT /admin/users/{id}`, `GET /admin/stats` (admin-only) |

Auth is enforced on every endpoint except `/auth/register` and `/auth/login`; ownership is enforced on every `VideoJob`/`ShortClip`/`BRollSuggestion` (a resource belonging to another user 404s, never leaking existence).

---

## Configuration Reference

Full list in `.env.example`. Key backend settings (`backend/app/config.py`):

- `MIN_SHORTS` / `MAX_SHORTS` / `MIN_CLIP_SECONDS` / `MAX_CLIP_SECONDS` — in `backend/app/services/moment_analysis_service.py`, not `.env`. `MIN_SHORTS` (default 5 per the product spec, matching the "at least 5 shorts" requirement) is the threshold between a `completed` result and a `partial` one.
- `ALLOWED_ORIGINS` — CORS allowlist; defaults include `http://localhost` (the Docker-served frontend, port 80) and the Vite dev ports.
- Rate limiting on `/auth/register` and `/auth/login` is fixed at 5 requests/minute (`backend/app/routers/auth.py`).

---

## Development

**Live-reload mode** (mounts source into the containers):
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**Frontend only** (faster iteration, run outside Docker):
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, set VITE_API_URL in frontend/.env
```

**Linting:**
```bash
cd backend && ruff check app/
cd frontend && npx tsc -b --noEmit && npm run lint
```

**Database migrations** (after changing a model):
```bash
docker-compose exec backend alembic revision --autogenerate -m "describe the change"
docker-compose exec backend alembic upgrade head
```

There is intentionally **no automated test suite** in this project.

---

## Known Limitations

- **Very long videos aren't chunked** for the Whisper call — a compressed mono audio track is extracted to stay under Whisper's 25MB request limit (~50+ minutes at 64kbps), but content beyond that isn't split into multiple requests.
- **The Celery pipeline is one large task**, not a chain of smaller retryable stages — a worker crash mid-run leaves the job stuck rather than auto-resuming from the last completed stage.
- **No rate-limit/backoff tuning per OpenAI call type** — transient OpenAI/Pexels errors rely on the SDK's own default retry behavior.
- **Logout doesn't revoke refresh tokens** (no blocklist table) — an acknowledged MVP limitation of the stateless-JWT design.
- **URL ingestion does a direct download, not a smart re-encode** — very large source videos consume worker disk/bandwidth up to the 500MB cap before any analysis happens.

---

## Troubleshooting

### Large uploads to OpenAI hang or time out (Windows + WSL2 + Docker Desktop)

**Symptom:** a small request (e.g. `GET /v1/models`) succeeds in ~1s from inside a container, but the Whisper transcription call (uploading several MB of audio) hangs for minutes and eventually times out — while the exact same upload from the Windows host succeeds in seconds.

**Cause:** a known WSL2 networking issue where large HTTP request bodies stall over the default NAT virtual network interface.

**Fix:**
1. Quit Docker Desktop completely (tray icon → Quit).
2. Create/edit `%USERPROFILE%\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
3. In PowerShell: `wsl --shutdown`
4. Restart Docker Desktop and `docker-compose up -d` again.

If `mirrored` alone doesn't fully resolve it, add `dnsTunneling=true` under the same `[wsl2]` block.

### `ValueError: password cannot be longer than 72 bytes` / password hashing crashes

**Cause:** `passlib` (used for bcrypt hashing) is unmaintained and incompatible with `bcrypt>=4.0`.

**Fix:** `backend/requirements.txt` pins `bcrypt<4.0.0` — make sure your installed environment matches (`pip install -r requirements.txt` fresh, or `pip install "bcrypt<4.0.0"` if you have a stale environment).

### A dispatched job stays at `pending` forever with no error

**Cause:** the Celery worker didn't import the module that registers the pipeline task (only relevant if you're customizing `backend/app/tasks/`).

**Check:** `docker logs <worker-container>` on startup should list both tasks under `[tasks]`:
```
[tasks]
  . app.tasks.pipeline.process_video_job
  . app.tasks.pipeline.render_single_short
```
If missing, confirm `backend/app/tasks/__init__.py` passes `include=["app.tasks.pipeline"]` to the `Celery(...)` constructor.

### `Permission denied` writing to `/app/uploads`, `/app/downloads`, or `/app/renders`

**Cause:** Docker named volumes are created root-owned by default; the containers run as a non-root `appuser`.

**Fix:** already handled in `backend/Dockerfile` (the directories are pre-created and `chown`'d before the volumes are ever mounted). If you still hit this after a manual `docker volume create`, remove the volume and let `docker-compose up` recreate it from the image:
```bash
docker-compose down
docker volume rm ai-video-slicer_uploads_data ai-video-slicer_downloads_data ai-video-slicer_renders_data
docker-compose up -d
```

### `413` from the Whisper API

**Cause:** OpenAI's Whisper endpoint hard-rejects any request over 25MB. A full video file routinely exceeds this.

**Fix:** already handled — `transcribe_video` extracts a compressed, audio-only track via `ffmpeg` before calling Whisper whenever the source file exceeds 25MB.
