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

# remove desktop packages
apt purge xserver* lightdm* vlc* lxde* chromium* desktop* gnome* gstreamer* gtk* hicolor-icon-theme* lx* mesa* \
python3-pygame pocketsphinx-en-us libllvm11 libgtk-3-common libflite1 libgtk2.0-common poppler-data \
libqt5gui5 qttranslations5-l10n libc6-dbg geany-common gdb libqt5core5a libstdc++-10-dev libgcc-10-dev python3-jedi \
libpython3.9-dev -y
apt-get remove realvnc-vnc-server -y
apt-get autoremove -y

# luma files and more
apt-get update -y
apt-get upgrade -y
apt-get install git python3-pip python3-pil -y libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff5 -y
pip3 install luma.oled


#websockets for radar and ADS1115 analog reader for co warner
pip3 install websockets ADS1x15-ADC

# espeak-ng for sound output and alsoaudio for external sound
apt-get install libasound2-dev libasound2-doc python3-alsaaudio espeak-ng espeak-ng-data libespeak-ng-dev -y
pip3 install py-espeak-ng pyalsaaudio

# bluetooth configs
apt-get install bluetooth libbluetooth-dev python3-dev -y
pip3 install pybluez pydbus
pip3 install pillow==8.4
apt purge piwiz -y
# necessary to disable bluetoothmessage "To turn on ..."

# get files from repo
cd /home/pi && sudo -u pi git clone -b "$branch" https://github.com/TomBric/stratux-radar-display.git

# include autostart into crontab of pi, so that radar starts on every boot
echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -u pi -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -


# bluetooth configuration
# Enable a system wide pulseaudio server, otherwise audio in non-login sessions is not working
#
# configs in /etc/pulse/system.pa
sed -i '$ a load-module module-bluetooth-discover' /etc/pulse/system.pa
sed -i '$ a load-module module-bluetooth-policy' /etc/pulse/system.pa
sed -i '$ a load-module module-switch-on-connect' /etc/pulse/system.pa

# configs in /etc/pulse/client.conf to disable client spawns
sed -i '$ a default-server = /var/run/pulse/native' /etc/pulse/client.conf
sed -i '$ a autospawn = no' /etc/pulse/client.conf

# allow user pulse bluetooth access
addgroup pulse bluetooth
addgroup pi pulse-access

# start pulseaudio system wide
cp /home/pi/stratux-radar-display/image/pulseaudio.service /etc/systemd/system/
systemctl --system enable pulseaudio.service
# systemctl --system start pulseaudio.service

# enable spi and i2c (for cowarner)
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0
echo "Radar configuration finished"

