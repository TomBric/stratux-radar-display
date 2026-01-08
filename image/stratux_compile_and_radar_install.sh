#!/bin/bash

# script compiles stratux and installs stratux-radar on stratux
# make sure that "persistent logging" is switched on on stratux before and rebooted
# connect stratux via "AP+client" mode to internet before as well

# script to be run as pi on stratux 
# usage /bin/bash stratux_compile_and_radar_install <branch>
# <branch> is the github branch from stratux-radar display o clone, this is optional and set to "main" if not provided
# example:  /bin/bash stratux_compile_and_radar_install
# for main branch
# example:  /bin/bash stratux_compile_and_radar_install.sh dev
# for dev branch


if [ "$#" -lt 1 ]; then
    branch="main"
else
    branch=$1
fi
sudo systemctl start systemd-timesyncd
sleep 2
sudo systemctl stop systemd-timesyncd

# sudo apt update
# sudo apt upgrade -y

sudo -i PWD=/root git clone --branch v1.6r1-eu032 --recursive https://github.com/stratux/stratux.git || sudo -i PWD=/root git -C /
root/stratux pull
sudo apt install build-essential -y
sudo apt install libncurses-dev -y
sudo apt install golang -y
sudo apt install librtlsdr-dev -y

sudo -i PWD=/root make -C /root/stratux
sudo -i PWD=/root make -C /root/stratux install

# installing radar-display
cd /home/pi && git clone -b "$branch" https://github.com/TomBric/stratux-radar-display.git || git pull
/bin/bash /home/pi/stratux-radar-display/image/configure_radar_on_stratux.sh
