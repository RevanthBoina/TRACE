# OpenHands Agent Memory for TRACE Project

## 🚀 Deployment Status

### Current Architecture
| Component | Provider | URL/Endpoint |
|-----------|----------|--------------|
| Frontend | Vercel | https://trace-phi-two.vercel.app |
| Backend API | AWS EC2 | http://13.63.208.13:8000 |
| Database | AWS RDS PostgreSQL | Connected |
| Message Queue | Redis (Docker) | docker-compose |

### EC2 Management
```bash
# SSH to EC2
ssh -i /workspace/trace-key.pem ec2-user@13.63.208.13

# Services on EC2
cd /home/ec2-user/TRACE
docker compose ps          # Check status
docker compose logs -f    # View logs
docker compose restart    # Restart services (after code changes)
docker compose down       # Stop services
```

## ✅ Completed Features

### Backend (FastAPI)
- `/upload` - Video upload to S3
- `/job/{job_id}` - Job status polling
- `/health` - Health check
- `/metrics` - Backend analytics metrics
- Celery task for watermark processing
- Redis integration for Celery broker
- CORS configured for Vercel frontend

### Frontend (Next.js)
- Video uploader with drag & drop
- Job status polling
- Download button for watermarked video
- Backend stats widget on dashboard
- Vercel Analytics integrated

### Analytics (Implemented)
- **Frontend Events**: `upload_started`, `upload_success`, `watermark_completed`, `download_started`, `error`
- **Backend Metrics**: Request counts, processing times, error rates, uptime
- **Dashboard**: Real-time backend stats display (auto-refresh 30s)

## 🔐 Secrets Management

### EC2 (.env at /home/ec2-user/TRACE)
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-north-1
S3_UPLOAD_BUCKET=trace-upload-temp
S3_OUTPUT_BUCKET=trace-watermarked-out
DATABASE_URL=postgresql://user:pass@rds.amazonaws.com:5432/trace
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
ALLOWED_ORIGINS=https://trace-phi-two.vercel.app
```

### Vercel Environment Variables
```
NEXT_PUBLIC_API_URL=http://13.63.208.13:8000
```

### Local Development
- PEM key: `/workspace/trace-key.pem` (never commit to git)
- .env.example has template for all variables

## 📋 TODO

### Completed
- [x] Basic video upload to S3
- [x] Backend API endpoints (/upload, /job, /health, /metrics)
- [x] Celery + Redis for background processing
- [x] Frontend-backend integration
- [x] CORS configuration
- [x] Analytics tracking (frontend + backend)
- [x] Deploy to EC2

### In Progress / Pending
- [ ] **Test end-to-end video watermarking**
- [ ] **Implement actual VideoSeal watermark embedding** (placeholder exists)
- [ ] Set up auto start/stop (EventBridge for 8AM-8PM)
- [ ] Infringement detection dashboard

## 📝 Important Notes

### EC2 Fixed IP
- **Public IP**: 13.63.208.13
- **Instance ID**: i-06bf6b1ce3d638fb5

### VideoSeal Model
- Location: `backend/ckpts/y_256b_img.jit` (228MB)
- Downloaded from: https://dl.fbaipublicfiles.com/videoseal/y_256b_img.jit
- Current watermark_worker.py has placeholder implementation

### GitHub Repository
- **Repo**: https://github.com/RevanthBoina/TRACE
- **Local path**: `/workspace/project/TRACE`
- **Recent commits**: bbc006d, 8a41557, 1212556, e39a91b

## 📊 Recent Commits
- `bbc006d` - Dockerfile fix
- `8a41557` - Add ALLOWED_ORIGINS to docker-compose
- `1212556` - Add comprehensive analytics tracking
- `e39a91b` - Wire watermark worker, Celery, job status
