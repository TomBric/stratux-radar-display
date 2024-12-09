#!/bin/bash

# script configures libraries and settings necessary for stratux-radar web configuration
# script to be run as root
# called via configure_radar as sudo with target image mounted
# run with option -s to configure webapp on stratux (uses port 81 instead of 80)
# example: /bin/bash mk_config_webapp.sh
#          /bin/bash mk_config_webapp.sh -s

# set -x

ON_STRATUX=false

while getopts ":s" opt; do
  case $opt in
    s)
      ON_STRATUX=true
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


apt update
# apt upgrade -y
apt install nginx -y
apt install python3-psutil
pip3 install bootstrap-flask flask-wtf werkzeug --break-system-packages
# generate reverse proxy config
unlink /etc/nginx/sites-enabled/default || true
cp radar_reverse.conf /etc/nginx/sites-available/
if [ "$ON_STRATUX" = true ]; then
  # change port 80 to 81 for nginx, since stratux already offers web on 80
  sed -i 's/listen 80/listen 81/g' /etc/nginx/sites-available/radar_reverse.conf
fi
ln -f /etc/nginx/sites-available/radar_reverse.conf /etc/nginx/sites-enabled/
# restart to read new configuration
systemctl restart nginx

