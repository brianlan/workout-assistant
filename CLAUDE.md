# Workout Assistant — Project Conventions

## Project Overview
Self-hosted workout video library with AI-powered plan generation. Monorepo with Python/FastAPI backend and React/Vite/TypeScript frontend.

## Architecture
- **Backend**: FastAPI + SQLModel + SQLite (WAL mode), Python 3.13+
- **Frontend**: React 19 + Vite + TypeScript + Tailwind CSS v4
- **Video processing**: yt-dlp, ffmpeg/ffprobe
- **AI integration**: httpx to OpenAI-compatible API
- **Testing**: pytest (backend), Vitest (frontend), Playwright (E2E)
- **Deployment**: Shell scripts, uvicorn monolith

## Commands

### Backend
```bash
cd backend
pip install -e ".[dev]"
pytest                          # Run all backend tests
pytest -v                       # Verbose output
pytest tests/test_models.py     # Run specific test file
pytest --cov=app                # Coverage report
```

### Frontend
```bash
cd frontend
npm install
npm test                        # Run Vitest tests
npm run test:watch              # Watch mode
npm run build                   # Production build
npm run dev                     # Dev server with HMR
```

### E2E
```bash
# Start the app first (start.sh or dev.sh)
npx playwright test             # Run E2E tests from project root
npx playwright test --ui        # Interactive UI mode
```

### Development
```bash
./scripts/dev.sh                # Start both servers (FastAPI :8000, Vite :5173)
```

### Production
```bash
./scripts/start.sh              # Build frontend, start monolith on :8000
```

## Directory Structure
```
backend/
  app/
    main.py          # FastAPI app entry point
    models.py        # SQLModel database models
    database.py      # SQLite connection, WAL mode
    config.py        # Settings (DATA_DIR, PORT)
    routers/         # API endpoint handlers
      categories.py  # /api/categories
      videos.py      # /api/videos
      plans.py       # /api/plans
      settings.py    # /api/settings
    services/        # Business logic
      video_processor.py  # Format detection, transcoding, thumbnails
      downloader.py       # yt-dlp wrapper
      ai_planner.py       # Prompt building, LLM calls, response parsing
  tests/             # Backend tests
frontend/
  src/
    api/client.ts    # Typed fetch wrappers
    types/index.ts   # TypeScript interfaces
    pages/           # Page components
    App.tsx          # Router + layout
frontend/e2e/        # E2E test specs (or root e2e/)
scripts/             # start.sh, dev.sh
data/                # SQLite DB, videos, thumbnails (gitignored)
```

## Key Conventions
- TDD: tests written first, implementation follows
- API prefix: `/api/*` for all endpoints
- Vite dev server proxies `/api` to FastAPI on :8000
- Video files stored in `data/videos/{category}/{uuid}.mp4`
- Thumbnails in `data/thumbnails/{uuid}.jpg`
- AI settings in `data/config.json`
- Non-MP4 videos auto-transcoded to H.264+AAC
- yt-dlp prefers H.264+AAC format to minimize transcoding
- All API responses use JSON
- Frontend uses Tailwind CSS utility classes

## Environment Variables
- `DATA_DIR`: Data storage directory (default: `./data`)
- `PORT`: Server port (default: `8000`)
- `HOST`: Server host (default: `0.0.0.0`)
