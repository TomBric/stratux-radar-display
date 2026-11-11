#!/bin/bash

# script configures a stratux-radar-display image for standalone display usage
# that means it can be used on a pi with a display and without stratux
# useful e.g. if only groundsensor is used
# script to be run as root on a already existing stratux-display image
# usage sudo /bin/bash configure_standalone_display.sh


# set -x
set -Eeuo pipefail
trap 'status=$?; echo "Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2; exit "$status"' ERR





# Set these build-time values before creating the standalone image.
STANDALONE_AP_SSID="Radar-Display"
AP_CONNECTION_NAME="radar-display"
STANDALONE_AP_IP="192.168.8.1/24"

if [ "$STANDALONE_AP_SSID" = "" ] || [ "${#STANDALONE_AP_SSID}" -gt 32 ]; then
  echo "[ERROR] Set STANDALONE_AP_SSID to a name of 1-32 characters." >&2
  exit 1
fi
command -v nmcli >/dev/null 2>&1 || {
  echo "[ERROR] nmcli is required to configure the standalone access point." >&2
  exit 1
}

# Disable saved Wi-Fi networks so NetworkManager only connects to this AP.
echo "[INFO] Looking for a Wi-Fi device..."
WIFI_DEVICE=$(nmcli -t -f DEVICE,TYPE device status |
  awk -F: '$2 == "wifi" { print $1; exit }')
if [ -z "$WIFI_DEVICE" ]; then
  echo "[ERROR] No Wi-Fi device found by NetworkManager." >&2
  exit 1
fi
echo "[OK] Using Wi-Fi device $WIFI_DEVICE."

echo "[INFO] Disabling saved Wi-Fi connections..."
echo "[INFO] I will come back with SSID $STANDALONE_AP_SSID and IP $STANDALONE_AP_IP"
while IFS=: read -r uuid type; do
  if [ "$type" = "802-11-wireless" ]; then
    nmcli connection modify uuid "$uuid" connection.autoconnect no
    if nmcli -g UUID connection show --active | grep -Fx "$uuid" >/dev/null; then
      nmcli connection down uuid "$uuid"
    fi
  fi
done < <(nmcli -t -f UUID,TYPE connection show)
echo "[OK] Saved Wi-Fi connections will not autoconnect."

# Re-create our profile to make rerunning this script safe and repeatable.
echo "[INFO] Preparing access point profile '$AP_CONNECTION_NAME'..."
EXISTING_AP_UUID=$(nmcli -t -f NAME,UUID connection show |
  awk -F: -v name="$AP_CONNECTION_NAME" '$1 == name { print $2; exit }')
if [ -n "$EXISTING_AP_UUID" ]; then
  nmcli connection delete uuid "$EXISTING_AP_UUID"
  echo "[OK] Removed the previous access point profile."
fi

nmcli radio wifi on
echo "[INFO] Creating open access point '$STANDALONE_AP_SSID'..."
nmcli connection add type wifi ifname "$WIFI_DEVICE" \
  con-name "$AP_CONNECTION_NAME" ssid "$STANDALONE_AP_SSID" \
  connection.autoconnect yes connection.autoconnect-priority 100 \
  802-11-wireless.mode ap 802-11-wireless.band bg \
  ipv4.method shared ipv4.addresses "$STANDALONE_AP_IP" \
  ipv6.method disabled
echo "[OK] Access point profile created."

echo "[INFO] Activating access point..."
nmcli connection up "$AP_CONNECTION_NAME"
if ! nmcli -g NAME connection show --active | grep -Fx "$AP_CONNECTION_NAME" >/dev/null; then
  echo "[ERROR] Access point '$AP_CONNECTION_NAME' is not active." >&2
  exit 1
fi

echo "[OK] Access point is active."
echo "Connect to the open Wi-Fi network '$STANDALONE_AP_SSID' (no password required)."
echo "Access the display at http://192.168.8.1"
