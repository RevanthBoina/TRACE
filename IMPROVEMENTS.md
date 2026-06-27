# TRACE - Comprehensive Improvement Plan

## Research Summary

### Current Setup Analysis
| Component | Current | Issue |
|-----------|---------|-------|
| Frontend | Vercel | ✅ Good - Serverless, global CDN |
| Backend | AWS EC2 | ⚠️ Always-on, manual management |
| Database | AWS RDS | ✅ Good - Managed PostgreSQL |
| Watermarking | VideoSeal | ⚠️ Placeholder only |
| Queue | Redis Docker | ⚠️ Ephemeral in compose |

---

## Phase 1: Infrastructure Optimizations

### 1.1 Database (Current: RDS) ✅ Keep as-is
- **Current**: AWS RDS PostgreSQL
- **Verdict**: Best choice for production - managed, reliable, free tier available
- **Improvement**: Add connection pooling with PgBouncer

### 1.2 Backend Hosting Options

| Option | Pros | Cons | Cost/mo |
|--------|------|------|---------|
| **Current EC2** | Full control, GPU support | Manual, always-on cost | ~$10-15 |
| **Railway** | Easy deploy, managed DB | Ephemeral storage, no GPU | $5-30 |
| **Render** | Simple, workers built-in | Sleeps on free tier | $7-25 |
| **Fly.io** | Global, per-second billing | No GPU (deprecated) | $2-10 |

**Recommendation**: Keep EC2 but add auto-start/stop (EventBridge) for 8AM-8PM

### 1.3 Queue Optimization

| Option | Pros | Cons | Cost |
|--------|------|------|------|
| **Redis Docker** | Free, local | Loses data on restart | Free |
| **Upstash Redis** | Serverless, durable | $0.04/1000 commands | ~$5/mo |
| **Redis Cloud** | Managed, free tier | - | Free tier |

**Recommendation**: Move Redis to Upstash for durability

---

## Phase 2: Video Processing Improvements

### 2.1 Watermarking Stack

| Option | Robustness | Complexity | Cost |
|--------|------------|------------|------|
| **VideoSeal (current)** | ✅ Excellent | High | Free (self-host) |
| **FFmpeg Visible** | ❌ Easy to remove | Low | Free |
| **AWS MediaConvert** | ✅ Good | Low | $0.0075/min |
| **inference.sh API** | ✅ Good | Low | ~$10/mo |

**Recommendation**: 
1. Complete VideoSeal implementation (current path)
2. Add visible watermark as fallback/deterrent
3. Use MediaConvert for large batch jobs

### 2.2 VideoSeal Implementation Steps

```
Step 1: Fix watermark_worker.py
├── Load TorchScript model correctly
├── Implement frame extraction with av (PyAV)
├── Apply watermark to 5/10 frames
├── Re-encode with ffmpeg
└── Return watermarked video

Step 2: Add GPU support
├── Check if EC2 has GPU (t3 doesn't)
├── Consider GPU instance for processing
└── OR use CPU with optimizations

Step 3: Optimize for production
├── Add batch processing
├── Add rate limiting
└── Add processing timeouts
```

### 2.3 Add Visible Watermark (Easy Win)

```python
# Quick visible watermark using ffmpeg
def add_visible_watermark(input_video, output_video, watermark_text):
    return f"""
    ffmpeg -i {input_video} -vf "
        drawtext=text='{watermark_text}':fontcolor=white:fontsize=24:
        box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=H-40
    " -codec:a copy {output_video}
    """
```

---

## Phase 3: Performance Optimizations

### 3.1 Backend Performance

| Optimization | Impact | Effort |
|--------------|--------|--------|
| Add connection pooling (PgBouncer) | High | Low |
| Add Redis caching for job status | Medium | Low |
| Add request rate limiting | High | Medium |
| Add response compression (gzip) | Medium | Low |

### 3.2 Frontend Performance

| Optimization | Impact | Effort |
|--------------|--------|--------|
| Add loading skeletons | High | Low |
| Add video preview thumbnails | Medium | Medium |
| Implement chunked uploads | High | High |
| Add service worker for offline | Low | Medium |

### 3.3 Database Performance

| Optimization | Impact | Effort |
|--------------|--------|--------|
| Add indexes on job_id, status | High | Low |
| Add pagination to /metrics | Medium | Low |
| Archive old completed jobs | Medium | Medium |

---

## Phase 4: Security Hardening

### 4.1 API Security

```
Step 1: Add API key authentication
├── Generate per-user API keys
├── Add X-API-Key header validation
└── Rate limit by API key

Step 2: Add CORS fine-tuning
├── Whitelist specific Vercel domains only
├── Remove allow_credentials for public API
└── Add CSP headers

Step 3: Add request validation
├── Validate file types (magic bytes)
├── Limit file sizes strictly
└── Add malware scanning (optional)
```

### 4.2 Infrastructure Security

```
Step 1: EC2 hardening
├── Use IAM roles (not access keys)
├── Add security groups (minimal ports)
├── Enable VPC endpoint for S3
└── Add CloudWatch monitoring

Step 2: Secrets management
├── Move to AWS Secrets Manager
├── Rotate access keys
└── Never commit .env to git
```

---

## Phase 5: Monitoring & Observability

### 5.1 Metrics to Track

| Metric | Why | How |
|--------|-----|-----|
| Upload success rate | Quality | Backend counter |
| Processing time p50/p95 | Performance | Backend histogram |
| Queue depth | Capacity | Redis SCARD |
| Error rate by type | Debugging | Backend counter |
| Active users | Engagement | Frontend analytics |

### 5.2 Alerts to Set Up

```
Critical (notify immediately):
├── Health check failing > 1 min
├── Error rate > 5%
└── Queue depth > 100

Warning (notify during business hours):
├── Processing time > 60s
├── Disk usage > 80%
└── Memory usage > 85%
```

### 5.3 Logging Strategy

```
Backend logs → CloudWatch
├── ERROR level for all exceptions
├── INFO level for key events
└── DEBUG level (disabled in prod)

Frontend errors → Sentry
├── Capture unhandled exceptions
├── Capture console errors
└── Track user sessions
```

---

## Phase 6: Cost Optimization

### 6.1 Current Monthly Costs

| Service | Current | Optimized |
|---------|---------|-----------|
| EC2 | ~$15 | ~$5 (8hr/day) |
| RDS | ~$0 (free tier) | ~$0 |
| S3 | ~$1 (storage + requests) | ~$1 |
| Redis | ~$0 (docker) | ~$5 (Upstash) |
| **Total** | **~$16/mo** | **~$11/mo** |

### 6.2 Cost Saving Actions

1. **EC2**: Use EventBridge to stop at 8PM, start at 8AM → 50% savings
2. **Redis**: Move to Upstash free tier (first 10k commands/day free)
3. **S3**: Add lifecycle rules to delete old files after 30 days
4. **MediaConvert**: Use only for large batch jobs, keep VideoSeal for realtime

---

## Implementation Priority

### Week 1: Quick Wins (Effort: 1 day)
- [ ] Add visible watermark fallback
- [ ] Add API rate limiting
- [ ] Add database indexes
- [ ] Set up EventBridge auto start/stop

### Week 2: Core Improvements (Effort: 3 days)
- [ ] Complete VideoSeal implementation
- [ ] Add connection pooling
- [ ] Set up CloudWatch monitoring
- [ ] Add Sentry error tracking

### Week 3: Polish (Effort: 2 days)
- [ ] Add loading skeletons
- [ ] Add chunked uploads
- [ ] Security hardening
- [ ] Documentation

### Week 4: Testing (Effort: 2 days)
- [ ] Load testing
- [ ] Security audit
- [ ] User acceptance testing
- [ ] Production deployment

---

## Estimated Timeline: 4 weeks

## Resources Needed

| Resource | Estimated Cost |
|----------|----------------|
| Development time | ~20 hours/week |
| Infrastructure (optimized) | ~$11/mo |
| External services (Sentry) | ~$0 (free tier) |
| Total | ~$11/mo + time |

---

## Questions to Answer Before Implementation

1. What's the expected daily video volume?
2. Is GPU processing required for processing time?
3. What's the retention period for videos?
4. Is user authentication required?
5. What's the budget for external services?
