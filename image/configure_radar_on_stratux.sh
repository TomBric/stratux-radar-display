#!/bin/bash

# script configures basic libraries necessary for stratux-radar
# script to be run as root on stratux (without a zero pi)
# usage /bin/bash configure_radar_on_stratux.sh

#  use option -u to enable UART for GroundSensor (if hardware is connected)
#  example: /bin/bash configure_radar_on_stratux.sh -u

set -x
UART=false

# check parameters
while getopts ":u" opt; do
      case $opt in
        u) UART=true ;;
        \?) echo "Invalid option: -$OPTARG"; exit 1 ;;
        :) echo "Option -$OPTARG requires a value."; exit 1 ;;
      esac
    done

if [ "$UART" = true ]; then
  echo "Enabling UART Ground Sensor support"
fi


apt update
apt install git python3-pip -y
# no sound or bluetooth on stratux
# apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth libttspico-utils
apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth python3-alsaaudio -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled python3-pip python3-numpy python3-pygame -y
su pi -c "pip3 install  ADS1x15-ADC --break-system-packages"
/bin/bash "$(dirname "$0")"/mk_config_webapp.sh -s

# check to get sound running on stratux
# this is the same effect as loginctl enable-linger pi
mkdir -p /var/lib/systemd/linger
touch /var/lib/systemd/linger/pi

# install and start service to start radar
su pi -c "mkdir -p /home/pi/.config/systemd/user/"
cp "$(dirname "$0")"/systemctl-autostart-radar.service /home/pi/.config/systemd/user/autostart-radar.service
chown pi /home/pi/.config/systemd/user/autostart-radar.service ; chgrp pi /home/pi/.config/systemd/user/autostart-radar.service
# create a symlink, do do the same as: systemctl --user -M pi@ enable autostart-radar
su pi -c "mkdir -p /home/pi/.config/systemd/user/default.target.wants"
su pi -c "ln -f -s /home/pi/.config/systemd/user/autostart-radar.service /home/pi/.config/systemd/user/default.target.wants/autostart-radar.service"

if [ "$UART" = true ]; then
  # enable sensor UART output
  # for groundsensor, disable ssh over serial cause it is needed for the sensor
  # disable ssh over serial otherwise
  sed -i /boot/firmware/cmdline.txt -e "s/console=ttyAMA0,[0-9]\+ //"
  sed -i /boot/firmware/cmdline.txt -e "s/console=serial0,[0-9]\+ //"
  sed -i /boot/firmware/cmdline.txt -e "s/console=tty[0-9]\+ //"
  # for bookworm disable serial-getty, it is whatsoever started by bookworm even if cmdline is changed
  systemctl mask serial-getty@ttyAMA0.service
fi

# change log level of rtkit, otherwise this fills journal with tons of useless info
sed -i '/\[Service\]/a LogLevelMax=notice' /usr/lib/systemd/system/rtkit-daemon.service
# ---------------

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
cp "$(dirname "$0")"/../config/checklist.example_small.xml "$(dirname "$0")"/../config/checklist.xml
chown pi "$(dirname "$0")"/../config/checklist.xml ; chgrp pi "$(dirname "$0")"/../config/checklist.xml


# disable bluetooth in any case, it is not working directly on Stratux
sed -i 's/-b/ /g' "$(dirname "$0")"/stratux_radar.sh
# set IP to localhost in any case, if someone changes stratux ip
sed -i 's/192.168.10.1/127.0.0.1/g' "$(dirname "$0")"/stratux_radar.sh
# set stratux flag for web app to disable several options
sed -i 's/radarapp.py -t 10/radarapp.py --stratux -t 10/g' "$(dirname "$0")"/stratux_radar.sh


# enable spi
raspi-config nonint do_spi 0