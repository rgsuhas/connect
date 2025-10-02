#!/bin/bash
cd /home/pi/connect
python3 -c "from download_manager import load_and_download_playlist; print('Starting downloads...'); res=load_and_download_playlist(); print('Downloads complete:', res)" > /home/pi/connect/logs/boot_download.log 2>&1 &
