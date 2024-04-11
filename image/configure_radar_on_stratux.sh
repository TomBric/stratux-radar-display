#!/bin/bash

# script configures basic libraries necessary for stratux-radar
# script to be run as root on stratux (without a zero pi)

set -x
# luma files, pip3 and more
apt-get update -y
apt install libasound2-dev libasound2-doc python3-alsaaudio espeak-ng espeak-ng-data -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled python3-numpy python3-pip -y
pip3 install pybluez py-espeak-ng ADS1x15-ADC --break-system-packages

# copy simple checklist once, can be changed later
cp /home/pi/stratux-radar-display/config/checklist.example_small.xml /home/pi/stratux-radar-display/config/checklist.xml

# disable bluetooth in any case, it is not working directly on Stratux
sed -i 's/-b/ /g' /home/pi/stratux-radar-display/image/stratux_radar.sh
# include autostart into crontab, so that radar starts on every boot
echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -u pi -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -

# enable spi
raspi-config nonint do_spi 0