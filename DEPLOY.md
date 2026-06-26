# TRACE Deployment Guide

## Overview
TRACE uses a multi-service architecture:
- **FastAPI Backend**: Handles video uploads and job status
- **Celery Worker**: Processes video watermarking in background
- **Redis**: Message queue for Celery tasks
- **PostgreSQL**: Stores job metadata
- **S3**: Stores original and watermarked videos

## Option 1: Docker Compose (Recommended for VPS/Dedicated Server)

### Prerequisites
- Docker & Docker Compose installed
- PostgreSQL database (can use managed service like Supabase, Neon, or Railway)
- S3 buckets created in AWS

### Steps

1. **Clone the repository**
```bash
git clone https://github.com/RevanthBoina/TRACE.git
cd TRACE
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your values
```

3. **Add required variables to `.env`**
```env
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
S3_UPLOAD_BUCKET=trace-upload-temp
S3_OUTPUT_BUCKET=trace-watermarked-out
DATABASE_URL=postgresql://user:pass@host:5432/trace
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
trace_key_pem=-----BEGIN RSA PRIVATE KEY-----\n...
```

4. **Download VideoSeal model (optional)**
```bash
mkdir -p backend/ckpts
curl -L -o backend/ckpts/y_256b_img.jit \
  https://dl.fbaipublicfiles.com/videoseal/y_256b_img.jit
```

5. **Start services**
```bash
docker-compose up -d
```

6. **Check status**
```bash
docker-compose logs -f backend
docker-compose ps
```

## Option 2: AWS EC2 with Docker

### Launch EC2 Instance
1. Choose Amazon Linux 2023 or Ubuntu 22.04
2. Instance type: t3.medium or larger (for video processing)
3. Configure security groups: Open ports 8000, 22

### SSH and Install Docker
```bash
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker ubuntu
```

### Clone and Deploy
```bash
git clone https://github.com/RevanthBoina/TRACE.git
cd TRACE
docker-compose up -d
```

## Option 3: Railway/Render (Managed Hosting)

### Railway
1. Create Railway account
2. Add PostgreSQL plugin
3. Add Redis plugin
4. Deploy from GitHub
5. Set environment variables in Railway dashboard

### Render
1. Create Web Service for backend
2. Create Background Worker for Celery
3. Add managed PostgreSQL
4. Add managed Redis
5. Set environment variables

## Frontend Deployment (Vercel)

1. **Push code to GitHub**
```bash
git push origin main
```

2. **Connect to Vercel**
- Go to vercel.com
- Import `RevanthBoina/TRACE`
- Framework: Next.js
- Root Directory: `.` (leave as default)

3. **Set environment variables in Vercel**
```
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
```

4. **Deploy**

## Health Check
```bash
curl https://your-backend-domain.com/health
# Should return: {"status":"healthy"}
```

## Troubleshooting

### Backend won't start
```bash
docker-compose logs backend
# Check DATABASE_URL and AWS credentials
```

### Celery worker not processing
```bash
docker-compose logs celery
# Ensure Redis is running
docker-compose ps redis
```

### Video processing fails
- Check ffmpeg is installed
- Verify S3 bucket permissions
- Check CloudWatch logs on AWS

## Monitoring
- Backend logs: `docker-compose logs -f backend`
- Celery logs: `docker-compose logs -f celery`
- Health check: `curl http://localhost:8000/health`
