#!/bin/bash

# script configures basic libraries and settings necessary for stratux-radar
# script to be run as root
# called via configure_radar as sudo
# usage /bin/bash mk_configure_radar.sh <branch>
# <branch> is the github branch to clone, this is optional and set to "main" if not provided

# remove unnecessary software from the recommended version, unfortunately the lite version does not handel uart correctly
# remove all x11 stuff
apt remove libice6 x11-common firefox "cpp*" gdb busybox "gstreamer*" "gnupg*" "gnome*" "lx*" piwiz \
   groff-base "samba*" "xdg*" galculator geany xcompmgr gcr "chromium-browser*" "liblouis*" "desktop-*" \
   adwaita-icon-theme --purge -y
apt autoremove --purge -y

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
# modify /boot/firmware/config.text for groundsensor
{
  echo "# modification for ultrasonic ground sensor"
  echo "enable_uart=1"
  echo "dtoverlay=miniuart-bt"
} | tee -a /boot/firmware/config.txt

# sound and espeak
apt install libasound2-dev libasound2-doc python3-alsaaudio espeak-ng espeak-ng-data -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled -y
pip3 install py-espeak-ng ADS1x15-ADC --break-system-packages

# bluetooth
apt install bluetooth pulseaudio pulseaudio-module-bluetooth -y

# bluetooth configuration
# Enable a system wide pulseaudio server, otherwise audio in non-login sessions is not working
# configs in /etc/pulse/system.pa
{
  echo "### modification for radar bluetooth interface"
  echo ".ifexists module-bluetooth-discover.so"
  echo "load-module module-bluetooth-discover"
  echo ".endif"
  echo ".ifexists module-bluetooth-policy.so"
  echo "load-module module-bluetooth-policy"
  echo ".endif"
  echo "load-module module-switch-on-connect"
} | tee -a /etc/pulse/system.pa

# configs in /etc/pulse/client.conf to disable client spawns
# sed -i '$ a default-server = /var/run/pulse/native' /etc/pulse/client.conf
# sed -i '$ a autospawn = no' /etc/pulse/client.conf
# disable user oriented pulseaudio completely, is started as system daemon later to
# enable bluetooth without interactive session
# systemctl --user mask pulseaudio.service
# systemctl --user mask pulseaudio.socket

# allow user pulse bluetooth access
usermod -a -G bluetooth pulse
# addgroup pulse lp
usermod -a -G pulse-access pi

# start pulseaudio system wide
cp /home/pi/stratux-radar-display/image/pulseaudio.service /etc/systemd/system/
systemctl daemon-reload
systemctl --system enable pulseaudio.service
systemctl --system start pulseaudio.service


# include autostart into crontab of pi, so that radar starts on every boot
echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -u pi -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -

# copy simple checklist once, can be changed later
cp /home/pi/stratux-radar-display/config/checklist.example_small.xml /home/pi/stratux-radar-display/config/checklist.xml


echo "Radar configuration finished. Reboot to start"
