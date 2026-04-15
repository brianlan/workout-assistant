# Workout Assistant — Finalized User Requirements

## 1. Core Goal

A **self-hosted, single-user web application** that serves as a personal workout video library and AI-powered plan generator. All videos are downloaded and stored locally. The user browses, plays, and organizes videos through a responsive web UI, and uses a form-based interface to generate workout plans from their library via an AI backend.

## 2. System Capabilities

### 2.1 Video Import & Storage
- Import workout videos from:
  - YouTube URLs
  - Direct video URLs
  - Social media URLs (e.g. Bilibili)
  - Local file uploads
- All remote videos are **downloaded to local disk** (not streamed from source)
- Each video gets a **user-assigned category** and optional metadata (title, description, difficulty, muscle groups)
- System auto-detects: duration, format, file size
- System auto-extracts a thumbnail from each video
- Videos are organized on the filesystem by category
- Import progress feedback (download progress for URLs, upload progress for files)
- Videos not in browser-playable format are **auto-transcoded to MP4/H.264+AAC** via ffmpeg
- yt-dlp format selection prefers H.264+AAC to minimize transcoding
- Non-playable videos that cannot be transcoded are rejected

### 2.2 Video Library & Playback
- Browse library in web UI with thumbnails, titles, categories
- Filter by category
- Search by title and description text
- Play videos in-browser using react-player
- Edit metadata (title, description, category, difficulty, muscle groups) after import
- Delete videos (removes file from disk and DB record)
- Videos deleted while referenced by plans show a "missing" indicator

### 2.3 Category Management
- Fully customizable categories — create, rename, delete
- Videos reassigned when categories change (directory renamed on disk)
- Delete category prompts user to reassign or remove associated videos

### 2.4 AI-Powered Workout Plan Generation
- Uses an **OpenAI-compatible API** with configurable base URL, API key, and model name
- **Form-based interface** (not chat): user selects plan parameters, system builds the prompt
- System generates rich prompt context: background, full video library listing with metadata, output format specification
- Plan parameters the user can specify:
  - **Plan granularity**: single session, weekly schedule, multi-week program
  - **Focus areas**: muscle groups or workout types to focus on
  - **Schedule preferences**: days per week, session duration
- Plans are composed of **videos from the user's library** (not free-text exercises)
- One-shot generation (not conversational iteration)
- User can regenerate if unsatisfied
- Generated plan is parsed into structured DB records (Plan → PlanItems)

### 2.5 Plan Tracking & Statistics
- Mark individual workout items as completed (done/not-done + date)
- Undo completion (mark as not-done)
- View current active plan with completion status for each item
- View plan history showing past plans and their completion status
- Statistics dashboard:
  - **Completion rate** (per plan/week)
  - **Category breakdown** (sessions per category)
  - **Visual charts** (bar/line charts via Recharts)

### 2.6 Settings
- Configure AI API: base URL, API key, model name
- Stored in `data/config.json`

## 3. Constraints

| Constraint | Detail |
|---|---|
| Single user | No authentication, no roles, no multi-tenancy |
| Offline-capable | All features work offline except AI plan generation |
| Local storage | Videos stored on local filesystem (~50-200 videos, up to ~100 GB) |
| Browser formats | Auto-transcode non-playable videos to MP4/H.264+AAC |
| yt-dlp | Used for YouTube, Bilibili, and other URL video downloading |
| No video editing | No manual editing or trimming; auto-transcode only |
| Serial downloads | One video download at a time |
| English language | All UI text and AI prompts in English |

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLModel, SQLite (WAL mode) |
| Frontend | React 19, Vite 8, TypeScript, Tailwind CSS |
| Video processing | yt-dlp (Python API), ffmpeg-python, ffprobe |
| Video player | react-player |
| Charts | Recharts |
| AI integration | httpx to OpenAI-compatible API |
| Testing | pytest, Vitest, Playwright |
| Deployment | Shell scripts, uvicorn |

## 5. Project Structure

Monorepo layout:
```
workout-assistant/
  backend/
    app/
    tests/
    pyproject.toml
  frontend/
    src/
    package.json
    vite.config.ts
  scripts/
    start.sh
    dev.sh
  data/  (gitignored)
```

Data storage:
```
data/
  videos/
    {category_name}/
      {uuid}.mp4
  thumbnails/
    {uuid}.jpg
  workout.db
  config.json
```

## 6. Deployment
- FastAPI serves both the API and built React static files (monolith)
- Dev mode: FastAPI + Vite dev server with proxy
- Production: `start.sh` builds frontend, starts uvicorn
- Configurable via environment variables (data dir, port; defaults: `./data/`, port 8000)

## 7. Non-Functional Requirements

- Library view loads within 2 seconds for up to 200 videos
- Video playback begins within 3 seconds
- AI plan generation completes within 30 seconds (network-dependent)
- Responsive web UI: 320px to 2560px width
- Clear visual feedback for all actions (loading states, success/error messages)
- Works on latest Chrome, Firefox, Safari (desktop and mobile)
- All features except AI plan generation work offline

## 8. Edge Cases

- Invalid/unreachable URL → clear error message with reason, offer retry
- AI API unreachable or error → display error, allow retry
- Video in plan deleted → plan shows "video unavailable" indicator
- Duplicate video (same source URL or identical file) → warn user, ask whether to proceed
- Low disk space during download → halt and notify user
- Video not browser-playable → auto-transcode to MP4/H.264+AAC
