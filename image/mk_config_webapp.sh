#!/bin/bash

# script configures libraries and settings necessary for stratux-radar web configuration
# script to be run as root
# called via configure_radar as sudo with target image mounted
# example: /bin/bash mk_config_webapp.sh

set -x
apt update
# apt upgrade -y
apt install nginx -y
apt install python3-psutil
pip3 install bootstrap-flask flask-wtf werkzeug --break-system-packages
# generate reverse proxy config
unlink /etc/nginx/sites-enabled/default
cp radar_reverse.conf /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/radar_reverse.conf /etc/nginx/sites-enabled/
# restart to read new configuration
systemctl restart nginx

