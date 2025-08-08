# Modern Video Downloader (Local-Only)

A local-only video downloader you can run on Unraid. Backend uses FastAPI + yt-dlp (Python API). Frontend is a Vite + React + Tailwind single-page app with a dark, glossy UI.

- Local-only. No analytics, no trackers.
- Uses yt-dlp Python API directly (no shelling out).
- Downloads saved to a fixed path defined by `DEFAULT_DOWNLOAD_DIR`, mounted into the API container at `/downloads`.

## Features (v1)

- URL input and buttons: Thumbnail, Preview, Download, Cancel
- Thumbnail pane shows the best thumbnail
- Video Preview pane plays a direct stream URL
- Download Queue with multiline textarea:
  - Paste multiple URLs, one per line
  - Buttons: Add to Queue, Start Queue (same as Add in v1), Clear
- Footer note: “Local-only. Your links never leave your machine.”
- In-memory FIFO queue processed sequentially

## Backend (FastAPI + yt-dlp)

Endpoints:

- `POST /api/thumbnail {url}` → `{thumbnail}`
- `POST /api/preview {url}` → `{stream_url}`
- `POST /api/download {url}` → enqueue one job → `{queued, job_ids}`
- `POST /api/queue/add {urls: string[]}` → enqueue many → `{queued, job_ids}`
- `GET /api/queue` → statuses → `{queue: [...]}`

Queue is in-memory and sequential using `asyncio.create_task`. Downloads use yt-dlp’s Python API with `merge_output_format: "mp4"`, `restrictfilenames: true`, quiet logging, and a stable `outtmpl`.

## Frontend (Vite + React + Tailwind)

- Dark, glossy, gradient accents
- Keyboard-friendly (Enter in URL triggers Preview)
- Uses `VITE_API_URL` for API base (defaults to `/` if unset)

## Docker

Each side has its own Dockerfile and `docker-compose.yml` runs both. The API mounts your local download folder to `/downloads`.

### Unraid Quickstart

You can use the Docker Compose Manager plugin (e.g., Ibracorp) on Unraid to manage this stack.

1) Clone or copy this repo to your Unraid share.
2) Create your `.env`:

```bash
cp .env.example .env
# then edit paths and URLs in .env
```

3) Build images:

```bash
docker compose build
```

4) Start the stack:

```bash
docker compose up -d
```

- UI: `http://<unraid-ip>:5173`
- API: `http://<unraid-ip>:8000`

### Environment

`.env`:

```ini
DEFAULT_DOWNLOAD_DIR=/mnt/user/Media/Downloads
VITE_API_URL=http://mvd-api:8000/
```

- `DEFAULT_DOWNLOAD_DIR` is mounted into the API container at `/downloads`.
- `VITE_API_URL` is used by the frontend at build time to call the API. In `docker-compose.yml`, it is passed as a build arg and environment variable to the web service.

### Windows Quickstart

Test locally with Docker Desktop on Windows:

1) Create `.env` in the project root with your downloads folder and API base:

```ini
DEFAULT_DOWNLOAD_DIR=C:\\Users\\<you>\\Downloads
VITE_API_URL=http://localhost:8000/
```

2) Build and start:

```powershell
docker compose build
docker compose up -d
```

3) Open the app:

- UI: `http://localhost:5173`
- API: `http://localhost:8000`

Notes:
- The compose file mounts `${DEFAULT_DOWNLOAD_DIR}` into the API container at `/downloads`. Using a Windows path works; Docker Desktop translates it to a bind mount.
- If you see a warning that the `version` attribute is obsolete, it is safe to ignore; modern Compose no longer requires it.

## Development

- Backend (local):

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

- Frontend (local):

```bash
cd frontend
npm ci
npm run dev
```

Set `VITE_API_URL` to match your API origin (e.g., `http://localhost:8000/`).

## Notes and Next Steps

- This is a local-only tool. Only the media sites you request are contacted.
- Files are saved to your configured `DEFAULT_DOWNLOAD_DIR`.

TODOs (not implemented yet):
- Progress hooks + cancel endpoint (yt-dlp progress hooks)
- Quality selector (1080p/720p/audio)
- Persistent queue (SQLite/Redis)