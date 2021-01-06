#!/bin/bash

# script configures basic libraries necessary for stratux-radar
# script must be run as root

#enable usermod
# sudo usermod -a -G spi,gpio,i2c pi


#luma files and more
apt update && apt full-upgrade -y
apt-get install python3-pip python3-pil -y
apt-get install libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff5 -y
pip3 install luma.oled
apt-get install git -y


#websockets for radar
pip3 install websockets

# espeak-ng for sound output
apt install espeak-ng espeak-ng-data libespeak-ng-dev -y
pip3 install py-espeak-ng

# get files from repo
cd /root && git clone https://github.com/TomBric/stratux-radar-display.git
# cp /root/stratux-radar-display/image/rc.local.Oled_1in5 /etc/rc.local
# cp /root/stratux-radar-display/image/rc.local.Epaper_3in7 /etc/rc.local
#reboot
