#!/bin/bash

# startup script for your radar
# This is called via crontab as pi user on every boot
# Configure your destination IP at the end, if you are not using standard
python3 /home/pi/stratux-radar-display/main/radar.py -s -D Oled_1in5 -c 192.168.10.1 &
# python3 /home/pi/stratux-radar-display/main/radar.py -s -D Epaper_3in7 -c 192.168.10.1 &
