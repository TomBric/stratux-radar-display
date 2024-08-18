#!/bin/bash
# startup script for your radar
# This is called as pi user via autostart-radar.service or on stratux via crontab on every boot

# start configuration webserver
cd /home/pi/stratux-radar-display/main/radar-web && python3 radar-app.py -t 3 &

# start radar. This line will be configured via the configuration webserver
cd /home/pi/stratux-radar-display/main && python3 radar.py -r -d Epaper3in7 -c 192.168.10.1