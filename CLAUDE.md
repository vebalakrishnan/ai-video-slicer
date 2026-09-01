# CLAUDE.md - AI Video Slicer Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** AI Video Slicer
**Description:** Turns long-form videos (URL or upload) into 5+ scored, AI-selected short-form clips (30–60s, 9:16) with B-roll suggestions, subtitles, and auto-fetched stock footage, ready for YouTube Shorts / Instagram Reels / Facebook.

**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + TypeScript + Vite
- Database: PostgreSQL + SQLAlchemy
- Auth: JWT, **credentials-based only** (email/password — no Google OAuth, no social login)
- UI: Chakra UI
- AI Model: OpenAI `gpt-4o-mini` (transcript analysis, moment scoring, B-roll keyword generation)
- Transcription: Whisper (timestamped transcript, feeds the analysis pipeline)
- Video Processing: `ffmpeg` (cropping, subtitles, B-roll compositing, silence removal)
- Background Jobs: Celery + Redis (long-running video pipeline runs async, never inline in a request)
- Stock B-roll: Pexels/Pixabay API
- Deployment: Docker (multi-stage backend image), docker-compose, image pushed to a container registry

---

## Project Structure

```
ai-video-slicer/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── video_job.py
│   │   │   ├── short_clip.py
│   │   │   └── broll_suggestion.py
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── auth.py, videos.py, shorts.py, analytics.py, admin.py
│   │   ├── services/
│   │   │   ├── transcription.py    # Whisper
│   │   │   ├── moment_analysis.py  # gpt-4o-mini scoring pipeline
│   │   │   ├── broll.py            # keyword gen + Pexels fetch
│   │   │   ├── renderer.py         # ffmpeg pipeline
│   │   │   └── email.py
│   │   ├── tasks/                  # Celery task definitions
│   │   └── auth/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/                  # login, register, dashboard, videos/new,
│   │   │                           # videos/[id], shorts/[id], analytics, admin
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── context/
│   │   └── types/
│   └── package.json
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.worker
│   └── Dockerfile.frontend
├── docker-compose.yml
├── .claude/
│   └── commands/
├── skills/
├── agents/
└── PRPs/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints
def get_video_job(db: Session, job_id: int) -> VideoJob:
    pass

# ALWAYS add docstrings for public functions
def score_candidate_clip(transcript_excerpt: str) -> ClipScores:
    """
    Score a candidate short clip across the 9 engagement dimensions
    using gpt-4o-mini. Never fabricates content not present in the
    transcript excerpt.
    """
    pass

# Long-running video work (transcription, analysis, rendering) MUST run
# as a Celery task — never block a request/response cycle with ffmpeg
# or an LLM call.
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces for props and data
interface ShortClip {
  id: number;
  category: "viral" | "educational" | "emotional" | "surprising" | "story" | "other";
  startTime: number;
  endTime: number;
  overallScore: number;
}

// NO any types allowed
const fetchShorts = async (videoJobId: number): Promise<ShortClip[]> => {
  // ...
};
```

---

## Forbidden Patterns

### Backend
- ❌ Never use `print()` - use `logging` module
- ❌ Never store passwords in plain text - always bcrypt
- ❌ Never hardcode secrets (OpenAI key, DB URL, JWT secret) - use environment variables
- ❌ Never use `SELECT *` - specify columns
- ❌ Never skip input validation
- ❌ Never run transcription/AI-scoring/ffmpeg rendering synchronously inside a request handler
- ❌ Never invent moments, quotes, or scores not grounded in the actual transcript
- ❌ Never add Google OAuth or any social login — auth is credentials-only

### Frontend
- ❌ Never use `any` type
- ❌ Never leave `console.log` in production
- ❌ Never skip error handling in async operations
- ❌ Never use inline styles - use Chakra UI

---

## Module-Specific Rules

### Video Ingestion
- Every `VideoJob` must belong to a user (`user_id` foreign key)
- `status` must be one of: `pending`, `transcribing`, `analyzing`, `rendering`, `completed`, `partial`, `failed`
- Accept either a `source_url` or an uploaded `file_path` — never both, never neither

### AI Moment Analysis
- Must return **at least 5** shorts (up to 10) when the source video supports it; each 30–60s, from a different section where possible
- No clip may start mid-sentence or end before the idea/thought completes
- If fewer than 5 valid shorts exist, respond with the exact `"partial"` JSON contract (see INITIAL.md) — never pad with weak clips to hit the count
- If the video can't be accessed/analyzed, respond with the exact `"error"` JSON contract — never guess or fabricate content

### B-Roll & Rendering
- Every short must have at least one `BRollSuggestion`, preferably placed near the middle of the clip
- Rendered output must match: 9:16, 1080×1920, MP4, H.264 video / AAC audio

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Use plural nouns for resources: `/videos`, `/shorts`
- Return appropriate HTTP status codes:
  - 200: Success
  - 201: Created
  - 400: Bad Request
  - 401: Unauthorized
  - 404: Not Found
  - 409: Conflict
- Video-analysis error/partial responses follow the exact JSON contracts defined in `INITIAL.md` (not generic HTTP error bodies)

---

## Authentication

Credentials-based only — email + password. **Do not implement Google OAuth or any other social login.**

### JWT Configuration
- Access token expires: 30 minutes
- Refresh token expires: 7 days
- Algorithm: HS256

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_video_slicer

# Auth
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Background jobs
REDIS_URL=redis://localhost:6379/0

# Stock B-roll
PEXELS_API_KEY=your-pexels-key

# Email
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASSWORD=

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Celery worker
cd backend
celery -A app.tasks worker --loglevel=info

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up -d

# Build & push backend image to registry
docker build -f docker/Dockerfile.backend -t <registry>/ai-video-slicer-backend:latest .
docker push <registry>/ai-video-slicer-backend:latest

# Tests
pytest backend/tests -v
cd frontend && npm test

# Linting
ruff check backend/
cd frontend && npm run lint
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
refactor([module]): refactor [component]
test([module]): add tests for [feature]
docs: update [documentation]
```

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT → Backend models
- BACKEND-AGENT → API + AI pipeline + ffmpeg rendering
- FRONTEND-AGENT → UI components
- TEST-AGENT → Testing
- REVIEW-AGENT → Code review
- DEVOPS-AGENT → Docker + registry deployment

Read agent definitions in `/agents/` folder.
