#!/bin/bash

# script optimizes boot time for a stratux-display image, so that radar.py is started as early as possible
# usage sudo /bin/bash optimize_boot_time.sh


# set -x
set -Eeuo pipefail
trap 'status=$?; echo "Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2; exit "$status"' ERR



# ---------------------------------------------------------------------------
# Boot time optimization: start radar.py as early as possible
# ---------------------------------------------------------------------------
echo "[INFO] Optimizing boot time..."

# Start radar as a system service directly after local filesystems and udev are up.
# It does not wait for network, user sessions or the NetworkManager AP, so radar.py starts
# much earlier than via the user service (autostart-radar.service).
cat > /etc/systemd/system/autostart-radar-early.service <<EOF
[Unit]
Description=Autostart Stratux-Radar (early)
DefaultDependencies=no
After=systemd-remount-fs.service systemd-udevd.service
Before=shutdown.target
Conflicts=shutdown.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/stratux-radar-display/image
ExecStart=/bin/bash /home/pi/stratux-radar-display/image/stratux_radar.sh
Restart=no
Nice=-5
CPUWeight=1000

[Install]
WantedBy=sysinit.target
EOF
systemctl daemon-reload
systemctl enable autostart-radar-early.service

# remove the late-starting user service, otherwise radar would be started twice
rm -f /home/pi/.config/systemd/user/default.target.wants/autostart-radar.service

# no user session needed any more: linger would create run-user-1000.mount and user@1000.service at boot
rm -f /var/lib/systemd/linger/pi

# swap/zram delays swap.target, which local-fs.target (and everything behind it) waited for
systemctl mask systemd-zram-setup@zram0.service dev-zram0.swap >/dev/null 2>&1 || true
systemctl disable rpi-zram-writeback.timer rpi-resize-swap-file.service >/dev/null 2>&1 || true
if [ -f /etc/rpi/swap.conf ]; then
  mkdir -p /etc/rpi/swap.conf.d
  printf '[Main]\nMechanism=none\n' > /etc/rpi/swap.conf.d/10-noswap.conf
fi

# Services not needed on a standalone display, they only delay boot
for svc in NetworkManager-wait-online.service systemd-networkd-wait-online.service \
    apt-daily.timer apt-daily-upgrade.timer man-db.timer e2scrub_all.timer fstrim.timer \
    ModemManager.service triggerhappy.service keyboard-setup.service console-setup.service \
    rpi-eeprom-update.service userconfig.service; do
  if systemctl list-unit-files "$svc" 2>/dev/null | grep -q "^$svc"; then
    systemctl disable "$svc" >/dev/null 2>&1 || true
    case "$svc" in
      *wait-online.service) systemctl mask "$svc" >/dev/null 2>&1 || true ;;
    esac
  fi
done

# cloud-init is not needed after first boot and costs several seconds on every boot
if dpkg -s cloud-init >/dev/null 2>&1; then
  echo "[INFO] Purging cloud-init..."
  touch /etc/cloud/cloud-init.disabled
  DEBIAN_FRONTEND=noninteractive apt-get purge -y cloud-init
  apt-get autoremove -y --purge
  rm -rf /etc/cloud /var/lib/cloud
  echo "[OK] cloud-init purged."
fi

# Boot config: no splash, no boot delay, quiet console (console output slows down boot)
if [ -f /boot/firmware/config.txt ]; then BOOT_CONFIG=/boot/firmware/config.txt; else BOOT_CONFIG=/boot/config.txt; fi
if [ -f /boot/firmware/cmdline.txt ]; then BOOT_CMDLINE=/boot/firmware/cmdline.txt; else BOOT_CMDLINE=/boot/cmdline.txt; fi
for line in 'disable_splash=1' 'boot_delay=0' 'camera_auto_detect=0'; do
  grep -Fxq "$line" "$BOOT_CONFIG" || printf '%s\n' "$line" >> "$BOOT_CONFIG"
done
grep -qw quiet "$BOOT_CMDLINE" || sed -i '1 s/$/ quiet loglevel=3/' "$BOOT_CMDLINE"
sed -i '1 s/ splash//; 1 s/ plymouth.ignore-serial-consoles//' "$BOOT_CMDLINE"
echo "[OK] Boot optimized. Radar is started by autostart-radar-early.service. Reboot to apply."
