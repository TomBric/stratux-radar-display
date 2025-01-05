#!/bin/bash

# script configures basic libraries necessary for stratux-radar
# script to be run as pi (but now calls mk_configure_radar.sh as root)
sudo /bin/bash "$(dirname "$0")"/mk_configure_radar.sh "$@"
sudo /bin/bash "$(dirname "$0")"/mk_config_webapp.sh "$@"