#!/bin/bash

# Configure Raspberry Pi OS Trixie with a RAM-backed root overlay.
# Run on the Pi after completing image configuration:
#   sudo /bin/bash configure_read_only.sh
#
# To make persistent changes later, run configure_writable.sh and follow its
# reboot instructions. Re-run this script after making changes.

# set -x
set -Eeuo pipefail
trap 'status=$?; echo "[ERROR] Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2; exit "$status"' ERR

if [ "$#" -ne 0 ]; then
  echo "Usage: sudo /bin/bash $0" >&2
  exit 2
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "[ERROR] Run this script as root." >&2
  exit 1
fi

if [ ! -r /etc/os-release ]; then
  echo "[ERROR] Cannot determine the operating system version." >&2
  exit 1
fi
# shellcheck source=/dev/null
. /etc/os-release
if [ "${VERSION_CODENAME:-}" != "trixie" ]; then
  echo "[ERROR] This script requires Raspberry Pi OS Trixie." >&2
  exit 1
fi

for command in raspi-config findmnt dpkg-query; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "[ERROR] Required command not found: $command" >&2
    exit 1
  fi
done

if [ -f /boot/firmware/config.txt ]; then
  BOOT_MOUNT=/boot/firmware
elif [ -f /boot/config.txt ]; then
  BOOT_MOUNT=/boot
else
  echo "[ERROR] Cannot find the Raspberry Pi boot configuration." >&2
  exit 1
fi

if ! findmnt -rn --mountpoint "$BOOT_MOUNT" >/dev/null; then
  echo "[ERROR] $BOOT_MOUNT is not mounted as a separate boot filesystem." >&2
  exit 1
fi
if [ "$(findmnt -rn -o FSTYPE --mountpoint /)" = "overlay" ]; then
  echo "[ERROR] The root overlay is already active. Disable it and reboot before changing its configuration." >&2
  exit 1
fi

echo "[INFO] Enabling the Trixie RAM overlay for root and boot partition write protection..."
raspi-config nonint do_overlayfs 0
echo "[DONE] The root overlay for root as well as boot protection have been enabled."

# raspi-config can report success even when enabling an overlay or boot protection fails.
if [ "$(dpkg-query -W -f='${db:Status-Status}' overlayroot 2>/dev/null)" != "installed" ]; then
  echo "[ERROR] overlayroot is not installed; the root overlay cannot start." >&2
  exit 1
fi
if [ "$(raspi-config nonint get_overlay_conf)" != "0" ]; then
  echo "[ERROR] The root overlay was not enabled in the boot command line." >&2
  exit 1
fi
BOOT_OPTIONS=$(findmnt -rn --fstab -o OPTIONS --mountpoint "$BOOT_MOUNT")
case ",$BOOT_OPTIONS," in
  *,ro,*) ;;
  *)
    echo "[ERROR] $BOOT_MOUNT is not configured read-only in /etc/fstab." >&2
    exit 1
    ;;
esac

echo "[OK] Read-only root and boot are configured. Reboot to activate them."
echo "[WARN] Root writes use RAM and are discarded on reboot, including settings and flight records."
echo "[WARN] The RAM overlay can fill up during prolonged use."
echo "[WARN] Other separately mounted filesystems and swap are not protected by this script."
echo "[INFO] See the script header for instructions to disable the overlay for persistent changes."
