#!/bin/bash
# script to flash T-Beam with firmware
# firmware including esptool etc. has to be in directory paramter one
# example usage:  /bin/bash flash-t-beam-once.sh /home/pi/stratux-radar-display/Gx811

cd "$1" || exit 1
FLAG_FILE="t-beam-flashed.flag"
LOGFILE="t-beam-flash.log"
EXEC_COMMAND="/bin/bash install-GxAirCom-Stratux-firmware.sh"
if [ -f "$FLAG_FILE" ]; then
    echo "T-Beam was already flashed. Exiting."
    exit 0
fi
echo "Flashing GxAirCom to T-Beam"
$EXEC_COMMAND > >(tee -a "$LOGFILE") 2>&1
touch "$FLAG_FILE"
