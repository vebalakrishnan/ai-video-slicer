# INITIAL.md - AI Video Slicer Product Definition

> AI-powered editor that turns long-form videos into multiple high-quality, ready-to-post short-form clips for YouTube Shorts, Instagram Reels, and Facebook.

---

## PRODUCT

### Name
AI Video Slicer

### Description
An AI video editor, short-form content strategist, and B-roll director in one tool. A user submits a long-form video (by URL or file upload). The system transcribes and analyzes the entire video, intelligently identifies the strongest moments (hook strength, retention, emotional impact, educational value, entertainment, surprise, storytelling, controversy, humor, practical value, shareability, standalone context), and produces **at least 5 distinct short-form clips (30–60s each)**, each scored across multiple engagement dimensions, with B-roll placement suggestions and auto-fetched stock footage, ready for vertical (9:16) short-form platforms.

### Target User
Creators and social media managers posting to Facebook, YouTube (Shorts), and Instagram (Reels) who want to repurpose long-form video into multiple high-performing shorts without manually re-watching and re-cutting the source footage.

### Type
- [x] SaaS (Software as a Service)

---

## TECH STACK

| Layer | Choice |
|-------|--------|
| Backend | FastAPI + Python 3.11+ |
| Frontend | React + TypeScript + Vite |
| Database | PostgreSQL + SQLAlchemy |
| Auth | JWT, credentials-based only (email/password — **no Google OAuth**) |
| UI | Chakra UI |
| Payments | None (MVP) |
| AI Model | OpenAI `gpt-4o-mini` for transcript analysis, moment scoring, and B-roll keyword generation |
| Transcription | Whisper (OpenAI API or `faster-whisper`) to produce a timestamped transcript before analysis |
| Video Processing | `ffmpeg` for slicing, 9:16 cropping/speaker-focused framing, subtitle burn-in, B-roll compositing |
| Background Jobs | Celery + Redis (async pipeline: transcription → analysis → scoring → rendering) |
| Stock Footage | Pexels (or Pixabay) API, queried with AI-generated B-roll search keywords |
| Deployment | Docker (multi-stage backend image), docker-compose (api, worker, redis, postgres, frontend), image pushable to a container registry |

---

## MODULES

### Module 1: Authentication (Required)

**Description:** Credentials-only user authentication (email/password). No OAuth providers.

**Models:**
- User: id, email (unique), hashed_password (bcrypt), full_name, is_active, is_admin, created_at

**API Endpoints:**
- POST /api/v1/auth/register - Create new account
- POST /api/v1/auth/login - Login with email/password, returns access + refresh token
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - Revoke refresh token
- GET /api/v1/auth/me - Get current user profile
- PUT /api/v1/auth/me - Update profile

**Frontend Pages:**
- /login - Login page
- /register - Registration page
- /profile - User profile page (protected)

---

### Module 2: Video Ingestion

**Description:** Accepts a long-form video by URL or direct file upload, stores it, and kicks off transcription.

**Models:**
```
VideoJob:
  - id, user_id (FK)
  - source_type: enum(url, upload)
  - source_url: str | null
  - file_path: str | null
  - title: str
  - duration_seconds: float | null
  - status: enum(pending, transcribing, analyzing, rendering, completed, partial, failed)
  - transcript: text | null          # timestamped transcript (JSON)
  - error_message: str | null
  - created_at, updated_at
```

**API Endpoints:**
```
POST   /api/v1/videos              - Submit a video (JSON {url} or multipart file upload)
GET    /api/v1/videos              - List current user's video jobs
GET    /api/v1/videos/{id}         - Get job status + metadata
DELETE /api/v1/videos/{id}         - Delete a video job and its assets
POST   /api/v1/videos/{id}/generate-shorts  - Trigger the full analysis pipeline (async)
```

**Frontend Pages:**
- /videos/new - Video URL input OR file upload + "Generate Shorts" button
- /dashboard - List of video jobs with status

---

### Module 3: AI Moment Analysis & Clip Scoring

**Description:** Core AI pipeline. Runs the STEP 1–6 process defined in the product spec: access video → identify candidate moments across the *entire* video → build 30–60s candidate clips with clean start/end boundaries → score each candidate → select the top 5 (up to 10) most distinct, standalone shorts. Uses `gpt-4o-mini` against the timestamped transcript; never fabricates content not present in the transcript.

**Models:**
```
ShortClip:
  - id, video_job_id (FK)
  - rank: int
  - category: enum(viral, educational, emotional, surprising, story, other)
  - start_time, end_time: float       # seconds in source video
  - duration_seconds: float
  - title: str
  - transcript_excerpt: text
  - hook_strength, standalone_value, engagement, retention,
    payoff, clarity, shareability, viral_potential, b_roll_quality: int (1-10)
  - overall_score: float
  - status: enum(scored, rendering, ready, failed)
  - file_path: str | null             # rendered 9:16 MP4
  - created_at
```

**API Endpoints:**
```
GET /api/v1/videos/{id}/shorts     - List generated shorts (ranked) for a video job
GET /api/v1/shorts/{id}            - Full detail incl. all scores + transcript excerpt
```

**Frontend Pages:**
- /videos/{id} - Processing status (polling) → results grid once complete
- /videos/{id}/shorts/{shortId} - Clip detail: preview, score breakdown, transcript excerpt

**Business Rules:**
- Must return **at least 5** shorts (up to 10) whenever the source video contains enough valid material; each must be 30–60s, from a different section where possible, with a complete idea (no mid-sentence cuts).
- If the pipeline finds **fewer than 5** valid shorts, respond with a `"partial"` status (see Error Handling) instead of forcing weak clips.
- If the video cannot be accessed/analyzed at all, respond with `"error"` status (see Error Handling).

---

### Module 4: B-Roll Suggestion & Sourcing

**Description:** For each selected short, identifies statements that can be visually illustrated, determines placement (preferring the middle of the clip), generates search keywords, and auto-fetches matching stock footage/images via the Pexels API.

**Models:**
```
BRollSuggestion:
  - id, short_clip_id (FK)
  - start_time, end_time: float        # within the short clip
  - visual_type: enum(stock_footage, image, screenshot, screen_recording, chart, animation)
  - search_keywords: str
  - description: str                   # what should appear + why it supports the narration
  - stock_asset_url: str | null        # fetched from Pexels
```

**API Endpoints:**
```
GET /api/v1/shorts/{id}/broll        - List B-roll suggestions (+ fetched asset URLs) for a short
```

---

### Module 5: Rendering & Export

**Description:** Renders the final short: 9:16 crop with speaker-focused framing, dynamic subtitles with keyword highlighting, subtle zoom, B-roll compositing with smooth transitions, silence/filler removal.

**API Endpoints:**
```
POST /api/v1/shorts/{id}/render      - Trigger final render (async, via Celery worker)
GET  /api/v1/shorts/{id}/download    - Download rendered MP4
```

**Output spec:**
- Aspect ratio 9:16, resolution 1080×1920, format MP4, video codec H.264, audio codec AAC.

---

### Module 6: Notifications

**Description:** Emails the user when their shorts are ready (or when processing fails/is partial).

**API Endpoints:**
- (Internal service, triggered by pipeline completion — no public endpoint required for MVP.)

---

### Module 7: Analytics Dashboard

**Description:** Per-user usage metrics.

**API Endpoints:**
```
GET /api/v1/analytics/overview   - Videos processed, shorts generated, avg scores, processing time
```

**Frontend Pages:**
- /analytics - Usage metrics dashboard

---

### Module 8: Admin Panel

**Description:** Admin-only management interface.

**API Endpoints:**
- GET /api/v1/admin/users - List all users
- PUT /api/v1/admin/users/{id} - Update user status (activate/deactivate)
- GET /api/v1/admin/stats - Platform-wide stats (jobs, success/failure rate, avg processing time)

**Frontend Pages:**
- /admin - Admin dashboard (protected, admin only)
- /admin/users - User management

---

## MVP SCOPE (step-by-step implementation phases)

### Phase 1 — Foundation
- [x] Credentials-based auth (register/login/JWT, no OAuth)
- [x] Docker Compose skeleton (api, worker, redis, postgres, frontend)
- [x] Core DB models (User, VideoJob, ShortClip, BRollSuggestion)

### Phase 2 — Video Ingestion
- [ ] Submit video by URL or file upload
- [ ] Store video, extract duration/title
- [ ] Transcription via Whisper → timestamped transcript stored on VideoJob

### Phase 3 — AI Analysis Pipeline
- [ ] `gpt-4o-mini`-driven candidate moment identification across full transcript
- [ ] Candidate clip boundary construction (clean start/end, 30–60s)
- [ ] Scoring (9 dimensions) + overall score
- [ ] Select top 5–10 distinct shorts; `partial`/`error` handling per spec

### Phase 4 — B-Roll & Rendering
- [ ] B-roll keyword generation + placement per short
- [ ] Pexels API fetch for matching stock footage
- [ ] ffmpeg render: 9:16 crop, subtitles, zoom, B-roll compositing → MP4 (H.264/AAC)

### Phase 5 — Frontend
- [ ] Upload/URL submission UI + "Generate Shorts" button
- [ ] Processing status view (polling)
- [ ] Results grid (scores, categories) + clip detail + download

### Phase 6 — Extras
- [ ] Email notification on completion/failure
- [ ] Analytics dashboard
- [ ] Admin panel

### Phase 7 — Deployment
- [ ] Multi-stage Dockerfile for backend image
- [ ] docker-compose for local/staging
- [ ] Build & push image to container registry

---

## ACCEPTANCE CRITERIA

### Authentication
- [ ] User can register and login with email/password (no OAuth)
- [ ] JWT access + refresh tokens work correctly
- [ ] Protected routes redirect to login

### Video Ingestion & Analysis
- [ ] User can submit a video by URL or upload
- [ ] Pipeline returns at least 5 shorts (30–60s each) when the source supports it, each scored 1–10 across all 9 dimensions
- [ ] Shorts cover distinct sections/topics of the source video whenever possible
- [ ] No clip starts mid-sentence or ends before the idea is complete
- [ ] `partial` status returned with explanation when <5 valid shorts exist
- [ ] `error` status returned when the video cannot be accessed/analyzed

### B-Roll & Rendering
- [ ] Each short has at least one B-roll suggestion with keywords, timestamps, and visual type
- [ ] B-roll auto-fetched from stock API using generated keywords
- [ ] Rendered output matches spec: 9:16, 1080×1920, MP4, H.264/AAC

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes, no `any`
- [ ] Docker builds and runs successfully; image pushes to registry

---

## SPECIAL REQUIREMENTS

### AI Model
- [x] Use `gpt-4o-mini` for all transcript analysis, moment scoring, and B-roll keyword generation
- [x] Never invent information not present in the transcript/video

### Security
- [x] Rate limiting on auth endpoints
- [x] Input validation on all endpoints
- [x] SQL injection prevention
- [x] XSS prevention
- [x] Signed/expiring URLs for uploaded video and rendered clip storage

### Error Handling (exact contracts)
```json
// Video cannot be accessed/analyzed
{
  "status": "error",
  "message": "Unable to access or analyze the provided video URL.",
  "video_url": "VIDEO_URL"
}
```
```json
// Fewer than 5 valid shorts found
{
  "status": "partial",
  "message": "The video does not contain five sufficiently strong standalone segments between 30 and 60 seconds.",
  "available_shorts": 3,
  "shorts": []
}
```

### Integrations
- [x] Whisper (transcription)
- [x] OpenAI `gpt-4o-mini` (analysis/scoring)
- [x] Pexels/Pixabay (stock B-roll)
- [x] Email service for notifications
- [x] Docker registry for image distribution

---

## AGENTS

> These 6 agents will build your product in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | All database models |
| BACKEND-AGENT | Builds API endpoints, AI pipeline, ffmpeg rendering | All modules' backends |
| FRONTEND-AGENT | Creates UI pages and components | All modules' frontends |
| DEVOPS-AGENT | Sets up Docker, docker-compose, CI/CD, registry push | Infrastructure |
| TEST-AGENT | Writes unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/ai-video-slicer-prp.md
```
