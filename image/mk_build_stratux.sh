#!/bin/bash

# Thomas Breitbach 2021 for stratux-radar-display, modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:
# sudo apt install --yes parted zip unzip zerofree
# If you want to build on x86 with aarch64 emulation, additionally install qemu-user-static qemu-system-arm
# Run this script as root.
#  sudo /bin/bash mk_stratux_display.sh [-b <branch>] [-k v32] [-u <USB-stick-name>]
# Run with argument "-b dev" to get the dev branch from github, otherwise with main
# Run with optional argument "-k v32" to create 32 bit based images for zero 1
# Run with optional argument "-u <USB-stick-name>" to move created images on the usb stick and then umount this
# call examples:
#   sudo /bin/bash mk_stratux_display.sh
#   sudo /bin/bash mk_stratux_display.sh -b dev
#   sudo /bin/bash mk_stratux_display.sh -b dev -k v32

set -x

RASPIOS_VERSION="2026-06-19"
RASPIOS_DOWNLOAD_URL="https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_armhf-${RASPIOS_VERSION}/2026-06-18-raspios-trixie-arm64-lite.img.xz"
TMPDIR="/home/pi/image-tmp"
DISPLAY_SRC="home/pi"

die() {
    echo "$1"
    exit 1
}

# set defaults
BRANCH=main
V32=false
USB_NAME=""


RASPIOS_VERSION="2026-06-19"
RASPIOS_DOWNLOAD_URL="https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-${RASPIOS_VERSION}/2026-06-18-raspios-trixie-arm64-lite.img.xz"

echo "Building stratux image based on Raspios Trixie Lite ARM64 version ${RASPIOS_VERSION}"

ZIPNAME="${RASPIOS_VERSION}-raspios-trixie-arm64-lite.img.xz"
IMGNAME="${ZIPNAME%.*}"

# cd to script directory
cd "$(dirname "$0")" || die "cd failed"
SRCDIR="$(realpath "$(pwd)"/..)"
mkdir -p $TMPDIR
cd $TMPDIR || die "cd failed"
mkdir -p $TMPDIR/out

# Download/extract image
wget -c $RASPIOS_DOWNLOAD_URL || die "Download failed"
unxz -k $ZIPNAME || die "Extracting base Trixie image failed"

echo "Trixie arm64 lite image downloaded and extracted to $IMGNAME"
# Check where in the image the root partition begins:
bootoffset=$(parted $IMGNAME unit B p | grep fat32 | awk -F ' ' '{print $2}')
bootoffset=${bootoffset::-1}
partoffset=$(parted $IMGNAME unit B p | grep ext4 | awk -F ' ' '{print $2}')
partoffset=${partoffset::-1}

echo "Boot partition starts at $bootoffset bytes, root partition starts at $partoffset bytes"

# Original image partition is too small to hold our stuff.. resize it to 5gb
truncate -s 5120M $IMGNAME || die "Image resize failed"
lo=$(losetup -f)
losetup $lo $IMGNAME
partprobe $lo
e2fsck -y -f ${lo}p2
parted --script ${lo} resizepart 2 100%
partprobe $lo || die "Partprobe failed failed"
resize2fs -p ${lo}p2 || die "FS resize failed"

echo "Image resized to 5GB, root partition resized to maximum size"


# Mount image locally, clone our repo, install packages..
mkdir -p mnt
mount -t ext4 "${lo}"p2 mnt/ || die "root-mount failed"
mount -t vfat "${lo}"p1 mnt/boot || die "boot-mount failed"

# install git for cloning repo (if not already installed) and pip
echo "Updating and full upgrade for image"
chroot mnt apt install git -y
chroot mnt apt update
chroot mnt apt full-upgrade -y

# download and use Virus Pilot build script
chroot mnt bash -c "$(wget -nv -O - https://raw.githubusercontent.com/VirusPilot/stratux-pi4/master/setup-pi4-latest.sh)""