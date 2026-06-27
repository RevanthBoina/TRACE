# TRACE — Project Structure

## Root Layout
```
/workspace/project/
└── TRACE/                  # Monorepo root: full-stack Next.js + FastAPI app
    ├── app/                # Next.js App Router pages
    ├── components/         # React UI components
    ├── lib/                # Shared utilities
    ├── backend/            # FastAPI Python backend
    └── [config files]
```

## Directory Breakdown

### `app/` — Next.js App Router
| Path | Purpose |
|------|---------|
| `app/layout.tsx` | Root layout: fonts, SiteNav, global CSS |
| `app/page.tsx` | Home/upload page — VideoUploader + RegistrationPanel |
| `app/globals.css` | Tailwind base styles |
| `app/dashboard/page.tsx` | Dashboard page — server component with hardcoded video data (demo) |

### `components/` — UI Components
```
components/
├── dashboard/
│   ├── dashboard-client.tsx   # Client component: filter pills, metric cards, video grid
│   └── video-card.tsx         # Article card per registered video; shows infringing links + DMCA buttons
├── ui/                        # shadcn/ui primitives (Badge, Button, Input, Label, Progress, Select)
├── registration-panel.tsx     # Form to register a canonical platform URL
├── site-nav.tsx               # Sticky top nav with active-link highlighting + notification bell
└── video-uploader.tsx         # Multi-step upload UI with progress tracking
```

### `backend/` — FastAPI Python Service
```
backend/
├── workers/
│   ├── __init__.py
│   └── watermark_worker.py    # Celery task: download from S3, apply watermark, re-upload
├── __init__.py
├── config.py                  # Pydantic Settings: AWS, DB, Redis env vars
├── database.py                # SQLAlchemy engine + session + ORM models
├── main.py                    # FastAPI app, routes, Celery app init
└── README.md
```

### Config / Infrastructure
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Three services: `backend` (FastAPI), `celery` (worker), `redis` |
| `Dockerfile` | Container image for backend + celery |
| `requirements.txt` | Python dependencies |
| `package.json` | Node dependencies (Next.js 16, React 19, shadcn, Tailwind 4) |
| `next.config.mjs` | Next.js config |
| `tsconfig.json` | TypeScript config with `@/` path alias |
| `.env` / `.env.example` | Environment variable templates |
| `components.json` | shadcn/ui component registry config |

## Architectural Patterns

### Frontend
- **Next.js App Router** with clear split: server components for data/metadata, `"use client"` for interactivity
- **shadcn/ui** primitives in `components/ui/` consumed by feature components
- State managed locally with `useState`/`useMemo` — no global state library
- `@/` path alias resolves to the TRACE root

### Backend
- **FastAPI** handles HTTP API; **Celery + Redis** handles async video processing
- **Pydantic Settings** (`config.py`) centralises all env-var configuration
- **SQLAlchemy 2.x** ORM for PostgreSQL persistence
- Processing pipeline: upload → S3 (upload bucket) → Celery worker watermarks → S3 (output bucket)

### Data Flow
```
Browser → FastAPI /upload → S3 upload bucket
                         → Celery task queued via Redis
                              → watermark_worker downloads, processes, re-uploads to S3 output bucket
                              → DB record updated
Browser ← polling /status ← FastAPI ← DB
```
