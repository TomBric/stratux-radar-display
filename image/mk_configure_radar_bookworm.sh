#!/bin/bash

# script configures basic libraries and settings necessary for stratux-radar
# script to be run as root
# called via configure_radar as sudo
# usage /bin/bash mk_configure_radar.sh <branch>
# <branch> is the github branch to clone, this is optional and set to "main" if not provided


apt update
apt upgrade -y

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
sudo systemctl mask serial-getty@ttyAMA0.service

# modify /boot/firmware/config.text for groundsensor
{
  echo "# modification for ultrasonic ground sensor"
  echo "enable_uart=1"
  echo "dtoverlay=miniuart-bt"
} | tee -a /boot/firmware/config.txt


# bookworm lite:
apt install git python3-pip -y
apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth libttspico-utils python3-alsaaudio -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled python3-pip python3-numpy -y
# create symbolic link to /dev/stdout for pico2wave and stdout
sudo apt-get install libttspico-utils
pip3 install  ADS1x15-ADC --break-system-packages

#  enable headless connect:
#  in  /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua       ["with-logind"] = true,  auf false setzen
sed -i 's/\["with-logind"\] = true/\["with-logind"\] = false/' /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua
mkdir -p /home/pi/.config/systemd/user/
cp systemctl-autostart-radar.service /home/pi/.config/systemd/user/autostart-radar.service
sudo -l -u pi systemctl --user enable autostart-radar.service
loginctl enable-linger pi

# include autostart into crontab of pi, so that radar starts on every boot
echo "@reboot /bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh" | crontab -u pi -
# only works if crontab is empty, otherwise use
# crontab -l | sed "\$a@reboot /bin/bash /home/pi/stratux-radar-display/image/start_radar" | crontab -



# copy simple checklist once, can be changed later
cp /home/pi/stratux-radar-display/config/checklist.example_small.xml /home/pi/stratux-radar-display/config/checklist.xml


echo "Radar configuration finished. Reboot to start"