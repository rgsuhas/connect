# Pi Player Systemd Service Configuration

This document describes how to configure the pi-player digital signage system as a systemd service for automatic startup and management.

## Service Overview

The pi-player service (`pi-player-kiosk.service`) is designed to:

- Start automatically after the graphical environment is available
- Run as the `pi` user with access to display and audio hardware
- Fetch the latest playlist before starting the player
- Restart automatically on failure
- Start background downloads after the player begins

## Service File Location

The service file is installed at:
```
/etc/systemd/system/pi-player-kiosk.service
```

## Service Configuration Template

```ini
[Unit]
Description=Pi Player Fullscreen Kiosk
Documentation=https://github.com/rgsuhas/pi-player
After=graphical.target
Wants=graphical.target
StartLimitBurst=3
StartLimitIntervalSec=300

[Service]
Type=simple
User=pi
Group=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
Environment=HOME=/home/pi
WorkingDirectory=/home/pi
ExecStartPre=/usr/bin/env bash -lc 'cd /home/pi/connect && python3 -c "from fetch_backend_playlist import fetch_and_save_backend_playlist_with_cleanup; fetch_and_save_backend_playlist_with_cleanup()" 2>&1'
ExecStart=/home/pi/connect/bin/start-player.sh
ExecStartPost=/home/pi/connect/bin/start-downloads.sh
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-player-kiosk

# Allow access to display and audio devices
SupplementaryGroups=audio video render

# Security settings - less restrictive for GUI apps
NoNewPrivileges=false
ProtectSystem=false
ProtectHome=false

[Install]
WantedBy=graphical.target
```

## Configuration Options

### Unit Section

| Option | Value | Description |
|--------|-------|-------------|
| `Description` | Pi Player Fullscreen Kiosk | Human-readable service description |
| `Documentation` | https://github.com/rgsuhas/pi-player | Link to project documentation |
| `After` | graphical.target | Wait for graphical environment to be ready |
| `Wants` | graphical.target | Prefer to start with graphical environment |
| `StartLimitBurst` | 3 | Maximum restart attempts in interval |
| `StartLimitIntervalSec` | 300 | Reset restart counter every 5 minutes |

### Service Section

| Option | Value | Description |
|--------|-------|-------------|
| `Type` | simple | Service doesn't fork background processes |
| `User` | pi | Run as pi user (required for X11 access) |
| `Group` | pi | Run as pi group |
| `Environment` | DISPLAY=:0 | Set X11 display for GUI applications |
| `Environment` | XAUTHORITY=/home/pi/.Xauthority | X11 authentication file |
| `Environment` | HOME=/home/pi | Set home directory |
| `WorkingDirectory` | /home/pi | Set working directory |
| `ExecStartPre` | fetch_backend_playlist... | Update playlist before starting |
| `ExecStart` | start-player.sh | Main startup script |
| `ExecStartPost` | start-downloads.sh | Background download script |
| `Restart` | on-failure | Restart if service fails |
| `RestartSec` | 5 | Wait 5 seconds before restart |
| `StandardOutput` | journal | Send stdout to systemd journal |
| `StandardError` | journal | Send stderr to systemd journal |
| `SyslogIdentifier` | pi-player-kiosk | Log identifier in journal |
| `SupplementaryGroups` | audio video render | Access to hardware devices |

### Security Settings

| Option | Value | Description |
|--------|-------|-------------|
| `NoNewPrivileges` | false | Allow privilege escalation (needed for X11) |
| `ProtectSystem` | false | Don't restrict system file access |
| `ProtectHome` | false | Don't restrict home directory access |

**Note:** Security settings are relaxed because GUI applications need broad system access.

### Install Section

| Option | Value | Description |
|--------|-------|-------------|
| `WantedBy` | graphical.target | Enable service when graphical environment starts |

## Service Management Commands

### Basic Operations

```bash
# Start the service
sudo systemctl start pi-player-kiosk.service

# Stop the service
sudo systemctl stop pi-player-kiosk.service

# Restart the service
sudo systemctl restart pi-player-kiosk.service

# Check service status
sudo systemctl status pi-player-kiosk.service

# Enable auto-start on boot
sudo systemctl enable pi-player-kiosk.service

# Disable auto-start on boot
sudo systemctl disable pi-player-kiosk.service
```

### Advanced Management

```bash
# Reload systemd configuration after changes
sudo systemctl daemon-reload

# View service logs in real-time
journalctl -u pi-player-kiosk.service -f

# View recent service logs
journalctl -u pi-player-kiosk.service -n 50

# View service logs from today
journalctl -u pi-player-kiosk.service --since today

# Check if service is enabled
systemctl is-enabled pi-player-kiosk.service

# Check if service is active
systemctl is-active pi-player-kiosk.service
```

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check detailed status
sudo systemctl status pi-player-kiosk.service -l

# Check journal for errors
journalctl -u pi-player-kiosk.service --since "1 hour ago"

# Verify X11 is running
echo $DISPLAY
xset q
```

#### Display Issues
```bash
# Check if pi user can access X11
sudo -u pi DISPLAY=:0 xset q

# Verify XAUTHORITY file exists
ls -la /home/pi/.Xauthority

# Check X11 permissions
xhost +local:pi
```

#### Permission Issues
```bash
# Check file permissions
ls -la /home/pi/connect/bin/start-player.sh
ls -la /home/pi/connect/

# Fix ownership if needed
sudo chown -R pi:pi /home/pi/connect/
```

### Restart Behavior

The service is configured to:
- Restart automatically on failure
- Try up to 3 restarts within 5 minutes
- Wait 5 seconds between restart attempts
- Reset restart counter after 5 minutes

### Log Analysis

View service logs with context:
```bash
# Show logs with timestamps
journalctl -u pi-player-kiosk.service -o short-iso

# Show logs from last boot
journalctl -u pi-player-kiosk.service -b

# Show only errors
journalctl -u pi-player-kiosk.service -p err

# Follow logs and filter for specific terms
journalctl -u pi-player-kiosk.service -f | grep -i error
```

## Customization

### Environment Variables

Add additional environment variables in the `[Service]` section:
```ini
Environment=BACKEND_URL=https://your-api.example.com
Environment=DEBUG=1
Environment=LOG_LEVEL=DEBUG
```

### Custom Working Directory

Change the installation path by modifying:
```ini
WorkingDirectory=/your/custom/path
ExecStartPre=/usr/bin/env bash -lc 'cd /your/custom/path && ...'
ExecStart=/your/custom/path/bin/start-player.sh
ExecStartPost=/your/custom/path/bin/start-downloads.sh
```

### Different User

To run as a different user:
```ini
User=your-user
Group=your-group
Environment=XAUTHORITY=/home/your-user/.Xauthority
Environment=HOME=/home/your-user
WorkingDirectory=/home/your-user
```

**Important:** The user must have access to X11 and be in the `audio`, `video`, and `render` groups.

## Integration with Boot Process

The service is designed to start with the graphical environment:

1. System boots
2. Basic system services start
3. Graphical environment initializes (`graphical.target`)
4. Pi Player service starts automatically
5. Service fetches latest playlist
6. Player launches in fullscreen
7. Background downloads begin

This ensures the display is ready and the system is fully initialized before the player starts.
