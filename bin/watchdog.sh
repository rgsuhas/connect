#!/usr/bin/env bash
set -euo pipefail
LOG_DIR="/home/pi/connect/logs"
LOG_FILE="$LOG_DIR/watchdog.log"
TS() { date '+%Y-%m-%d %H:%M:%S'; }

# Ensure log dir exists
mkdir -p "$LOG_DIR"

log() { echo "[$(TS)] $*" >> "$LOG_FILE"; }

SERVICES=(
  pi-player-kiosk.service
  pi-player.service
  pi-player-startup.service
)

restart_needed=0

for svc in "${SERVICES[@]}"; do
  if systemctl list-unit-files --type=service --no-legend | awk '{print $1}' | grep -qx "$svc"; then
    state=$(systemctl is-active "$svc" || true)
    enabled=$(systemctl is-enabled "$svc" || true)
    if [[ "$enabled" == "enabled" ]] && [[ "$state" != "active" ]]; then
      log "Service $svc is $state (enabled=$enabled) — restarting"
      if systemctl restart "$svc"; then
        log "Service $svc restarted"
        restart_needed=1
      else
        log "ERROR: Failed to restart $svc"
      fi
    fi
  fi
done

# Optional: journal hint
if [[ $restart_needed -eq 1 ]]; then
  log "One or more services were restarted by watchdog"
else
  log "All monitored services are healthy"
fi
