#!/bin/bash

# script configures basic libraries necessary for stratux-radar
# script to be run as pi on stratux (without a zero pi)

# luma files and more
sudo apt-get update -y
sudo apt install python3-pip python3-pil -y
sudo apt-get install libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff5 -y
sudo pip3 install luma.oled

#websockets for radar
sudo pip3 install websockets

# espeak-ng for sound output
# sudo apt-get update
sudo apt-get install espeak-ng espeak-ng-data libespeak-ng-dev -y
sudo pip3 install py-espeak-ng

# bluetooth configs
sudo apt-get install libbluetooth-dev -y
sudo pip3 install pybluez
sudo pip3 install pydbus
sudo pip3 install --upgrade PILLOW

sudo apt install python3-numpy -y

# get files from repo
# cd /home/pi && git clone https://github.com/TomBric/stratux-radar-display.git

# include autostart into crontab, so that radar starts on every boot
echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -

# enable spi
sudo raspi-config nonint do_spi 0