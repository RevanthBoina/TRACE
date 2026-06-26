# OpenHands Agent Memory for TRACE Project

## 🚀 Deployment: Vercel
- **GitHub Repo**: `RevanthBoina/TRACE`
- **Vercel URL**: https://vercel.com/import/git?utm_source=github&utm_campaign=oss
- Project is deployed on Vercel for 24/7 uptime

## 🔐 Secrets Management (Vercel Environment Variables)
All secrets are stored in **Vercel Dashboard** → Project Settings → Environment Variables:
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (e.g., us-east-1)
- `S3_UPLOAD_BUCKET` - S3 upload bucket name
- `S3_OUTPUT_BUCKET` - S3 output bucket name
- `DATABASE_URL` - PostgreSQL connection string
- `RESEND_API_KEY` - Email service API key
- `trace_key_pem` - **PEM private key value** (saved as environment variable, not file path)

## PEM Key File
- The PEM private key is stored as Vercel env var `trace_key_pem` (not as a file)
- In code: read from `process.env.trace_key_pem`
- For local development: `/workspace/trace-key.pem` contains the same key

## Local Development Setup
- `.env` file at `/workspace/project/TRACE/.env` uses variable references
- For local dev, PEM file at `/workspace/trace-key.pem` is used
- For production (Vercel): use `process.env.trace_key_pem`

## Notes
- Vercel auto-injects env vars at build/run time
- No need to manage secrets manually - Vercel handles 24/7 availability
