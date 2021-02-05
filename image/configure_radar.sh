#!/bin/bash

# script configures basic libraries necessary for stratux-radar
# script to be run as pi

#enable usermod
# sudo usermod -a -G spi,gpio,i2c pi

#luma files and more
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install python3-pip python3-pil -y
sudo apt-get install libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff5 -y
sudo pip3 install luma.oled
sudo apt-get install git -y


#websockets for radar
sudo pip3 install websockets

# espeak-ng for sound output
sudo apt-get update
sudo apt-get install espeak-ng espeak-ng-data libespeak-ng-dev -y
sudo pip3 install py-espeak-ng

# bluetooth configs
sudo apt-get install libbluetooth-dev -y
sudo pip3 install pybluez
sudo pip3 install pydbus
sudo apt purge piwiz -y
# necessary to disable bluetoothmessage "To turn on ..."

# get files from repo
cd /home/pi && git clone https://github.com/TomBric/stratux-radar-display.git

# include autostart into crontab, so that radar starts on every boot
echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -


# bluetooth configuration
# Enable a system wide pulseaudio server, otherwise audio in non-login sessions is not working
#
# configs in /etc/pulse/system.pa
sudo sed -i '$ a load-module module-bluetooth-discover' /etc/pulse/system.pa
sudo sed -i '$ a load-module module-bluetooth-policy' /etc/pulse/system.pa
# configs in /etc/pulse/client.conf to disable client spawns
sudo sed -i '$ a default-server = /var/run/pulse/native' /etc/pulse/client.conf
sudo sed -i '$ a autospawn = no' /etc/pulse/client.conf

# allow user pulse bluetooth access
sudo addgroup pulse bluetooth

# start pulseaudio system wide
sudo cp /home/pi/stratux-radar-display/image/pulseaudio.service /etc/systemd/system/
sudo systemctl --system enable pulseaudio.service
sudo systemctl --system start pulseaudio.service
