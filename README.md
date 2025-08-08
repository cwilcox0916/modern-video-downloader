# Modern Video Downloader (Local-Only)

A local-only video downloader you can run on Unraid. Backend uses FastAPI + yt-dlp (Python API). Frontend is a Vite + React + Tailwind single-page app with a dark, glossy UI.

- Local-only. No analytics, no trackers.
- Uses yt-dlp Python API directly (no shelling out).
- Downloads saved to a fixed path defined by `DEFAULT_DOWNLOAD_DIR`, mounted into the API container at `/downloads`.

## Features

- **URL input and controls**: Thumbnail, Preview, Download, Cancel
- **Thumbnail preview**: Shows the best available thumbnail
- **Video preview**: Plays direct stream URL with CORS proxy
- **Download queue**: Paste multiple URLs, one per line
- **Real-time progress tracking**: Live progress bars with speed, ETA, and file size
- **Stop downloads**: Cancel running or queued downloads with comprehensive cleanup
- **File management**: Browser download or Save As dialog with File System Access API
- **Local-only**: Your links never leave your machine
- **Sequential processing**: In-memory FIFO queue with progress monitoring

## Backend (FastAPI + yt-dlp)

Endpoints:

- `POST /api/thumbnail {url}` → `{thumbnail}` - Get best thumbnail URL
- `POST /api/preview {url}` → `{stream_url}` - Get direct video stream URL  
- `POST /api/download {url}` → `{queued, job_ids}` - Enqueue single download
- `POST /api/queue/add {urls: string[]}` → `{queued, job_ids}` - Enqueue multiple downloads
- `GET /api/queue` → `{queue: [...]}` - Get queue status with progress
- `DELETE /api/jobs/{job_id}` → `{success, message}` - Cancel download job
- `GET /api/jobs/{job_id}/file` → File download - Serve completed downloads
- `GET /api/proxy?url=<encoded_url>` → Proxied content - CORS bypass for previews

Queue is in-memory and sequential using `asyncio.create_task`. Downloads use yt-dlp’s Python API with `merge_output_format: "mp4"`, `restrictfilenames: true`, quiet logging, and a stable `outtmpl`.

## Frontend (Vite + React + Tailwind)

- Dark, glossy, gradient accents
- Keyboard-friendly (Enter in URL triggers Preview)
- Uses `VITE_API_URL` for API base (defaults to `/` if unset)

## Docker

Each side has its own Dockerfile and `docker-compose.yml` runs both. The API mounts your local download folder to `/downloads`.

## Unraid 7.1.2 Installation

This section provides complete instructions for installing Modern Video Downloader on Unraid 7.1.2 with auto-update capabilities.

### Prerequisites

1. **Unraid 7.1.2** or newer
2. **Docker enabled** in Unraid settings (Settings → Docker → Enable Docker: Yes)
3. **Git plugin** - Install from Community Applications if not already installed
4. **User Scripts plugin** (optional, for auto-updates) - Install from Community Applications

### Method 1: Manual Docker Compose (Recommended)

#### Step 1: Clone Repository

SSH into your Unraid server or use the terminal in the Unraid UI:

```bash
# Navigate to your appdata directory
cd /mnt/user/appdata

# Clone the repository
git clone https://github.com/cwilcox0916/modern-video-downloader.git

# Navigate to the project directory
cd modern-video-downloader
```

#### Step 2: Create Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit the configuration
nano .env
```

Configure your `.env` file for Unraid:

```ini
# Downloads will be saved to this location on your Unraid server
DEFAULT_DOWNLOAD_DIR=/mnt/user/Media/Downloads

# API URL - use your Unraid server IP
VITE_API_URL=http://<YOUR-UNRAID-IP>:8000/
```

Replace `<YOUR-UNRAID-IP>` with your actual Unraid server IP address.

#### Step 3: Create Download Directory

```bash
# Ensure the download directory exists
mkdir -p /mnt/user/Media/Downloads
chmod 755 /mnt/user/Media/Downloads
```

#### Step 4: Build and Start

```bash
# Build the Docker images
docker compose build

# Start the services
docker compose up -d

# Verify the containers are running
docker compose ps
```

#### Step 5: Access the Application

- **Web UI**: `http://<YOUR-UNRAID-IP>:5173`
- **API Documentation**: `http://<YOUR-UNRAID-IP>:8000/docs`

### Method 2: Using Docker Templates (Alternative)

If you prefer using Unraid's Docker tab instead of Docker Compose:

#### Container 1: Modern Video Downloader API

1. Go to **Docker** tab in Unraid UI
2. Click **Add Container**
3. Fill in the template:

```yaml
Repository: modern-video-downloader-api:latest
Name: mvd-api
Network Type: Bridge
Port Mappings:
  - Container Port: 8000, Host Port: 8000, Protocol: TCP
Path Mappings:
  - Container Path: /downloads, Host Path: /mnt/user/Media/Downloads, Access Mode: Read/Write
Environment Variables:
  - Variable: DEFAULT_DOWNLOAD_DIR, Value: /downloads
```

#### Container 2: Modern Video Downloader Web

1. Click **Add Container** again
2. Fill in the template:

```yaml
Repository: modern-video-downloader-web:latest  
Name: mvd-web
Network Type: Bridge
Port Mappings:
  - Container Port: 80, Host Port: 5173, Protocol: TCP
Environment Variables:
  - Variable: VITE_API_URL, Value: http://<YOUR-UNRAID-IP>:8000/
```

### Auto-Update Setup

To automatically update when the GitHub repository changes:

#### Option 1: User Scripts (Recommended)

1. Install **User Scripts** plugin from Community Applications
2. Go to **Settings** → **User Scripts**
3. Click **Add New Script** and name it `update-video-downloader`
4. Paste this script:

```bash
#!/bin/bash

# Modern Video Downloader Auto-Update Script
cd /mnt/user/appdata/modern-video-downloader

echo "Checking for updates..."

# Fetch latest changes
git fetch origin main

# Check if there are new commits
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Updates found! Updating..."
    
    # Stop services
    docker compose down
    
    # Pull latest changes
    git pull origin main
    
    # Rebuild and restart
    docker compose build --no-cache
    docker compose up -d
    
    echo "Update completed successfully!"
    
    # Send notification (optional)
    /usr/local/emhttp/webGui/scripts/notify -e "Modern Video Downloader" -s "Updated to latest version" -i "normal"
else
    echo "Already up to date"
fi
```

5. Set schedule: **Custom** → `0 2 * * *` (runs daily at 2 AM)
6. Click **Save Changes**

#### Option 2: Cron Job

```bash
# Edit crontab
crontab -e

# Add this line to check for updates daily at 2 AM
0 2 * * * /mnt/user/appdata/modern-video-downloader/update.sh
```

Create the update script:

```bash
# Create update script
cat > /mnt/user/appdata/modern-video-downloader/update.sh << 'EOF'
#!/bin/bash
cd /mnt/user/appdata/modern-video-downloader
git fetch origin main
if [ $(git rev-parse HEAD) != $(git rev-parse origin/main) ]; then
    docker compose down
    git pull origin main  
    docker compose build --no-cache
    docker compose up -d
    echo "$(date): Updated Modern Video Downloader" >> /var/log/video-downloader-updates.log
fi
EOF

# Make it executable
chmod +x /mnt/user/appdata/modern-video-downloader/update.sh
```

### Unraid-Specific Configuration

#### Recommended Share Settings

For optimal performance, configure your shares:

1. **Media Share Settings** (where downloads are saved):
   - **Use cache**: Yes
   - **Cache**: Prefer (if you have cache drives)

#### Network Configuration

- The application uses ports **5173** (Web UI) and **8000** (API)  
- Ensure these ports aren't used by other services
- Consider using a reverse proxy (like Nginx Proxy Manager) for cleaner URLs

#### Backup Considerations

Your download queue is stored in memory and will be lost on restart. Consider these backup strategies:

1. **Bookmark important URLs** before downloading
2. **Use persistent volume** for queue data (future enhancement)
3. **Regular backups** of your configuration:

```bash
# Backup script
tar -czf /mnt/user/Backups/video-downloader-$(date +%Y%m%d).tar.gz /mnt/user/appdata/modern-video-downloader
```

## Troubleshooting

### Common Issues on Unraid

#### Containers Won't Start
```bash
# Check container logs
docker compose logs api
docker compose logs web

# Check if ports are in use
netstat -tulpn | grep -E ":(5173|8000)"

# Restart Docker service
/etc/rc.d/rc.docker restart
```

#### Permission Issues
```bash
# Fix download directory permissions
chmod 755 /mnt/user/Media/Downloads
chown nobody:users /mnt/user/Media/Downloads
```

#### Network Issues
- Ensure Docker is enabled in Unraid settings
- Check if your firewall is blocking the ports
- Verify your Unraid server IP address in the `.env` file

#### Updates Not Working
```bash
# Manually update
cd /mnt/user/appdata/modern-video-downloader
git pull origin main
docker compose down
docker compose build --no-cache  
docker compose up -d
```

### Performance Tips

1. **Use SSD Cache**: Place downloads on cache drives for better performance
2. **Resource Allocation**: Consider Docker memory limits for heavy usage
3. **Network Speed**: Ensure good internet connection for large video downloads
4. **Cleanup**: Regularly clean old downloads to save disk space

### Getting Help

- **Check logs**: Use `docker compose logs` to debug issues
- **GitHub Issues**: Report bugs at https://github.com/cwilcox0916/modern-video-downloader/issues
- **Unraid Forums**: Ask questions in the Docker Engine forum

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
- Downloads are processed sequentially to avoid overwhelming your system.
- All cancelled downloads are cleaned up completely to prevent storage bloat.

### Planned Features

- **Quality selector** (1080p/720p/audio-only) via yt-dlp format syntax
- **Persistent queue** (SQLite/Redis) for queue survival across restarts  
- **Batch operations** (select multiple items for bulk cancel/retry)
- **Download scheduling** (queue items for specific times)
- **Multiple download directories** with category-based routing