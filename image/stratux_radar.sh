#!/bin/bash

# startup script for your radar
# This is called via crontab as pi user on every boot
# Configure your destination IP at the end, if you are not using standard
cd /home/pi/stratux-radar-display/main && python3 radar.py -b -r -d Oled_1in5 -c 192.168.10.1
# cd /home/pi/stratux-radar-display/main && python3 radar.py -b -r -d Epaper_3in7 -c 192.168.10.1
# cd /home/pi/stratux-radar-display/main && python3 radar.py -b -d Epaper_1in54 -c 192.168.10.1
