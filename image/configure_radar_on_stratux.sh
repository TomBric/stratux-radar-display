#!/bin/bash

# script configures basic libraries necessary for stratux-radar
# script to be run as root on stratux (without a zero pi)

# set -x
apt install git python3-pip -y
# no sound or bluetooth on stratux
# apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth libttspico-utils
apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth python3-alsaaudio -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled python3-pip python3-numpy python3-pygame -y
su pi -c "pip3 install  ADS1x15-ADC --break-system-packages"

# check to get sound running on stratux
# this is the same effect as loginctl enable-linger pi
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
# ---------------

# copy simple checklist once, can be changed later
su pi -c "cp /home/pi/stratux-radar-display/config/checklist.example_small.xml /home/pi/stratux-radar-display/config/checklist.xml"

# disable bluetooth in any case, it is not working directly on Stratux
sed -i 's/-b/ /g' /home/pi/stratux-radar-display/image/stratux_radar.sh
# set IP to localhost in any case, if someone changes stratux ip
sed -i 's/192.168.10.1/127.0.0.1/g' /home/pi/stratux-radar-display/image/stratux_radar.sh
# include autostart into crontab, so that radar starts on every boot
# echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -u pi -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -

# enable spi
raspi-config nonint do_spi 0