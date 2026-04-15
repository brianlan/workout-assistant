# Workout Assistant — Implementation Plan

## Overview

9 milestones, TDD throughout (tests written first for every feature). Each milestone produces a testable, deployable increment.

---

## Milestone 0: Project Scaffolding

**Goal**: Monorepo structure with all tooling configured.

### Steps

1. Create directory structure:
   ```
   workout-assistant/
     backend/
       app/
         __init__.py
         main.py
         models.py
         database.py
         config.py
         routers/
           __init__.py
           videos.py
           categories.py
           plans.py
           settings.py
         services/
           __init__.py
           video_processor.py
           downloader.py
           ai_planner.py
       tests/
         conftest.py
         test_models.py
         test_video_processor.py
         test_downloader.py
         test_ai_planner.py
         test_api_videos.py
         test_api_categories.py
         test_api_plans.py
       pyproject.toml
     frontend/
       src/
         App.tsx
         main.tsx
         components/
         pages/
         api/
         types/
       package.json
       vite.config.ts
       tsconfig.json
       vitest.config.ts
     scripts/
       start.sh
       dev.sh
     e2e/
       playwright.config.ts
       specs/
     data/             # gitignored
     .gitignore
   ```

2. **Backend `pyproject.toml`**:
   - Dependencies: fastapi, uvicorn[standard], sqlmodel, aiosqlite, yt-dlp, ffmpeg-python, httpx, python-multipart, aiofiles
   - Dev dependencies: pytest, pytest-asyncio, pytest-cov
   - Python: >=3.13

3. **Frontend `package.json`**:
   - Dependencies: react, react-dom, react-router-dom, react-player, recharts
   - Dev dependencies: typescript, @types/react, @types/react-dom, vite, @vitejs/plugin-react, tailwindcss, @tailwindcss/vite, vitest, @testing-library/react, @testing-library/jest-dom, jsdom
   - E2E: @playwright/test (installed at root or frontend level)

4. **Vite config**: Proxy `/api` to FastAPI (localhost:8000) in dev mode

5. **`start.sh`**: Install deps if needed, build frontend (`npm run build`), copy output to `backend/static/`, start uvicorn serving API + static files

6. **`dev.sh`**: Start FastAPI (uvicorn --reload) and Vite dev server concurrently

7. **`.gitignore`**: `data/`, `backend/static/`, `__pycache__/`, `node_modules/`, `.env`

8. **Tailwind CSS**: Initialize with `@tailwindcss/vite` plugin, configure content paths

### Verification
- [ ] `cd backend && pytest` runs with 0 tests collected (no errors)
- [ ] `cd frontend && npm test` runs with 0 tests (no errors)
- [ ] `./scripts/dev.sh` starts both servers (FastAPI on :8000, Vite on :5173)
- [ ] Vite dev server proxies `/api/*` to FastAPI
- [ ] `./scripts/start.sh` builds frontend, starts production server

---

## Milestone 1: Database Models + Category Management

**Goal**: SQLite database with all entities, full category CRUD API + tests.

### TDD Cycle

1. **Write tests first** (`tests/test_models.py`):
   - Create Category, verify name uniqueness constraint
   - Create Video with all fields, verify FK to Category
   - Create Plan with PlanItems, verify FK to Video (nullable)
   - Query relationships: video.category, plan.items, item.video

2. **Write tests first** (`tests/test_api_categories.py`):
   - POST /categories with valid name → 201
   - POST /categories with duplicate name → 409
   - GET /categories → list of categories
   - GET /categories/{id} → single category
   - PUT /categories/{id} with new name → 200, name updated
   - DELETE /categories/{id} with no videos → 204
   - DELETE /categories/{id} with videos + reassignment → 204, videos reassigned

3. **Implement**:
   - `models.py`:
     ```python
     class Category(SQLModel, table=True):
         id: int | None = Field(default=None, primary_key=True)
         name: str = Field(unique=True, index=True)
         created_at: datetime

     class Video(SQLModel, table=True):
         id: int | None = Field(default=None, primary_key=True)
         title: str
         description: str | None = None
         category_id: int = Field(foreign_key="category.id")
         difficulty: str | None = None  # beginner/intermediate/advanced
         muscle_groups: str | None = None  # JSON list
         duration: float | None = None  # seconds
         format: str | None = None
         file_size: int | None = None  # bytes
         thumbnail_path: str | None = None
         file_path: str
         source_url: str | None = None
         status: str = "importing"  # importing/transcoding/ready/failed
         imported_at: datetime

     class Plan(SQLModel, table=True):
         id: int | None = Field(default=None, primary_key=True)
         title: str
         plan_type: str  # single_session/weekly/multi_week
         parameters: str  # JSON: focus_areas, days_per_week, duration_weeks
         created_at: datetime

     class PlanItem(SQLModel, table=True):
         id: int | None = Field(default=None, primary_key=True)
         plan_id: int = Field(foreign_key="plan.id")
         video_id: int | None = Field(default=None, foreign_key="video.id")
         day_position: int
         order_position: int
         completed: bool = False
         completed_at: datetime | None = None
     ```
   - `database.py`: SQLite connection with WAL mode, `create_db_and_tables()` on startup, session dependency
   - `config.py`: Settings class with data_dir, port defaults
   - `routers/categories.py`: Full CRUD with reassignment logic on delete

### Verification
- [ ] All model tests pass
- [ ] All category API tests pass
- [ ] SQLite file created at `data/workout.db`
- [ ] WAL mode enabled

---

## Milestone 2: Video Import (File Upload)

**Goal**: Upload a local video file, store on disk, detect metadata, extract thumbnail, auto-transcode if needed.

### TDD Cycle

1. **Write tests first** (`tests/test_video_processor.py`):
   - `is_web_compatible(mp4_h264_aac)` → True
   - `is_web_compatible(webm_vp9)` → False
   - `is_web_compatible(mkv_h265)` → False
   - `extract_thumbnail(video_path)` → valid JPEG file exists
   - `extract_thumbnail(short_video)` → valid JPEG (from first frame)
   - `get_video_metadata(video_path)` → dict with duration, format, file_size
   - `transcode_video(input_path, output_path)` → output is H.264+AAC MP4 with faststart

2. **Write tests first** (`tests/test_api_videos.py` — upload portion):
   - POST /videos/upload with MP4 file + category → 201, file on disk, DB record status=ready, thumbnail exists
   - POST /videos/upload with WebM file + category → 201, status=transcoding
   - POST /videos/upload with metadata → fields stored in DB
   - POST /videos/upload with no title → title derived from filename
   - POST /videos/upload with invalid category → 400

3. **Implement**:
   - `services/video_processor.py`:
     - `is_web_compatible(file_path) → bool`: ffprobe check for H.264+AAC in MP4
     - `extract_thumbnail(file_path, output_path)`: ffmpeg extract at 25% duration, fallback to frame 1
     - `get_video_metadata(file_path) → dict`: ffprobe for duration, format, file_size
     - `transcode_video(input_path, output_path)`: ffmpeg with `-preset veryfast -crf 23 -movflags +faststart`
     - `ensure_faststart(input_path)`: `ffmpeg -c copy -movflags +faststart` (for already-compatible files)
   - `routers/videos.py` — upload endpoint:
     - Stream file to temp location
     - Probe format
     - If compatible: move to `data/videos/{category}/{uuid}.mp4`, ensure faststart
     - If not compatible: queue background transcode, status=transcoding
     - Extract thumbnail, record metadata in DB

### Verification
- [ ] All video_processor tests pass
- [ ] Upload MP4 → immediately ready, playable
- [ ] Upload WebM/MKV → transcoded to MP4 → ready
- [ ] Thumbnails generated for all uploads
- [ ] Files stored in correct category directories

---

## Milestone 3: Video Import (URL Download)

**Goal**: Submit a URL, download via yt-dlp, process same as upload.

### TDD Cycle

1. **Write tests first** (`tests/test_downloader.py`):
   - yt-dlp options include `-S "vcodec:h264,res,acodec:aac"` and `--merge-output-format mp4`
   - Progress hook called with correct status transitions
   - Invalid URL raises DownloadError with clear message
   - Duplicate source URL detected from DB

2. **Write tests first** (`tests/test_api_videos.py` — URL portion):
   - POST /videos/import-url with valid URL → 202, job created
   - GET /videos/{id} shows status=importing initially
   - After download completes, status=transcoding or ready
   - POST /videos/import-url with duplicate URL → 409 warning
   - POST /videos/import-url with invalid URL → 400

3. **Implement**:
   - `services/downloader.py`:
     - `download_video(url, output_dir, progress_callback)`: yt-dlp wrapper with format preferences
     - Progress hook: update DB status, report download percentage
     - Error handling: catch yt-dlp exceptions, return clear error messages
   - `routers/videos.py` — URL import endpoint:
     - Check for duplicate source_url in DB
     - Create Video record with status=importing
     - Queue background download task
     - After download: run video_processor pipeline (format check, transcode if needed, thumbnail)
   - Serial download queue: simple asyncio queue or in-memory task tracker (one at a time)

### Verification
- [ ] All downloader tests pass
- [ ] YouTube URL → downloads as MP4 → appears in library
- [ ] Bilibili URL → downloads as MP4 → appears in library
- [ ] Invalid URL → clear error message
- [ ] Duplicate URL → warning
- [ ] Serial: second URL waits for first to complete

---

## Milestone 4: Video Library API

**Goal**: Full video library API — browse, search, filter, stream, edit, delete.

### TDD Cycle

1. **Write tests first** (`tests/test_api_videos.py` — library portion):
   - GET /videos → paginated list (default page size 20)
   - GET /videos?category_id=X → filtered results
   - GET /videos?search=keyword → search title + description
   - GET /videos?category_id=X&search=keyword → combined filter
   - GET /videos/{id}/stream → 200 with Content-Type video/mp4
   - GET /videos/{id}/stream with Range header → 206 Partial Content
   - GET /videos/{id}/thumbnail → 200 with image/jpeg
   - PUT /videos/{id} with new metadata → 200, fields updated
   - PUT /videos/{id} with new category_id → file moved to new directory
   - DELETE /videos/{id} → 204, file removed, thumbnail removed, DB record removed
   - DELETE video referenced by plan item → plan item.video_deleted = True

2. **Implement**:
   - List endpoint: SQLModel query with optional category filter, text search (LIKE), pagination (offset/limit)
   - Stream endpoint: `FileResponse` with `media_type="video/mp4"` (handles range requests automatically)
   - Thumbnail endpoint: `FileResponse` for JPEG
   - Edit endpoint: update fields; if category changes, move file and update directory
   - Delete endpoint: remove file, thumbnail, DB record; update any plan items referencing this video (set video_id=None, add video_deleted flag or check at query time)

### Verification
- [ ] All library API tests pass
- [ ] Streaming supports seeking (range requests)
- [ ] Search and filter work correctly
- [ ] Delete cleans up all files
- [ ] Plan items referencing deleted video show missing indicator

---

## Milestone 5: Frontend — Video Library UI

**Goal**: React UI for browsing, searching, filtering, importing, and playing videos.

### Steps

1. **Set up routing and layout**:
   - React Router with routes: `/` (library), `/plans`, `/plans/history`, `/stats`, `/settings`
   - Layout: sidebar navigation (desktop) / hamburger menu (mobile)
   - Responsive shell with Tailwind breakpoints

2. **Library page**:
   - Grid of video cards (thumbnail, title, category badge, duration)
   - Category filter sidebar (desktop) / dropdown (mobile)
   - Search bar with debounce
   - Responsive grid: 1 col (<640px), 2 col (640-1024px), 3-4 col (>1024px)
   - Empty state when no videos

3. **Import dialog/modal**:
   - Two tabs: File Upload / URL Import
   - Category selector (required)
   - Optional fields: title, description, difficulty (dropdown), muscle groups (multi-select or tags)
   - File upload: drag-and-drop zone, progress bar
   - URL import: text input for URL, progress indicator
   - Submit → API call → refresh library

4. **Video detail/player page**:
   - react-player for playback
   - Metadata display: title, description, category, difficulty, muscle groups, duration
   - Edit button → inline form for metadata
   - Delete button → confirmation dialog
   - Back to library

5. **Type definitions** (`types/`):
   - Video, Category, Plan, PlanItem, Settings interfaces matching backend models

6. **API client** (`api/`):
   - Typed fetch wrappers for all backend endpoints
   - Error handling with toast notifications

### TDD
- Vitest: component rendering tests for library grid, import dialog, player page
- Playwright E2E-01 (file import), E2E-02 (URL import), E2E-03 (browse & play)

### Verification
- [ ] Can browse library with thumbnails
- [ ] Can filter by category and search by text
- [ ] Can import video via file upload
- [ ] Can import video via URL
- [ ] Can play video in browser
- [ ] Can edit video metadata
- [ ] Can delete video
- [ ] Responsive at 320px, 768px, 1920px

---

## Milestone 6: AI Plan Generation (Backend)

**Goal**: Form-based plan generation using OpenAI-compatible API. System builds prompt, sends to LLM, parses response into structured DB records.

### TDD Cycle

1. **Write tests first** (`tests/test_ai_planner.py`):
   - `build_prompt(library, params)` includes:
     - System role description
     - Full video library listing (id, title, category, difficulty, duration, muscle_groups)
     - User parameters (plan_type, focus_areas, days_per_week, duration_weeks)
     - Output JSON schema specification
   - `parse_response(valid_json)` creates Plan + PlanItems referencing real video IDs
   - `parse_response(malformed_json)` raises ParseError with details
   - `parse_response(plan_with_invalid_video_ids)` raises error listing invalid IDs
   - `call_llm()` with mocked httpx: timeout → raises AIClientError
   - `call_llm()` with mocked httpx: 401 → raises AIAuthError
   - `call_llm()` with mocked httpx: 500 → raises AIServerError

2. **Write tests first** (`tests/test_api_plans.py`):
   - POST /plans/generate with valid params + mocked LLM → 201, plan with items
   - GET /plans → list of plans
   - GET /plans/{id} → plan detail with items, video info, completion status
   - POST /plans/{id}/regenerate → new plan created

3. **Implement**:
   - `services/ai_planner.py`:
     - `build_prompt(videos: list[Video], params: PlanParams) → list[dict]`:
       - System message: "You are a workout plan generator..."
       - User message: library listing + parameters + output format
       - Output format: JSON schema specifying plan structure with video_id references
     - `call_llm(config: AIConfig, messages: list[dict]) → str`:
       - httpx POST to `{base_url}/chat/completions`
       - Headers: Authorization: Bearer {api_key}
       - Body: model, messages, temperature
     - `parse_response(response_text: str, valid_video_ids: set[int]) → (PlanCreate, list[PlanItemCreate])`:
       - Parse JSON from LLM response
       - Validate video IDs exist in library
       - Return structured plan data
   - `routers/plans.py`:
     - POST /plans/generate: accept params, build prompt, call LLM, parse, save to DB
     - GET /plans: list all plans
     - GET /plans/{id}: full plan with items
     - POST /plans/{id}/regenerate: same params, new LLM call
   - Settings storage: `data/config.json` for API config

### Verification
- [ ] All AI planner tests pass with mocked LLM
- [ ] Plan generation with real API produces valid plan with library videos
- [ ] Malformed LLM responses handled gracefully
- [ ] API errors return clear messages to user

---

## Milestone 7: Plan Tracking & History + Statistics

**Goal**: Mark items done/undone, view active plan, view history, completion statistics with charts.

### TDD Cycle

1. **Write tests first** (backend):
   - PATCH /plans/{id}/items/{item_id} with completed=true → sets completed_at
   - PATCH /plans/{id}/items/{item_id} with completed=false → clears completed_at
   - GET /plans/active → current active plan
   - GET /plans/history → past plans with completion percentages
   - GET /plans/stats → { completion_rate, category_breakdown }

2. **Write tests first** (frontend):
   - Plan page renders items with checkboxes
   - Clicking checkbox triggers API call and updates state
   - History page lists past plans
   - Stats page renders Recharts components

3. **Implement backend**:
   - Completion toggle endpoint
   - Active plan endpoint (most recent plan)
   - History endpoint (all plans with computed completion %)
   - Stats endpoint: aggregate completion rate by week, category distribution
   - Settings CRUD: GET/PUT /settings for API config

4. **Implement frontend**:
   - **Plan page**: Display active plan as schedule/day view
     - Days as sections, items within each day
     - Checkboxes for completion, click to toggle
     - Progress bar showing overall completion
     - "Regenerate" button
   - **History page**: List of past plans
     - Each plan shows title, date, completion %, number of items
     - Click to expand and see item-level details
   - **Stats page**: Dashboard with charts
     - Bar chart: completion rate over time (per week)
     - Pie chart: category breakdown (sessions per category)
     - Recharts responsive containers
   - **Settings page**: Form for API configuration
     - Base URL, API key (masked input), model name
     - Test connection button
     - Save to config.json via API

### TDD
- Vitest: plan page, history page, stats page, settings page component tests
- Playwright E2E-04 (plan generation), E2E-05 (tracking), E2E-07 (stats), E2E-08 (settings)

### Verification
- [ ] Can toggle item completion, date recorded/cleared
- [ ] Progress bar updates correctly
- [ ] History shows past plans with completion %
- [ ] Stats charts render with real data
- [ ] Settings persist and reload correctly

---

## Milestone 8: Category Management UI + Polish

**Goal**: Category management UI, responsive polish, edge case handling, error states.

### Steps

1. **Category management page**:
   - List all categories with video counts
   - Create new category (name input + button)
   - Inline rename (click name to edit)
   - Delete with modal: "Reassign videos to [dropdown] or delete all"
   - Category list also appears as filter in library sidebar

2. **Error handling UI**:
   - Toast notification system (success, error, warning, info)
   - Loading spinners for async operations
   - Import progress bar (download progress from yt-dlp)
   - Transcoding status indicator on video cards
   - "AI features unavailable" banner when API unreachable
   - Network error retry prompts

3. **Edge case handling**:
   - Duplicate video warning dialog (import anyway / cancel)
   - Low disk space detection before download
   - Missing video indicator in plans (deleted video icon + "Video unavailable" text)
   - Empty states for all pages (no videos, no plans, no categories)
   - Long title truncation with ellipsis

4. **Responsive polish**:
   - Test at: 320px, 375px, 768px, 1024px, 1440px, 1920px, 2560px
   - Mobile: hamburger menu, single column, bottom-friendly touch targets
   - Tablet: two-column layout
   - Desktop: sidebar navigation, multi-column grid
   - Ensure no horizontal scroll at any width
   - Touch-friendly: minimum 44px touch targets on mobile

### TDD
- Playwright E2E-06 (category management), E2E-09 (responsive), E2E-10 (offline behavior)

### Verification
- [ ] Category CRUD works in UI
- [ ] Delete with reassignment works correctly
- [ ] Error toasts appear for failed operations
- [ ] Import progress shown during download
- [ ] Transcoding status visible on video cards
- [ ] Missing video indicator in plans
- [ ] No horizontal scroll at 320px
- [ ] Effective layout at 1920px

---

## Milestone 9: Deployment + Documentation

**Goal**: Production-ready startup, deployment scripts, project documentation.

### Steps

1. **Production build**:
   - Vite `build` outputs to `frontend/dist/`
   - `start.sh` copies `frontend/dist/` to `backend/static/`
   - FastAPI mounts static files: `app.mount("/", StaticFiles(directory="static", html=True))`
   - API routes mounted at `/api/*`
   - SPA fallback: all non-API routes serve `index.html`

2. **`start.sh`**:
   ```bash
   #!/bin/bash
   set -e
   cd frontend && npm install && npm run build
   cp -r dist/ ../backend/static/
   cd ../backend
   pip install -e ".[dev]" 2>/dev/null || pip install -e .
   uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```

3. **`dev.sh`**:
   ```bash
   #!/bin/bash
   set -e
   # Start FastAPI in background
   (cd backend && uvicorn app.main:app --reload --port 8000) &
   # Start Vite dev server
   cd frontend && npm run dev -- --proxy /api:http://localhost:8000
   ```

4. **Configuration**:
   - Environment variables: `DATA_DIR` (default: `./data`), `PORT` (default: 8000)
   - `data/config.json` for AI API settings (created on first use)

5. **`CLAUDE.md`**: Project conventions, test commands, dev workflow

6. **Final test run**: All unit, integration, and E2E tests pass

### Verification
- [ ] `./scripts/start.sh` starts the app in production mode
- [ ] Accessible at `http://localhost:8000`
- [ ] API at `http://localhost:8000/api/*`
- [ ] Frontend SPA routing works (direct URLs load correctly)
- [ ] `./scripts/dev.sh` starts both servers with hot reload
- [ ] Accessible from another device on same network
- [ ] All tests pass: `pytest`, `npm test`, `npx playwright test`

---

## Dependency Graph

```
M0 (scaffolding)
 ├─→ M1 (models + categories)
 │    ├─→ M2 (video upload)
 │    │    └─→ M3 (URL download)
 │    │         └─→ M4 (library API)
 │    │              └─→ M5 (library UI)
 │    │                   └─→ M7 (tracking + stats UI)
 │    ├─→ M6 (AI plan generation)
 │    │    └─→ M7 (tracking + stats UI)
 │    └─→ M8 (category UI + polish)
 └─→ M9 (deployment)
```

M6 and M2-M5 can proceed in parallel after M1 is complete.
M8 can proceed after M1 but benefits from M5 being done.
M9 is last after all others are complete.
