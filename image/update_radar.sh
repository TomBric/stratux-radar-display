#!/bin/bash

# update file to update stratux_radar without internet connections
# connect via ssh to the destination and run this skript as pi
# usage: update_radar.sh
# to be used with windows batch-file remote_update.bat

HOME_DIR="/home/pi"
RADAR_DIR="$HOME_DIR/stratux-radar-display"
GITHUB_DIR="$HOME_DIR/stratux-radar-display-main"
CONFIGURATION="image/stratux_radar.sh"

die() {
    echo "$1"
    exit 1
}

cd $HOME_DIR || die "$HOME_DIR not found"
now=$(date +"%F_%H%M%S")
OLD_VERSION="$RADAR_DIR.$now"
mv "$RADAR_DIR" "$OLD_VERSION" || echo "Info: No valid old version found."
rm "$GITHUB_DIR/*.jpg"
mv "$GITHUB_DIR" "$RADAR_DIR"
cp "$OLD_VERSION/$CONFIGURATION" "$RADAR_DIR/$CONFIGURATION"  || echo "No old configuration found. Using default."

echo "Update successfully applied.  Please reboot and test"