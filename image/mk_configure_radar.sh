#!/bin/bash

# script configures basic libraries and settings necessary for stratux-radar
# script to be run as root
# called via configure_radar as sudo
# usage /bin/bash mk_configure_radar.sh
# use option -i pico2tts to install pico2tts from debian source (necessary for armhf 32 bit version)
# exmple: /bin/bash mk_configure_radar.sh -i pico2tts

DEBIAN=false

while getopts ":i" opt; do
  case $opt in
    i)
      if [ "$OPTARG" = "pico2tts" ]; then
        DEBIAN=true
      fi
      ;;
    \?)
      echo "Invalid option: -$OPTARG"
      exit 1
      ;;
    :)
      echo "option -$OPTARG requires a value."
      exit 1
      ;;
  esac
done


# set -x

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
systemctl mask serial-getty@ttyAMA0.service

# modify /boot/firmware/config.text for groundsensor
{
  echo "# modification for ultrasonic ground sensor"
  echo "enable_uart=1"
  echo "dtoverlay=miniuart-bt"
} | tee -a /boot/firmware/config.txt


if [ "$DEBIAN" = false ]; then
  apt install libttspico-utils -y
else
  # pico2wave is not installable in bookworm armhf (why so ever), so include debian source to install
  {
    echo "deb [arch=armhf, trusted=yes] http://deb.debian.org/debian bookworm main contrib non-free"
  } | tee -a /etc/apt/sources.list
  apt update
  apt install libttspico-utils -y
  # remove the last line in sources.list now again
  sudo sed -i /etc/apt/sources.list -e '$d'
fi

# bookworm lite:
apt install git python3-pip -y
apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth python3-alsaaudio -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled python3-pip python3-numpy python3-pygame -y
su pi -c "pip3 install  ADS1x15-ADC --break-system-packages"

#  enable headless connect:
#  in  /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua       ["with-logind"] = true,  auf false setzen
sed -i 's/\["with-logind"\] = true/\["with-logind"\] = false/' /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua
# configuration changes for bluetooth
# change autoconnect feature and limit headset roles
sed -i 's/\["bluez5.auto-connect"\]  = "\[ hfp_hf hsp_hs a2dp_sink \]",/\["bluez5.auto-connect"\]  = "\[ hfp_hf a2dp_sink \]",/' /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua
sed -i 's/--\["bluez5.headset-roles"\] = "\[ hsp_hs hsp_ag hfp_hf hfp_ag \]",/\["bluez5.headset-roles"\] = "\[ hfp_hf hfp_ag \]",/' /usr/share/wireplumber/bluetooth.lua.d/50-bluez-config.lua
# tweaks for bluetooth on zero 2 w
# /lib/firmware/brcm/brcmfmac43436s-sdio.raspberrypi,model-zero-2-w.txt
# btc_mode=1
# btc_params8=0x4e20
# btc_params1=0x7530

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

# copy simple checklist once, can be changed later
su pi -c "cp /home/pi/stratux-radar-display/config/checklist.example_small.xml /home/pi/stratux-radar-display/config/checklist.xml"

echo "Radar configuration finished. Reboot to start"
