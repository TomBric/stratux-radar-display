#!/bin/bash

set -Eeuo pipefail

# script configures basic libraries necessary for stratux-radar
# script to be run as pi (but now calls mk_configure_radar.sh as root)

if [ "$#" -ne 0 ]; then
  echo "Usage: $0" >&2
  exit 2
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

sudo /bin/bash "$SCRIPT_DIR/mk_configure_radar.sh"
sudo /bin/bash "$SCRIPT_DIR/mk_config_webapp.sh"