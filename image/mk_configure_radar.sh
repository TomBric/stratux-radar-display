#!/bin/bash

# script configures basic libraries and settings necessary for stratux-radar
# script to be run as root
# called via configure_radar as sudo via qemu
# usage /bin/bash mk_configure_radar.sh <branch>
# <branch> is the github branch to clone, this is optional and set to "main" if not provided

if [ "$#" -lt 1 ]; then
    branch="main"
else
    branch=$1
fi


# try to reduce writing to SD card as much as possible, so they don't get bricked when yanking the power cable
# Disable swap...
systemctl disable dphys-swapfile
apt purge -y dphys-swapfile
apt autoremove -y
apt clean

# enable ssh
raspi-config nonint do_ssh 0
# create user pi and "raspberry"
# useradd -m pi
# chpasswd pi:raspberry
# usermod -aG sudo pi
# set wifi with raspi-config
raspi-config nonint do_wifi_ssid_passphrase stratux

# enable spi and i2c (for cowarner)
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0

# for groundsensor, disable ssh over serial cause it is needed for the sensor
# disable ssh over serial otherwise
sed -i /boot/cmdline.txt -e "s/console=ttyAMA0,[0-9]\+ //"
sed -i /boot/cmdline.txt -e "s/console=serial0,[0-9]\+ //"
sed -i /boot/cmdline.txt -e "s/console=tty[0-9]\+ //"
# modify /boot/config.text for groundsensor
{
  echo "# modification for ultrasonic ground sensor"
  echo "enable_uart=1"
  echo "dtoverlay=miniuart-bt"
} | tee -a /boot/config.txt


apt install python3-pip python3-numpy python3-websockets python3-serial python3-luma.oled python3-xmltodict python3-pydbus -y
# sound and espeak
apt install libasound2-dev libasound2-doc python3-alsaaudio espeak-ng espeak-ng-data -y

# break system packages is needed here to install without a virtual environment
pip3 install py-espeak-ng ADS1x15-ADC --break-system-packages


# bluetooth configuration
# Enable a system wide pulseaudio server, otherwise audio in non-login sessions is not working
# configs in /etc/pulse/system.pa
# sed -i '$ a load-module module-bluetooth-discover' /etc/pulse/system.pa
# sed -i '$ a load-module module-bluetooth-policy' /etc/pulse/system.pa
# sed -i '$ a load-module module-switch-on-connect' /etc/pulse/system.pa

# configs in /etc/pulse/client.conf to disable client spawns
# sed -i '$ a default-server = /var/run/pulse/native' /etc/pulse/client.conf
# sed -i '$ a autospawn = no' /etc/pulse/client.conf

# allow user pulse bluetooth access
addgroup pulse bluetooth
addgroup pi pulse-access

# start pulseaudio system wide
# cp /home/pi/stratux-radar-display/image/pulseaudio.service /etc/systemd/system/
# systemctl --system enable pulseaudio.service
# systemctl --system start pulseaudio.service


# include autostart into crontab of pi, so that radar starts on every boot
echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -u pi -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -


echo "Radar configuration finished. Reboot to start"
