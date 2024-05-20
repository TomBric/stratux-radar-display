#!/bin/bash

# script configures basic libraries and settings necessary for stratux-radar
# script to be run as root
# called via configure_radar as sudo
# usage /bin/bash mk_configure_radar.sh

# set -x

# apt update
# apt upgrade -y

# enable ssh
raspi-config nonint do_ssh 0
# enable spi and i2c (for cowarner)
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0

# for groundsensor, disable ssh over serial cause it is needed for the sensor
# disable ssh over serial otherwise
sed -i /boot/firmware/cmdline.txt -e "s/console=ttyAMA0,[0-9]\+ //"
sed -i /boot/firmware/cmdline.txt -e "s/console=serial0,[0-9]\+ //"
sed -i /boot/firmware/cmdline.txt -e "s/console=tty[0-9]\+ //"
# for bookworm disable serial-getty, it is whatsoever started by bookworm even if cmdline is changed
systemctl mask serial-getty@ttyAMA0.service

# modify /boot/firmware/config.text for groundsensor
{
  echo "# modification for ultrasonic ground sensor"
  echo "enable_uart=1"
  echo "dtoverlay=miniuart-bt"
} | tee -a /boot/firmware/config.txt


# bookworm lite:
apt install git python3-pip -y
apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth libttspico-utils python3-alsaaudio -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled python3-pip python3-numpy python3-pygame -y
su pi -c "pip3 install  ADS1x15-ADC --break-system-packages"

#  enable headless connect:
#  in  /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua       ["with-logind"] = true,  auf false setzen
sed -i 's/\["with-logind"\] = true/\["with-logind"\] = false/' /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua

# this is the same effect as loginctl enable-linger piA
mkdir -p /var/lib/systemd/linger
touch /var/lib/systemd/linger/pi

# install and start service to start radar
su pi -c "mkdir -p /home/pi/.config/systemd/user/"
su pi -c "cp /home/pi/stratux-radar-display/image/systemctl-autostart-radar.service /home/pi/.config/systemd/user/autostart-radar.service"
# create a symlink, do do the same as: systemctl --user -M pi@ enable autostart-radar
su pi -c "mkdir /home/pi/.config/systemd/user/default.target.wants"
su pi -c "ln -s /home/pi/.config/systemd/user/autostart-radar.service /home/pi/.config/systemd/user/default.target.wants/autostart-radar.service"

# change log level of rtkit, otherwise this fills journal with tons of useless info
sed -i '/\[Service\]/a LogLevelMax=notice' /usr/lib/systemd/system/rtkit-daemon.service

# copy simple checklist once, can be changed later
su pi -c "cp /home/pi/stratux-radar-display/config/checklist.example_small.xml /home/pi/stratux-radar-display/config/checklist.xml"

echo "Radar configuration finished. Reboot to start"
