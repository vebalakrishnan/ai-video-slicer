# PRP: AI Video Slicer

> Implementation blueprint for parallel agent execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | AI Video Slicer |
| **Type** | SaaS |
| **Version** | 1.0 |
| **Created** | 2026-08-31 |
| **Complexity** | High (async AI pipeline + video rendering, beyond a standard CRUD SaaS) |

---

## PRODUCT OVERVIEW

**Description:** An AI video editor that turns a long-form video (URL or upload) into at least 5 scored, standalone short-form clips (30–60s, 9:16) with B-roll suggestions and rendered subtitles, ready for YouTube Shorts, Instagram Reels, and Facebook.

**Value Proposition:** Creators repurpose one long video into multiple high-performing shorts without manually re-watching footage, writing captions, or sourcing B-roll — the AI finds the strongest moments, scores them, and hands back ready-to-post vertical clips.

**MVP Scope:**
- [ ] Credentials-based auth (register/login, no OAuth)
- [ ] Submit video by URL or file upload
- [ ] Transcription (Whisper) → timestamped transcript
- [ ] `gpt-4o-mini`-driven candidate moment identification + 9-dimension scoring
- [ ] Select top 5–10 distinct, standalone shorts (30–60s each)
- [ ] B-roll keyword generation + Pexels stock fetch, placed near clip midpoint
- [ ] ffmpeg render: 9:16 crop, subtitles, B-roll compositing → MP4 (H.264/AAC)
- [ ] Results UI: processing status → scored results grid → clip detail → download
- [ ] `partial` / `error` JSON contracts when the pipeline can't produce 5 valid shorts

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy | skills/DATABASE.md |
| Auth | JWT + bcrypt, credentials-only (no OAuth) | skills/BACKEND.md |
| UI | Chakra UI | skills/FRONTEND.md |
| AI | OpenAI `gpt-4o-mini` (analysis/scoring/B-roll keywords) + Whisper (transcription) | skills/BACKEND.md |
| Background Jobs | Celery + Redis | skills/BACKEND.md |
| Video Processing | ffmpeg | skills/BACKEND.md |
| Stock Footage | Pexels API | skills/BACKEND.md |
| Testing | pytest + RTL | skills/TESTING.md |
| Deployment | Docker (multi-stage) + docker-compose + registry push | skills/DEPLOYMENT.md |

---

## DATABASE MODELS

### User Model
- id, email (unique), hashed_password, full_name, is_active, is_admin, created_at

### VideoJob Model
- id, user_id (FK → User)
- source_type: enum(url, upload)
- source_url: str | null
- file_path: str | null
- title: str
- duration_seconds: float | null
- status: enum(pending, transcribing, analyzing, rendering, completed, partial, failed)
- transcript: text | null (timestamped JSON)
- error_message: str | null
- created_at, updated_at

### ShortClip Model
- id, video_job_id (FK → VideoJob)
- rank: int
- category: enum(viral, educational, emotional, surprising, story, other)
- start_time, end_time, duration_seconds: float
- title: str
- transcript_excerpt: text
- hook_strength, standalone_value, engagement, retention, payoff, clarity, shareability, viral_potential, b_roll_quality: int (1–10)
- overall_score: float
- status: enum(scored, rendering, ready, failed)
- file_path: str | null (rendered MP4)
- created_at

### BRollSuggestion Model
- id, short_clip_id (FK → ShortClip)
- start_time, end_time: float (within the short)
- visual_type: enum(stock_footage, image, screenshot, screen_recording, chart, animation)
- search_keywords: str
- description: str
- stock_asset_url: str | null

**Relationships:** User 1—N VideoJob 1—N ShortClip 1—N BRollSuggestion. All cascade-delete from User → VideoJob → ShortClip → BRollSuggestion.

---

## MODULES

### Module 1: Authentication
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Create account (email/password) |
| POST | /api/v1/auth/login | Get access + refresh tokens |
| POST | /api/v1/auth/refresh | Refresh access token |
| POST | /api/v1/auth/logout | Revoke refresh token |
| GET | /api/v1/auth/me | Current user profile |
| PUT | /api/v1/auth/me | Update profile |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /login | LoginPage | LoginForm |
| /register | RegisterPage | RegisterForm |
| /profile | ProfilePage | ProfileForm |

---

### Module 2: Video Ingestion
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/videos | Submit video (URL JSON or multipart upload) |
| GET | /api/v1/videos | List current user's video jobs |
| GET | /api/v1/videos/{id} | Get job status + metadata |
| DELETE | /api/v1/videos/{id} | Delete job + assets |
| POST | /api/v1/videos/{id}/generate-shorts | Trigger async pipeline |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /videos/new | NewVideoPage | UrlOrUploadForm, GenerateShortsButton |
| /dashboard | DashboardPage | VideoJobList, StatusBadge |

---

### Module 3: AI Moment Analysis & Clip Scoring
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/videos/{id}/shorts | List ranked shorts for a video job |
| GET | /api/v1/shorts/{id} | Full detail incl. all scores + transcript excerpt |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /videos/{id} | VideoStatusPage | ProcessingSpinner (poll), ResultsGrid |
| /videos/{id}/shorts/{shortId} | ShortDetailPage | VideoPreview, ScoreBreakdown, TranscriptExcerpt |

**Pipeline rules:** at least 5 shorts (up to 10) when possible, 30–60s, distinct sections, complete ideas, exact `error`/`partial` JSON contracts on failure (see INITIAL.md → Special Requirements).

---

### Module 4: B-Roll Suggestion & Sourcing
**Agents:** BACKEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/shorts/{id}/broll | List B-roll suggestions + fetched asset URLs |

---

### Module 5: Rendering & Export
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/shorts/{id}/render | Trigger final render (Celery) |
| GET | /api/v1/shorts/{id}/download | Download rendered MP4 |

**Frontend:** DownloadButton on ShortDetailPage. Output spec: 9:16, 1080×1920, MP4, H.264/AAC.

---

### Module 6: Analytics Dashboard
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/analytics/overview | Videos processed, shorts generated, avg scores, processing time |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /analytics | AnalyticsPage | MetricCards, UsageChart |

---

### Module 7: Admin Panel
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/admin/users | List all users |
| PUT | /api/v1/admin/users/{id} | Update user status |
| GET | /api/v1/admin/stats | Platform-wide stats |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /admin | AdminDashboardPage | StatsCards |
| /admin/users | AdminUsersPage | UserTable |

---

### Module 8: Notifications
**Agents:** BACKEND-AGENT

Internal `email.py` service triggered by pipeline completion/failure — no public endpoint required for MVP.

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: User, VideoJob, ShortClip, BRollSuggestion models + Alembic migrations
- BACKEND-AGENT: main.py, config.py, database.py, Celery app skeleton, project structure
- FRONTEND-AGENT: Vite setup, folder structure, Chakra UI theme, base components, routing shell
- DEVOPS-AGENT: docker-compose.yml (api, worker, redis, postgres, frontend), Dockerfile.backend, Dockerfile.worker, Dockerfile.frontend, env files

**Validation Gate 1:** `pip install -r requirements.txt`, `alembic upgrade head`, `npm install`, `docker-compose config`

**Phase 2: Modules (backend + frontend parallel per module)**
- Auth Module: JWT endpoints + Login/Register/Profile pages
- Video Ingestion: submit/list/status endpoints + upload/dashboard UI
- AI Analysis Pipeline: transcription service (Whisper) → moment_analysis service (`gpt-4o-mini`) → scoring → Celery task wiring + status polling UI
- B-Roll Module: keyword generation + Pexels fetch service
- Rendering Module: ffmpeg render service (crop/subtitles/B-roll compositing) + download endpoint/UI
- Analytics Module: overview endpoint + dashboard UI
- Admin Module: user/stats endpoints + admin UI
- Notifications: email service wired to pipeline completion/failure

**Validation Gate 2:** `ruff check backend/`, `npm run type-check`

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest (incl. mocked OpenAI/Whisper/Pexels/ffmpeg calls) + RTL tests, 80%+ coverage
- REVIEW-AGENT: security audit (auth, file upload validation, signed URLs), performance review (async pipeline never blocks requests)
- RESEARCH-AGENT: best-practices validation (ffmpeg flags, Celery task idempotency, prompt design for `gpt-4o-mini`)

**Final Validation:** Full test suite, `docker-compose up -d`, `curl localhost:8000/health`, end-to-end smoke test (submit sample video → poll status → verify ≥5 shorts or valid `partial`/`error` response)

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config` |
| 2 | `ruff check backend/`, `npm run type-check` |
| 3 | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=postgresql://user:password@localhost:5432/ai_video_slicer
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
REDIS_URL=redis://localhost:6379/0
PEXELS_API_KEY=your-pexels-key
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=
VITE_API_URL=http://localhost:8000
```

> No `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` — auth is credentials-only per product spec.

---

## NEXT STEP

Execute with parallel agents:
/execute-prp PRPs/ai-video-slicer-prp.md
