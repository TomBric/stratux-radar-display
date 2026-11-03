#!/bin/bash

set -Eeuo pipefail

die() {
    echo "$1" >&2
    exit 1
}

trap 'status=$?; echo "Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2; exit "$status"' ERR

echo "mk_configure_radar.sh called with arguments: $0 $*"

# script configures basic libraries and settings necessary for stratux-radar
# script to be run as root
# called via configure_radar as sudo
# usage /bin/bash mk_configure_radar.sh


SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

if [ "$(id -u)" -ne 0 ]; then
    die "This script must be run as root"
fi

echo "Checking pi user configuration..."
PI_PASSWD_ENTRY=$(getent passwd pi) || die "pi user is missing"
PI_HOME=$(echo "$PI_PASSWD_ENTRY" | cut -d: -f6)
PI_SHELL=$(echo "$PI_PASSWD_ENTRY" | cut -d: -f7)

[ -n "$PI_HOME" ] || die "pi home directory is not configured"
[ -d "$PI_HOME" ] || die "pi home directory '$PI_HOME' is missing"
[ -x /bin/bash ] || die "Missing /bin/bash"
[ "$PI_SHELL" = "/bin/bash" ] || die "pi login shell is '$PI_SHELL', expected /bin/bash"

echo "pi user ok: shell=$PI_SHELL, home=$PI_HOME"


apt update
# do an upgrade, otherwise bluez is not working properly in version 2024-07-04
# apt upgrade -y
# apt -y autoremove

# enable ssh
raspi-config nonint do_ssh 0
# enable spi and i2c (for cowarner)
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0
# disable password request for sudo in Trixie
raspi-config nonint do_sudo_pass 1

# Disable swap, for Trixie modify /etc/rpi/swap.conf ...
if [ -f /etc/rpi/swap.conf ]; then
    if grep -q '^\[Main\]' /etc/rpi/swap.conf; then
        if ! grep -q '^Mechanism=' /etc/rpi/swap.conf; then
            sed -i '/^\[Main\]/a Mechanism=none  # modified by mk_configure_radar' /etc/rpi/swap.conf
        else
            sed -i 's/^Mechanism=.*/Mechanism=none  # modified by mk_configure_radar/' /etc/rpi/swap.conf
        fi
    else
        printf '\n[Main]\nMechanism=none  # modified by mk_configure_radar\n' >> /etc/rpi/swap.conf
    fi
fi
# Generate ssh key for all installs. Otherwise it would have to be done on each boot, which takes a couple of seconds
ssh-keygen -A -v
systemctl disable regenerate_ssh_host_keys


# for groundsensor, disable ssh over serial cause it is needed for the sensor
# disable ssh over serial otherwise
if [ -f /boot/firmware/cmdline.txt ]; then
    BOOT_CMDLINE=/boot/firmware/cmdline.txt
elif [ -f /boot/cmdline.txt ]; then
    BOOT_CMDLINE=/boot/cmdline.txt
else
    die "Could not find Raspberry Pi cmdline.txt under /boot or /boot/firmware"
fi
sed -i -e "s/console=ttyAMA0,[0-9]\+ //" "$BOOT_CMDLINE"
sed -i -e "s/console=serial0,[0-9]\+ //" "$BOOT_CMDLINE"
sed -i -e "s/console=tty[0-9]\+ //" "$BOOT_CMDLINE"
# for bookworm and trixie disable serial-getty, it is whatsoever started by bookworm even if cmdline is changed
systemctl mask serial-getty@ttyAMA0.service

# modify the boot config for the ultrasonic ground sensor
if [ -f /boot/firmware/config.txt ]; then
    BOOT_CONFIG=/boot/firmware/config.txt
elif [ -f /boot/config.txt ]; then
    BOOT_CONFIG=/boot/config.txt
else
    die "Could not find Raspberry Pi config.txt under /boot or /boot/firmware"
fi
grep -Fxq '# modification for ultrasonic ground sensor' "$BOOT_CONFIG" ||
    printf '%s\n' '# modification for ultrasonic ground sensor' >> "$BOOT_CONFIG"
grep -Fxq 'enable_uart=1' "$BOOT_CONFIG" ||
    printf '%s\n' 'enable_uart=1' >> "$BOOT_CONFIG"
grep -Fxq 'dtoverlay=miniuart-bt' "$BOOT_CONFIG" ||
    printf '%s\n' 'dtoverlay=miniuart-bt' >> "$BOOT_CONFIG"


apt install libttspico-utils -y
# trixie lite:
apt install git python3-pip -y

# bluetooth and sound installation
apt install pipewire libspa-0.2-bluetooth pulseaudio-module-bluetooth python3-alsaaudio -y
rfkill unblock bluetooth    # enable bluetooth which is otherwise disabled on lite image
mkdir -p /etc/wireplumber/wireplumber.conf.d
# rules for wireplumber to accept bluetooth sinks and headless connect
cp "$SCRIPT_DIR/wireplumber-bluetooth.conf" /etc/wireplumber/wireplumber.conf.d/bluetooth.conf     # rules for wireplumber to accept bluetooth sinks
# limit reconnect attempts after loss of Bluetooth connection, since this leads to network outages
sed -i 's/#ReconnectAttempts = 7/ReconnectAttempts = 3/' /etc/bluetooth/main.conf

# apt install pipewire pipewire-audio pipewire-alsa libspa-0.2-bluetooth python3-alsaaudio -y
apt install python3-websockets python3-xmltodict python3-pydbus python3-luma.oled python3-luma.lcd python3-numpy python3-scipy python3-pygame python3-gpiozero -y

su pi -c "pip3 install ADS1x15-ADC --break-system-packages"
su pi -c "pip3 install bayesian-filters --break-system-packages --root-user-action=ignore --no-warn-script-location"
su pi -c "pip3 install bleak --break-system-packages --root-user-action=ignore"
apt -y autoremove


# this is the same effect as loginctl enable-linger pi, starts radar without any login
mkdir -p /var/lib/systemd/linger
touch /var/lib/systemd/linger/pi


# install and start service to start radar
PI_USER_SERVICE_DIR="$PI_HOME/.config/systemd/user"
PI_USER_WANTS_DIR="$PI_USER_SERVICE_DIR/default.target.wants"
install -d -o pi -g pi "$PI_USER_WANTS_DIR"
cp "$SCRIPT_DIR/systemctl-autostart-radar.service" "$PI_USER_SERVICE_DIR/autostart-radar.service"
chown pi:pi "$PI_USER_SERVICE_DIR/autostart-radar.service"

# create a symlink, do do the same as: systemctl --user -M pi@ enable autostart-radar
ln -sfn "$PI_USER_SERVICE_DIR/autostart-radar.service" "$PI_USER_WANTS_DIR/autostart-radar.service"

# change log level of rtkit, otherwise this fills journal with tons of useless info
sed -i '/\[Service\]/a LogLevelMax=notice' /usr/lib/systemd/system/rtkit-daemon.service

# copy simple checklist once, can be changed later
cp "$SCRIPT_DIR/../config/checklist.example_small.xml" "$SCRIPT_DIR/../config/checklist.xml"
chown pi:pi "$SCRIPT_DIR/../config/checklist.xml"

echo "Radar configuration finished. Reboot to start"
