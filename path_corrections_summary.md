# Path Corrections Summary: pi-player → connect

## Files Updated ✅

### 1. **config.py**
- `BASE_DIR: Path = Path("/home/pi/pi-player")` → `Path("/home/pi/connect")`
- Dev mode path: `current_dir / "pi-player"` → `current_dir / "connect"`

### 2. **install.sh**
- `INSTALL_DIR="${PI_HOME}/pi-player"` → `"${PI_HOME}/connect"`
- Status script log paths: `/home/pi/pi-player/logs/` → `/home/pi/connect/logs/`
- Update script path: `cd /home/pi/pi-player` → `cd /home/pi/connect`

### 3. **services/pi-player.service**
- `WorkingDirectory=/home/pi/pi-player` → `/home/pi/connect`
- `PYTHONPATH=/home/pi/pi-player` → `/home/pi/connect`
- `ExecStart=...pi-player/venv/bin/python...pi-player/pi_server.py` → `connect` paths
- `ReadWritePaths=/home/pi/pi-player` → `/home/pi/connect`

### 4. **services/media-player.service**
- `WorkingDirectory=/home/pi/pi-player` → `/home/pi/connect`
- `PYTHONPATH=/home/pi/pi-player` → `/home/pi/connect`
- `ExecStart=...pi-player/venv/bin/python...pi-player/media_player.py` → `connect` paths
- `ReadWritePaths=/home/pi/pi-player` → `/home/pi/connect`

### 5. **services/pi-player-startup.service**
- `WorkingDirectory=/home/pi/pi-player` → `/home/pi/connect`
- `PYTHONPATH=/home/pi/pi-player` → `/home/pi/connect`
- `ExecStart=/home/pi/pi-player/run.sh` → `/home/pi/connect/run.sh`

### 6. **setup_boot.sh**
- `INSTALL_DIR="/home/${PI_USER}/pi-player"` → `"/home/${PI_USER}/connect"`
- Cron grep: `grep -q "pi-player/run.sh"` → `"connect/run.sh"`
- rc.local grep: `grep -q "pi-player/run.sh"` → `"connect/run.sh"`
- Sudoers file: `/etc/sudoers.d/pi-player` → `/etc/sudoers.d/pi-connect`
- Test script path: `/home/pi/pi-player/run.sh` → `/home/pi/connect/run.sh`

### 7. **run.sh**
- `INSTALL_DIR="/home/${PI_USER}/pi-player"` → `"/home/${PI_USER}/connect"`

### 8. **deploy_to_connect.sh** ✨
- **NEW**: Complete deployment script that handles all file copying and service setup
- Copies all Python files to `/home/pi/connect`
- Installs corrected systemd services
- Creates utility scripts with correct paths
- Sets proper permissions for pi user

## Directory Structure After Deployment

```
/home/pi/connect/
├── *.py                          # All Python application files
├── *.sh                          # Shell scripts (run.sh, setup_boot.sh, etc.)
├── services/                     # systemd service files
│   ├── pi-player.service
│   ├── media-player.service
│   └── pi-player-startup.service
├── media_cache/                  # Downloaded media files
├── logs/                         # Application logs
├── current_playlist.json         # Active playlist (with Cloudinary URLs)
├── status.sh                     # System status check
├── restart.sh                    # Restart services
└── create_test_playlist.py       # Test playlist creation
```

## Services with Corrected Paths

All systemd services now use `/home/pi/connect` paths:

- **pi-player.service**: API server (port 8000)
- **media-player.service**: Media playback daemon  
- **pi-player-startup.service**: Boot startup orchestrator

## Deployment Command

```bash
# On your Raspberry Pi:
./deploy_to_connect.sh
```

This will:
1. Copy all files to `/home/pi/connect`
2. Install systemd services with correct paths
3. Set proper permissions
4. Start services
5. Create default Cloudinary playlist
6. Test the installation

## Verification Commands

```bash
# Check services
systemctl status pi-player.service
systemctl status media-player.service

# Check API
curl http://localhost:8000/health
curl http://localhost:8000/playlist

# Check logs
tail -f /home/pi/connect/logs/pi_server.log
tail -f /home/pi/connect/logs/media_player.log

# Run status check
/home/pi/connect/status.sh
```

## Result

✅ **All path references updated from `pi-player` to `connect`**  
✅ **Complete deployment solution provided**  
✅ **Cloudinary collection URLs integrated as default fallback**  
✅ **Services ready for Raspberry Pi with `/home/pi/connect` structure**

Your Pi Player will now work correctly with the "connect" folder name on your Raspberry Pi!