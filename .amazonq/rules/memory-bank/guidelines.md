# TRACE — Development Guidelines

## Code Quality Standards

### Python (Backend)
- Every module, class, and public method has a docstring (`"""..."""`)
- Module-level docstring at the top of every `.py` file describing its purpose
- Class docstrings explain the responsibility and key design decisions (e.g., model name, algorithm used)
- Method docstrings include `Args:` and `Returns:` sections for non-trivial signatures
- Use `Optional[str]` / union types (`str | None`) — Python 3.10+ union syntax preferred in newer files, `Optional` in older ones
- All constants defined at module level in SCREAMING_SNAKE_CASE
- Guard heavy imports inside methods to defer them (e.g., `import subprocess` inside `process_video_frames`)

### TypeScript / React (Frontend)
- `"use client"` directive on every component that uses hooks or browser APIs — omit on pure server components
- Named exports for all components (no default component exports except page files)
- Page files (`app/*/page.tsx`, `app/layout.tsx`) use default exports as required by Next.js
- Types/interfaces defined in the same file where they are first used; shared types exported from their canonical component file (e.g., `RegisteredVideo` from `video-card.tsx`)
- `type` keyword preferred over `interface` for union/intersection shapes; `interface` for extensible object shapes
- `import type` used for type-only imports
- `React` namespace not imported — only specific hooks (`useState`, `useCallback`, etc.)

---

## Structural Conventions

### Frontend Component Structure
Components follow this consistent order:
1. `"use client"` (if needed)
2. Imports — type imports, then React/Next, then UI primitives, then icons, then utils
3. Module-level constants (ACCEPTED formats, MAX_BYTES, API URLs, static maps/arrays)
4. TypeScript type/interface definitions
5. Component function with props destructuring inline
6. State declarations at the top of the component
7. `useEffect` hooks
8. `useCallback` handlers
9. Helper functions (sync utilities like `validate`)
10. JSX return

### Python Module Structure
1. Module docstring
2. Standard library imports
3. Third-party imports
4. Local imports (`from backend.x import ...`)
5. Module-level constants and globals
6. Class definition (with docstring)
7. `__init__` with explicit typed parameters
8. Private methods prefixed with `_`
9. Public methods
10. Module-level async runner (guarded with `if __name__ == "__main__":`)

---

## Naming Conventions

### Python
- Classes: `PascalCase` (`WatermarkWorker`, `Upload`, `Settings`)
- Functions/methods: `snake_case`
- Private methods: `_snake_case` (single underscore)
- Constants: `SCREAMING_SNAKE_CASE` (`MODEL_PATH`, `VIDEO_SEAL_MODEL`)
- Pydantic model fields: `SCREAMING_SNAKE_CASE` for env vars (`AWS_ACCESS_KEY_ID`), `snake_case` for internal names (`trace_key_pem`)

### TypeScript
- Components: `PascalCase` function names exported as named exports
- Types/interfaces: `PascalCase` (`RegisteredVideo`, `UploadResponse`, `Status`)
- Local constants: `SCREAMING_SNAKE_CASE` for static config (`API_BASE_URL`, `MAX_BYTES`, `ACCEPTED`, `DMCA_URL`)
- State variables: `camelCase` (`isDragging`, `outputKey`, `pollIntervalRef`)
- Filter/union string types defined as `type X = "a" | "b"` literals

---

## API Design Patterns (FastAPI)

### Route Conventions
```python
@app.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ...

@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    ...

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

- Every endpoint has an explicit `response_model`
- Dependency injection via `Depends(get_db)` for DB sessions
- `HTTPException` raised with explicit `status_code` and `detail` string
- Celery failures are caught and logged but do not fail the parent HTTP request

### Response Models
Pydantic `BaseModel` subclasses for every response shape:
```python
class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str
    celery_task_id: Optional[str] = None
```
- All optional fields have `= None` defaults
- Status strings use consistent vocabulary: `"pending"`, `"processing"`, `"completed"`, `"failed"`, `"duplicate"`

### Error Handling Pattern
```python
try:
    # operation
except ClientError as e:          # specific AWS/external exception first
    result.update({"status": "failed", "error": str(e)})
except Exception as e:            # generic fallback
    result.update({"status": "failed", "error": f"Processing error: {str(e)}"})
```

---

## Database Patterns (SQLAlchemy 2.x)

### Model Definition
```python
class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```
- Use `Mapped[T]` + `mapped_column()` (SQLAlchemy 2.x declarative style)
- Timestamps always timezone-aware with `server_default=func.now()`
- UUIDs as primary keys via `UUID(as_uuid=True)` with `default=uuid.uuid4`
- Nullable columns declared with `nullable=True` in `mapped_column`

### Session Management
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
- Always use generator-based session yielding for FastAPI Depends
- `pool_pre_ping=True` on engine for connection health checks

### Query Functions
Standalone module-level functions (not methods) for DB operations:
```python
def check_duplicate(db, file_hash: str) -> Upload | None: ...
def save_upload(db, file_hash: str, s3_key: str, filename: str, job_id: Optional[str] = None) -> Upload: ...
def update_upload_status(db, job_id: str, status: str, output_key: Optional[str] = None, ...) -> ...: ...
```

---

## Frontend Patterns

### State Machine with Typed Status
Use a string union type as a status enum and derive boolean flags from it:
```tsx
type Status = "idle" | "uploading" | "processing" | "done" | "already-protected" | "error"

const isProtected = status === "already-protected"
const isDone = status === "done"
const isError = status === "error"
const isProcessing = status === "uploading" || status === "processing"
```

### API Communication
```tsx
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const response = await fetch(`${API_BASE_URL}/upload`, { method: "POST", body: formData })
if (!response.ok) {
  const errorData = await response.json()
  throw new Error(errorData.detail || "Upload failed")
}
const data: UploadResponse = await response.json()
```
- Always type the parsed JSON response explicitly
- `errorData.detail` matches FastAPI's `HTTPException` shape

### Polling Pattern
```tsx
const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

// Start polling
pollIntervalRef.current = setInterval(() => pollJobStatus(id), 2000)

// Stop on terminal state
if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)

// Cleanup on unmount
useEffect(() => {
  return () => { if (pollIntervalRef.current) clearInterval(pollIntervalRef.current) }
}, [])
```

### cn() Utility
Always use `cn()` from `@/lib/utils` for conditional class merging:
```tsx
import { cn } from "@/lib/utils"

className={cn(
  "base-classes",
  condition && "conditional-class",
  variant === "active" && "active-class",
)}
```

### Accessibility
- Interactive non-button divs get `role="button"`, `tabIndex={0}`, and `onKeyDown` handlers for Enter/Space
- Icons always have `aria-hidden="true"` since they are decorative
- Error messages use `role="alert"`
- Screen-reader-only labels use `className="sr-only"`

---

## Styling Conventions (Tailwind CSS v4)

### Design Token Usage
Always use semantic tokens, never raw colours:
| Token | Usage |
|-------|-------|
| `text-foreground` | Primary text |
| `text-muted-foreground` | Secondary/label text |
| `bg-background` | Page background |
| `bg-card` | Card surfaces |
| `bg-muted` | Subtle fills |
| `border-border` | Default borders |

### Status Colour Palette
| Status | Colour |
|--------|--------|
| Success / Active | `emerald-400` / `emerald-500/15` |
| Warning / Match | `amber-400` |
| Error / Failed | `red-400` / `red-500/15` |
| Protected / Safe | `teal-400` / `teal-500/10` |
| Info / Neutral | `muted-foreground` |

### Layout Patterns
- Max-width containers: `max-w-md` (forms/upload), `max-w-4xl` (dashboard)
- Page padding: `px-4 py-10` or `px-4 py-12`
- Card padding: `p-4` (metric cards), `p-5` (feature cards)
- Full-viewport minus nav: `min-h-[calc(100svh-57px)]`
- Sticky nav: `sticky top-0 z-10 border-b bg-background/80 backdrop-blur`

### Component Variants (shadcn/cva pattern)
UI primitives use `cva()` for variant definitions and always export both the component and `[component]Variants`:
```tsx
export { Button, buttonVariants }
export { Badge, badgeVariants }
```
Consumers use `buttonVariants()` directly when applying button styles to non-button elements (e.g., `<Link>`).

---

## Celery Task Patterns

```python
@celery_app.task(name="process_video_task", bind=True)
def process_video_task(self, job_id: str, s3_key: str, watermark_message: str):
    self.update_state(state="PROCESSING", meta={"progress": 10})
    # ... work ...
    self.update_state(state="SUCCESS", meta=result)
    return result
```
- `bind=True` for access to `self.update_state()`
- Progress reported as integer 0–100 in `meta={"progress": N}`
- Task name explicitly set (`name="process_video_task"`) to avoid auto-naming surprises
- WatermarkWorker instantiated inside the task (not at module level) to avoid serialisation issues

---

## Configuration Best Practices

- All secrets and environment-specific values go in `.env` (never hardcoded)
- `pydantic_settings.BaseSettings` with `class Config: env_file = ".env"` for Python
- `NEXT_PUBLIC_` prefix for any env var that must reach the browser
- Sensible defaults for non-secret values (`AWS_REGION = "us-east-1"`, `DATABASE_URL = "postgresql://localhost:5432/trace"`)
- Docker Compose passes all env vars explicitly via the `environment:` block
