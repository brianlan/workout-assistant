# Workout Assistant — Validation Criteria & Acceptance Tests

## 1. Test Infrastructure

| Layer | Framework | Location |
|---|---|---|
| Backend unit/integration | pytest + pytest-asyncio | `backend/tests/` |
| Frontend unit | Vitest | `frontend/src/` (co-located) |
| End-to-end | Playwright | `frontend/e2e/` or root `e2e/` |

All tests must pass before any milestone is considered complete.

---

## 2. Unit Tests (pytest — Backend)

### 2.1 Video Format Detection (`test_video_processor.py`)
- [ ] `is_web_compatible()` returns `True` for H.264+AAC MP4
- [ ] `is_web_compatible()` returns `False` for VP9/WebM
- [ ] `is_web_compatible()` returns `False` for HEVC (H.265)
- [ ] `is_web_compatible()` returns `False` for non-MP4 containers
- [ ] `extract_thumbnail()` produces valid JPEG file from video
- [ ] `extract_thumbnail()` handles very short videos (< 5 seconds)
- [ ] `get_video_metadata()` returns correct duration, format, file size
- [ ] Transcode function produces H.264+AAC MP4 with faststart from WebM input

### 2.2 yt-dlp Downloader (`test_downloader.py`)
- [ ] Format selection options prefer H.264+AAC (`-S "vcodec:h264,res,acodec:aac"`)
- [ ] Merge output format is set to MP4
- [ ] Progress hook correctly updates video status in DB
- [ ] Invalid URL returns clear error with reason
- [ ] Duplicate source URL detection works

### 2.3 Database Models (`test_models.py`)
- [ ] Create/read/update/delete Category
- [ ] Create/read/update/delete Video with all metadata fields
- [ ] Create Plan with PlanItems referencing Videos
- [ ] Video-Category foreign key relationship
- [ ] PlanItem-Video foreign key relationship (nullable for deleted videos)
- [ ] Category name uniqueness constraint

### 2.4 AI Prompt Builder (`test_ai_planner.py`)
- [ ] `build_prompt()` includes video library context (all videos with categories and metadata)
- [ ] `build_prompt()` includes user parameters (granularity, focus areas, schedule)
- [ ] `build_prompt()` includes output format specification (JSON schema)
- [ ] `parse_response()` correctly parses valid LLM JSON into Plan + PlanItem records
- [ ] `parse_response()` handles malformed/incomplete responses gracefully
- [ ] `parse_response()` rejects plan items referencing non-existent video IDs
- [ ] API error handling: timeout returns clear error
- [ ] API error handling: 401 returns clear error
- [ ] API error handling: 500 returns clear error

### 2.5 Duplicate Detection
- [ ] Same source URL triggers warning
- [ ] Identical file hash triggers warning

---

## 3. Integration Tests (pytest — Backend API)

### 3.1 File Upload Flow (`test_api_videos.py`)
- [ ] POST /videos/upload with MP4 → 201, file on disk, DB record with status=ready, thumbnail generated
- [ ] POST /videos/upload with WebM → 201, status=transcoding, eventually status=ready after transcode
- [ ] Upload assigns to correct category directory
- [ ] Upload with metadata (title, description, difficulty, muscle_groups) stored correctly
- [ ] Upload without optional metadata uses defaults (title from filename)

### 3.2 URL Import Flow
- [ ] POST /videos/import-url with valid URL → 202 (accepted, async processing)
- [ ] Polling GET /videos/{id}/status returns importing → (transcoding) → ready
- [ ] Invalid URL returns 400 with clear error message
- [ ] Duplicate URL returns 409 with warning

### 3.3 Video Library API
- [ ] GET /videos returns paginated list with thumbnails, titles, categories
- [ ] GET /videos?category=X filters correctly
- [ ] GET /videos?search=keyword searches title and description
- [ ] GET /videos/{id}/stream supports HTTP range requests (seeking)
- [ ] GET /videos/{id}/thumbnail returns JPEG image
- [ ] PUT /videos/{id} updates metadata; changing category moves file on disk
- [ ] DELETE /videos/{id} removes file, thumbnail, DB record
- [ ] Deleted video referenced by plan items → plan items show video_deleted=True

### 3.4 Category API (`test_api_categories.py`)
- [ ] POST /categories → 201, category created
- [ ] GET /categories → list all categories
- [ ] PUT /categories/{id} → rename category, videos updated, directory renamed
- [ ] DELETE /categories/{id} → prompt reassignment, videos reassigned, directory renamed
- [ ] Duplicate category name → 409

### 3.5 Plan API (`test_api_plans.py`)
- [ ] POST /plans/generate with parameters → plan created with items referencing real library videos
- [ ] POST /plans/generate with mocked LLM → structured plan matches expected format
- [ ] GET /plans → list all plans
- [ ] GET /plans/{id} → full plan with items, video details, completion status
- [ ] PATCH /plans/{id}/items/{item_id} toggle completion → sets/clears completed_at
- [ ] POST /plans/{id}/regenerate → new plan created with different items
- [ ] GET /plans/history → past plans with completion percentages
- [ ] GET /plans/stats → completion rate and category breakdown

### 3.6 Settings API
- [ ] GET /settings → current API config (key masked)
- [ ] PUT /settings → save API base URL, key, model name to config.json

---

## 4. Frontend Unit Tests (Vitest)

### 4.1 Component Rendering
- [ ] Library grid renders video cards with thumbnails, titles, categories
- [ ] Plan view renders items with checkboxes and video info
- [ ] Settings form renders API configuration fields
- [ ] Stats page renders Recharts components

### 4.2 Search & Filter
- [ ] Category filter produces correct filtered results
- [ ] Text search produces correct filtered results
- [ ] Combined filter + search works

### 4.3 Plan Form
- [ ] Form validates required fields (granularity)
- [ ] Form collects optional fields (focus areas, schedule preferences)
- [ ] Submit triggers correct API call with expected payload

### 4.4 State Management
- [ ] Video list state updates after import
- [ ] Plan state updates after completion toggle
- [ ] Settings state persists across navigation

---

## 5. End-to-End Tests (Playwright)

### E2E-01: Full File Import Flow
1. Open library page
2. Click import button
3. Select file upload tab
4. Upload a test MP4 file
5. Assign category from dropdown
6. Fill optional metadata
7. Submit
8. Verify: video card appears in library grid with thumbnail, title, category
9. Verify: video file exists on disk in correct category directory

### E2E-02: URL Import Flow
1. Open library page
2. Click import button
3. Select URL tab
4. Paste a test video URL
5. Assign category
6. Submit
7. Verify: progress indicator shown
8. Verify: video card appears in library when download completes

### E2E-03: Library Browse & Play
1. Browse library — verify grid of video cards
2. Select category filter — verify only matching videos shown
3. Type search keyword — verify filtered results
4. Click a video card
5. Verify: video player page opens
6. Verify: video plays in browser
7. Click edit, change metadata, save — verify updated
8. Go back to library — verify changes reflected

### E2E-04: Plan Generation
1. Navigate to Plans page
2. Click "Generate Plan"
3. Fill form: granularity=weekly, focus areas=legs, days_per_week=3
4. Submit
5. Verify: plan displayed with videos from library organized by day
6. Verify: each item shows video title, thumbnail, category
7. Click "Regenerate" — verify new plan generated

### E2E-05: Plan Tracking
1. View active plan
2. Mark first item as completed
3. Verify: item shows checkmark and today's date
4. Verify: plan progress bar updates
5. Mark item as un-done
6. Verify: completion date cleared, progress bar updates
7. Navigate to History — verify plan listed with completion status

### E2E-06: Category Management
1. Navigate to Categories page
2. Create new category "Test Category"
3. Verify: appears in list
4. Rename to "Renamed Category"
5. Verify: videos in that category updated
6. Delete category with reassignment to another category
7. Verify: videos reassigned, directory structure updated

### E2E-07: Statistics
1. Complete several plan items across different categories
2. Navigate to Stats page
3. Verify: completion rate chart shows data
4. Verify: category breakdown chart shows data
5. Verify: date range filter works

### E2E-08: Settings
1. Navigate to Settings page
2. Enter API base URL, API key, model name
3. Save
4. Reload page
5. Verify: settings persisted (key masked)

### E2E-09: Responsive Layout
1. Resize browser to 320px width
2. Verify: no horizontal scroll, all controls accessible, hamburger menu
3. Resize to 768px (tablet)
4. Verify: layout adapts (2 columns)
5. Resize to 1920px (desktop)
6. Verify: full layout with sidebar, 3-4 column grid

### E2E-10: Offline Behavior
1. Block AI API endpoint (network interception)
2. Attempt plan generation
3. Verify: "AI features unavailable" message displayed
4. Browse library, play video — verify all works
5. Verify: no crashes or errors from missing AI connection

---

## 6. Manual Verification Steps

| # | Step | Expected Result |
|---|---|---|
| M-01 | Run `./scripts/start.sh` | Both backend and frontend serve; accessible at localhost:8000 |
| M-02 | Run `./scripts/dev.sh` | Hot reload works for both backend and frontend |
| M-03 | Import a real YouTube URL | Video downloads, appears in library, plays in browser |
| M-04 | Import a real Bilibili URL | Video downloads, appears in library, plays in browser |
| M-05 | Upload a local MP4 file | File stored, metadata recorded, plays in browser |
| M-06 | Upload a non-MP4 file (e.g. MKV) | Auto-transcoded to MP4, plays in browser |
| M-07 | Access from phone browser (same network) | UI renders and is usable at mobile width |
| M-08 | Disconnect network, browse library | Everything except plan generation works |
| M-09 | Disconnect network, attempt plan generation | Clear "AI unavailable" message, can retry |
| M-10 | Run all tests: `pytest && npm test && npx playwright test` | All tests pass |

---

## 7. Acceptance Criteria (from REQUIREMENTS.md)

| ID | Criterion | Covered By |
|---|---|---|
| AC-01 | Import local video → stored on disk, playable in browser | E2E-01, Integration 3.1 |
| AC-02 | Import YouTube URL → downloaded, playable | E2E-02, Integration 3.2 |
| AC-03 | Import social media URL → downloaded, playable | E2E-02, Integration 3.2 |
| AC-04 | Browse library filtered by category | E2E-03, Integration 3.3 |
| AC-05 | Search library by title | E2E-03, Integration 3.3 |
| AC-06 | Generate single-session plan | E2E-04, Integration 3.5 |
| AC-07 | Generate weekly plan | E2E-04, Integration 3.5 |
| AC-08 | Generate multi-week plan | E2E-04, Integration 3.5 |
| AC-09 | Regenerate plan | E2E-04, Integration 3.5 |
| AC-10 | Mark plan item completed with date | E2E-05, Integration 3.5 |
| AC-11 | View plan history | E2E-05, Integration 3.5 |
| AC-12 | UI usable at 320px | E2E-09 |
| AC-13 | UI effective at 1920px | E2E-09 |
| AC-14 | Offline: library, playback, tracking work | E2E-10, M-08 |
| AC-15 | Offline: AI shows clear error | E2E-10, M-09 |
| AC-16 | Category CRUD with video reassignment | E2E-06, Integration 3.4 |
| AC-17 | Deleted video in plan shows missing indicator | Integration 3.3 |
