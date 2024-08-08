#!/bin/bash

# script configures libraries and settings necessary for stratux-radar web configuration
# script to be run as root
# called via configure_radar as sudo with target image mounted
# usage /bin/bash mk_configure webapp.sh
# exmple: /bin/bash mk_config_webapp.sh


set -x
apt update
# apt upgrade -y
apt install nginx -y
pip3 install bootstrap-flask flask-wtf --break-system-packages
cp radar_reverse.conf /etc/nginx/conf.d/