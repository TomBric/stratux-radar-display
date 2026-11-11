#!/bin/bash

set -Eeuo pipefail
trap 'status=$?; echo "Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2; exit "$status"' ERR

# script configures libraries and settings necessary for stratux-radar web configuration
# script to be run as root
# called via configure_radar as sudo with target image mounted
# run with option -s to configure webapp on stratux (uses port 81 instead of 80)
# example: /bin/bash mk_config_webapp.sh
#          /bin/bash mk_config_webapp.sh -s

# set -x

ON_STRATUX=false
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

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
shift $((OPTIND - 1))
[ "$#" -eq 0 ] || { echo "Unexpected argument: $1" >&2; exit 1; }


apt update
# apt upgrade -y
apt install nginx -y
apt install python3-psutil -y
apt install bootstrap-flask python3-flaskext.wtf werkzeug -y
pip cache purge
# necessary to match new hashes
# uninstall types-flask-migrate if present, because it is not needed
if pip3 show types-flask-migrate >/dev/null 2>&1; then
  pip3 uninstall types-flask-migrate --break-system-packages --root-user-action=ignore -y
fi
# generate reverse proxy config
rm -f /etc/nginx/sites-enabled/default
cp "$SCRIPT_DIR/radar_reverse.conf" /etc/nginx/sites-available/radar_reverse.conf
if [ "$ON_STRATUX" = true ]; then
  # change port 80 to 81 for nginx, since stratux already offers web on 80
  sed -i 's/listen 80/listen 81/g' /etc/nginx/sites-available/radar_reverse.conf
fi
ln -f /etc/nginx/sites-available/radar_reverse.conf /etc/nginx/sites-enabled/
# validate configuration before restarting
nginx -t
# systemd is not running when called in a chroot (image build), nginx is started on first boot then
if [ -d /run/systemd/system ]; then
  systemctl restart nginx
else
  echo "systemd not running (chroot?), skipping nginx restart"
fi
