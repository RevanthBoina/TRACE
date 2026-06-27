# TRACE — Product Overview

## Purpose
TRACE is a video content protection platform that watermarks and fingerprints uploaded videos, then monitors the web for unauthorized copies. It enables creators and rights holders to detect and act on infringing uses of their content.

## Value Proposition
- Invisible digital watermarking embedded directly into video content
- Persistent fingerprinting for reliable re-identification even after re-encoding
- Automated background monitoring via registered platform URLs
- Actionable dashboard listing detected infringing links with confidence scores

## Key Features
- **Video Upload & Watermarking** — Users upload a video; the backend applies an invisible watermark using a PEM-keyed signing process and produces a fingerprinted output stored in S3.
- **Registration** — After upload, users register the canonical URL(s) where their video lives (YouTube, Instagram, etc.).
- **Infringement Dashboard** — Lists all registered videos with status (Active / Failed), last-scanned time, and a per-link table of detected copies with confidence percentages and detection dates.
- **Background Processing** — Watermark/fingerprint generation runs asynchronously via Celery workers backed by Redis, keeping the API responsive.
- **Take-down Workflow** — Dashboard surfaces infringing links so users can initiate take-down actions.

## Target Users
- Independent video creators (YouTube, Instagram)
- Media companies and studios protecting premium content
- Marketing teams tracking brand video distribution

## Core User Flows
1. Land on home page → upload video → receive watermarked copy
2. Register canonical platform URL(s) for the video
3. Visit dashboard → review scan results → act on infringing links
