#!/bin/bash

# script configures a stratux-radar-display image for standalone display usage
# that means it can be used on a pi with a display and without stratux
# useful e.g. if only groundsensor is used
# script to be run as root on a stratux-display image
# usage /bin/bash configure_standalone_display.sh


# set -x
set -Eeuo pipefail
trap 'status=$?; echo "Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2; exit "$status"' ERR

# Set these build-time values before creating the standalone image.
STANDALONE_AP_SSID="Radar-Display"
STANDALONE_AP_PASSWORD="12345678"
AP_CONNECTION_NAME="radar-display"

if [ "$STANDALONE_AP_SSID" = "" ] || [ "${#STANDALONE_AP_SSID}" -gt 32 ]; then
  echo "Set STANDALONE_AP_SSID to a name of 1-32 characters." >&2
  exit 1
fi
if [ "$STANDALONE_AP_PASSWORD" = "SET-A-UNIQUE-WPA2-PASSWORD" ] ||
   [ "${#STANDALONE_AP_PASSWORD}" -lt 8 ] ||
   [ "${#STANDALONE_AP_PASSWORD}" -gt 63 ]; then
  echo "Set STANDALONE_AP_PASSWORD to a unique WPA2 password of 8-63 characters." >&2
  exit 1
fi

command -v nmcli >/dev/null 2>&1 || {
  echo "nmcli is required to configure the standalone access point." >&2
  exit 1
}

# Disable saved Wi-Fi networks so NetworkManager only connects to this AP.
WIFI_DEVICE=$(nmcli -t -f DEVICE,TYPE device status |
  awk -F: '$2 == "wifi" { print $1; exit }')
if [ -z "$WIFI_DEVICE" ]; then
  echo "No Wi-Fi device found by NetworkManager." >&2
  exit 1
fi

while IFS=: read -r uuid type; do
  if [ "$type" = "802-11-wireless" ]; then
    nmcli connection modify uuid "$uuid" connection.autoconnect no
    if nmcli -g UUID connection show --active | grep -Fx "$uuid" >/dev/null; then
      nmcli connection down uuid "$uuid"
    fi
  fi
done < <(nmcli -t -f UUID,TYPE connection show)

# Re-create our profile to make rerunning this script safe and repeatable.
EXISTING_AP_UUID=$(nmcli -t -f NAME,UUID connection show |
  awk -F: -v name="$AP_CONNECTION_NAME" '$1 == name { print $2; exit }')
if [ -n "$EXISTING_AP_UUID" ]; then
  nmcli connection delete uuid "$EXISTING_AP_UUID"
fi

nmcli radio wifi on
nmcli connection add type wifi ifname "$WIFI_DEVICE" \
  con-name "$AP_CONNECTION_NAME" ssid "$STANDALONE_AP_SSID" \
  connection.autoconnect yes connection.autoconnect-priority 100 \
  802-11-wireless.mode ap 802-11-wireless.band bg \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.proto rsn \
  802-11-wireless-security.pairwise ccmp \
  802-11-wireless-security.group ccmp \
  802-11-wireless-security.psk "$STANDALONE_AP_PASSWORD" \
  ipv4.method shared ipv6.method disabled
nmcli connection up "$AP_CONNECTION_NAME"
