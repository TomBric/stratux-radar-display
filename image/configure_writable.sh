#!/bin/bash

# Restore a writable Raspberry Pi OS Trixie system after configure_read_only.sh.
# Run as root, reboot if instructed, and run again to finish:
#   sudo /bin/bash configure_writable.sh

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

for command in raspi-config findmnt; do
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

ROOT_TYPE=$(findmnt -rn -o FSTYPE --mountpoint /)
OVERLAY_NOW=$(raspi-config nonint get_overlay_now)
if [ "$ROOT_TYPE" = "overlay" ] && [ "$OVERLAY_NOW" != "0" ]; then
  echo "[ERROR] An unsupported root overlay is active; refusing to change its configuration." >&2
  exit 1
fi

echo "[INFO] Disabling the Trixie RAM overlay..."
raspi-config nonint do_overlayfs 1
if [ "$(raspi-config nonint get_overlay_conf)" != "1" ]; then
  echo "[ERROR] The root overlay is still enabled in the boot command line." >&2
  exit 1
fi

if [ "$ROOT_TYPE" = "overlay" ] || [ "$OVERLAY_NOW" = "0" ]; then
  echo "[INFO] Reboot, then run this script again to make the boot partition writable."
  echo "[WARN] Root changes made before the reboot will be discarded."
  exit 0
fi

BOOT_OPTIONS=$(findmnt -rn --fstab -o OPTIONS --mountpoint "$BOOT_MOUNT")
case ",$BOOT_OPTIONS," in
  *,ro,*)
    echo "[ERROR] $BOOT_MOUNT is still configured read-only in /etc/fstab." >&2
    exit 1
    ;;
esac
ROOT_OPTIONS=$(findmnt -rn -o OPTIONS --mountpoint /)
case ",$ROOT_OPTIONS," in
  *,rw,*) ;;
  *)
    echo "[ERROR] The root filesystem is not mounted writable." >&2
    exit 1
    ;;
esac

mount -o remount,rw "$BOOT_MOUNT"
BOOT_OPTIONS=$(findmnt -rn -o OPTIONS --mountpoint "$BOOT_MOUNT")
case ",$BOOT_OPTIONS," in
  *,rw,*) ;;
  *)
    echo "[ERROR] $BOOT_MOUNT is not mounted writable." >&2
    exit 1
    ;;
esac

echo "[OK] Root and boot are writable; subsequent changes will persist."
