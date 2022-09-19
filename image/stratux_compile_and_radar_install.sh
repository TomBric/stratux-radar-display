#!/bin/bash

# script compiles stratux and installs stratux-radar on stratux
# make sure that "persistent logging" is switched on on stratux before and rebooted
# connect stratux via "AP+client" mode to internet before as well

# script to be run as pi on stratux 
# usage /bin/bash stratux_compile_and_radar_install <branch>
# <branch> is the github branch from stratux-radar display o clone, this is optional and set to "main" if not provided
# example:  /bin/bash stratux_compile_and_radar_install
# for main branch
# example:  /bin/bash stratux_compile_and_radar_install dev
# for dev branch


if [ "$#" -lt 1 ]; then
    branch="main"
else
    branch=$1
fi
sudo systemctl start systemd-timesyncd
sleep 2
sudo systemctl stop systemd-timesyncd

sudo -i PWD=/root git clone --recursive https://github.com/b3nn0/stratux.git
sudo apt install build-essential
sudo -i PWD=/root wget https://golang.org/dl/go1.17.1.linux-arm64.tar.gz
sudo -i PWD=/root tar xzf go1.17.1.linux-arm64.tar.gz
sudo -i PWD=/root rm go1.17.1.linux-arm64.tar.gz

sudo make -C /root/stratux
sudo make -C /root/stratux install

# installing radar-display
cd /home/pi && git clone -b "$branch" https://github.com/TomBric/stratux-radar-display.git
/bin/bash /home/pi/stratux-radar-display/image/configure_radar_on_stratux
