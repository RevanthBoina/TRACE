# 1. OBJECTIVE

Build a FastAPI backend in the `backend/` folder of the TRACE repository (github.com/RevanthBoina/TRACE) with:
1. A `POST /upload` endpoint that accepts video files, computes SHA-256 hash, checks Postgres for duplicates, and uploads to S3
2. A `.env.example` file for environment variables (no real secrets)
3. A `requirements.txt` with all necessary Python packages

# 2. CONTEXT SUMMARY

**Repository:** github.com/RevanthBoina/TRACE (Next.js frontend)

**Current Repository Structure:**
```
TRACE/
├── app/              ← Next.js pages (already exists)
├── components/       ← UI components (already exists)
├── lib/              ← Utility functions (already exists)
├── package.json      ← Node dependencies (already exists)
└── [config files]    ← Various config files (already exists)
```

**New Files to Create:**
- `backend/main.py` - FastAPI application with POST /upload endpoint
- `backend/database.py` - PostgreSQL database connection and models
- `backend/config.py` - Environment variable configuration
- `.env.example` - Environment variable template (no secrets)
- `requirements.txt` - Python dependencies

**Environment Variables Required:**
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (e.g., us-east-1)
- `S3_UPLOAD_BUCKET` - S3 bucket name (trace-upload-temp)
- `DATABASE_URL` - PostgreSQL connection string

# 3. APPROACH OVERVIEW

1. **Create `backend/` directory** - Base directory for FastAPI code
2. **Create `backend/config.py`** - Load environment variables using pydantic-settings
3. **Create `backend/database.py`** - SQLAlchemy setup with a `uploads` table tracking file hashes and S3 keys
4. **Create `backend/main.py`** - FastAPI app with:
   - POST `/upload` endpoint accepting multipart video file
   - SHA-256 hash computation of file content
   - Duplicate check in PostgreSQL database
   - S3 upload using boto3 if not duplicate
   - Return job_id (UUID) with upload status
5. **Create `.env.example`** - Template with all required variables
6. **Create `requirements.txt`** - All Python dependencies

# 4. IMPLEMENTATION STEPS

### Step 1: Create backend/ directory and config.py
- **Goal:** Set up environment variable loading
- **Method:** 
  - Create `backend/__init__.py`
  - Create `backend/config.py` using pydantic-settings to load:
    - AWS credentials and region
    - S3 bucket name
    - DATABASE_URL
- **Reference:** `/workspace/project/TRACE/backend/config.py`

### Step 2: Create backend/database.py
- **Goal:** Set up PostgreSQL database connection and models
- **Method:**
  - Create SQLAlchemy engine and session
  - Define `Upload` model with columns:
    - `id` (UUID, primary key)
    - `file_hash` (String, SHA-256 hash, unique)
    - `s3_key` (String, S3 object key)
    - `filename` (String, original filename)
    - `created_at` (DateTime, timestamp)
    - `status` (String, upload status)
  - Create function to check if hash exists
  - Create function to save upload record
- **Reference:** `/workspace/project/TRACE/backend/database.py`

### Step 3: Create backend/main.py
- **Goal:** Create FastAPI app with POST /upload endpoint
- **Method:**
  - Import FastAPI, UploadFile, File, HTTPException
  - Import boto3 for S3 uploads
  - Import hashlib for SHA-256 computation
  - Import uuid for job_id generation
  - Import database functions
  - Import config settings
  - Create POST `/upload` endpoint that:
    1. Accepts `file: UploadFile = File(...)`
    2. Reads file content
    3. Computes SHA-256 hash
    4. Checks database for existing hash
    5. If exists: return existing job_id with "duplicate" status
    6. If not: uploads to S3 bucket, saves record, returns new job_id
  - Add CORS middleware for frontend
  - Add GET `/health` endpoint
- **Reference:** `/workspace/project/TRACE/backend/main.py`

### Step 4: Create .env.example
- **Goal:** Provide safe template for environment variables
- **Method:** Create file with template values (no real secrets):
  ```
  AWS_ACCESS_KEY_ID=your_key_here
  AWS_SECRET_ACCESS_KEY=your_secret_here
  AWS_REGION=us-east-1
  S3_UPLOAD_BUCKET=trace-upload-temp
  DATABASE_URL=postgresql://localhost:5432/trace
  ```
- **Reference:** `/workspace/project/TRACE/.env.example`

### Step 5: Create requirements.txt
- **Goal:** List all Python dependencies
- **Method:** Include:
  - fastapi
  - uvicorn[standard]
  - python-multipart (for file uploads)
  - boto3 (AWS SDK)
  - sqlalchemy
  - psycopg2-binary (PostgreSQL driver)
  - pydantic-settings (environment config)
  - python-dotenv (loading .env files)
- **Reference:** `/workspace/project/TRACE/requirements.txt`

# 5. TESTING AND VALIDATION

After implementation, verify:

1. **Directory Structure** - `backend/` should contain: `__init__.py`, `config.py`, `database.py`, `main.py`
2. **Environment Variables** - Code should use `os.getenv()` or pydantic-settings to load from environment
3. **File Hash** - SHA-256 computation should be deterministic (same file = same hash)
4. **Duplicate Detection** - If hash exists in database, should return existing job_id
5. **S3 Upload** - New files should upload to `trace-upload-temp` bucket with unique S3 key
6. **Response Format** - POST /upload should return JSON with job_id (UUID)
7. **Requirements** - All imports in requirements.txt should be pip-installable

**Note:** Runtime testing requires AWS credentials and PostgreSQL database to be configured.
