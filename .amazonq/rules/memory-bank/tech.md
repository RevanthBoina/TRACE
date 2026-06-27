# TRACE — Technology Stack

## Frontend

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js (App Router) | 16.2.6 |
| UI Library | React | 19.2.4 |
| Language | TypeScript | 5.7.3 |
| Styling | Tailwind CSS v4 | ^4.2.0 |
| Component library | shadcn/ui (via `shadcn` CLI) | ^4.8.0 |
| Icons | lucide-react | ^1.16.0 |
| Class utilities | clsx + tailwind-merge | — |
| Animations | tw-animate-css | ^1.4.0 |
| Analytics | @vercel/analytics | 1.6.1 |
| Fonts | Geist Sans + Geist Mono (next/font/google) | — |
| Package manager | pnpm | — |

### TypeScript Config Highlights
- `strict: true`, `target: ES6`, `moduleResolution: bundler`
- Path alias: `@/*` → `TRACE/*` (root of Next.js app)
- `ignoreBuildErrors: true` in next.config.mjs (v0-scaffolded project)

---

## Backend

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | FastAPI | >=0.109.0 |
| Server | Uvicorn (standard) | >=0.27.0 |
| Language | Python | 3.x |
| ORM | SQLAlchemy | >=2.0.0 |
| DB driver | psycopg2-binary (PostgreSQL) | >=2.9.9 |
| Config | pydantic-settings | >=2.0.0 |
| Task queue | Celery | >=5.3.0 |
| Message broker | Redis | >=5.0.0 |
| Cloud storage | boto3 (AWS S3) | >=1.34.0 |
| Video processing | opencv-python-headless, ffmpeg-python, Pillow | various |
| ML/tensors | PyTorch | >=2.0.0 |
| Multipart uploads | python-multipart | >=0.0.6 |

---

## Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerisation | Docker + Docker Compose |
| Services | `backend` (FastAPI on :8000), `celery` (worker), `redis` (Redis 7 Alpine) |
| Database | PostgreSQL (external, via `DATABASE_URL`) |
| Object storage | AWS S3 (two buckets: upload + output) |
| Deployment | Vercel (frontend auto-deploy on `main`) + Docker for backend |

---

## Development Commands

### Frontend (run from `TRACE/`)
```bash
pnpm dev          # Start Next.js dev server on :3000
pnpm build        # Production build
pnpm start        # Start production server
pnpm lint         # ESLint check
```

### Backend (run from `TRACE/`)
```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI dev server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker
celery -A backend.main.celery_app worker --loglevel=info
```

### Docker (full stack)
```bash
# From TRACE/  — uses Docker Compose v2 (no hyphen)
docker compose up --build      # Start all services
docker compose up -d           # Detached mode
docker compose logs -f celery  # Follow worker logs
docker compose down            # Stop all services
```

> **Note:** `docker-compose` (v1) is not installed. Always use `docker compose` (v2 plugin, space not hyphen).

### Environment Variables (`.env`)
```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_UPLOAD_BUCKET=
S3_OUTPUT_BUCKET=
DATABASE_URL=postgresql://...
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
trace_key_pem=           # PEM key for watermark signing
```
