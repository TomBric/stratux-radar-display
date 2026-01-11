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

# cd .
set -x

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

# check parameters
while getopts ":b:k:u" opt; do
  case $opt in
    b)
      BRANCH="$OPTARG"
      ;;
    k)
      if [ "$OPTARG" = "v32" ]; then
        V32=true
      fi
      ;;
    u)
      USB_NAME=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG"
      exit 1
      ;;
    :)
      echo "option -$OPTARG requires a value."
      exit 1
      ;;
  esac
done

echo "Building images for branch '$BRANCH' V32=$V32 based on Trixie"

if [ "$V32" = true ]; then
  IMAGE_VERSION="armhf"
  outprefix="v32-stratux-display"
else
  IMAGE_VERSION="arm64"
  outprefix="stratux-display"
fi

ZIPNAME="2025-12-04-raspios-trixie-${IMAGE_VERSION}-lite.img.xz"
BASE_IMAGE_URL="https://downloads.raspberrypi.org/raspios_lite_${IMAGE_VERSION}/images/raspios_lite_${IMAGE_VERSION}-2025-12-04/${ZIPNAME}"

IMGNAME="${ZIPNAME%.*}"

# variables for pi imager repo.json
GITHUB_BASE_URL="https://github.com/TomBric/stratux-radar-display"
REPONAME="Stratux Radar Display"
V32_REPONAME="V32 Stratux Radar Display"
ICON_URL_BLACK="$GITHUB_BASE_URL/raw/main/pi-imager/stratux-logo-black192x192.png"
ICON_URL_WHITE="$GITHUB_BASE_URL/raw/main/pi-imager/stratux-logo-white192x192.png"

# cd to script directory
cd "$(dirname "$0")" || die "cd failed"
SRCDIR="$(realpath "$(pwd)"/..)"
mkdir -p $TMPDIR
cd $TMPDIR || die "cd failed"
mkdir -p $TMPDIR/out

# Download/extract image
wget -c $BASE_IMAGE_URL || die "Download failed"
unxz -k $ZIPNAME || die "Extracting image failed"

# Check where in the image the root partition begins:
bootoffset=$(parted $IMGNAME unit B p | grep fat32 | awk -F ' ' '{print $2}')
bootoffset=${bootoffset::-1}
partoffset=$(parted $IMGNAME unit B p | grep ext4 | awk -F ' ' '{print $2}')
partoffset=${partoffset::-1}

# Original image partition is too small to hold our stuff.. resize it to 5gb
truncate -s 5120M $IMGNAME || die "Image resize failed"
lo=$(losetup -f)
losetup $lo $IMGNAME
partprobe $lo
e2fsck -y -f ${lo}p2
parted --script ${lo} resizepart 2 100%
partprobe $lo || die "Partprobe failed failed"
resize2fs -p ${lo}p2 || die "FS resize failed"

# Mount image locally, clone our repo, install packages..
mkdir -p mnt
mount -t ext4 "${lo}"p2 mnt/ || die "root-mount failed"
mount -t vfat "${lo}"p1 mnt/boot || die "boot-mount failed"


# for groundsensor, disable ssh over serial cause it is needed for the sensor
# disable ssh over serial otherwise
# does not work in mk_configure_radar, since it is not mounted there when called via chroot mnt
# before first boot cmdline and config are still in /boot not /boot/firmware
sed -i mnt/boot/cmdline.txt -e "s/console=ttyAMA0,[0-9]\+ //"
sed -i mnt/boot/cmdline.txt -e "s/console=serial0,[0-9]\+ //"
sed -i mnt/boot/cmdline.txt -e "s/console=tty[0-9]\+ //"

# modify /boot/config.text for groundsensor
{
  echo "# modification for UART ground sensor"
  echo "enable_uart=1"
  echo "dtoverlay=miniuart-bt"
} | tee -a mnt/boot/config.txt

# install git for cloning repo (if not already installed) and pip
chroot mnt apt install git -y

cd mnt/$DISPLAY_SRC || die "cd failed"
su pi -c "git clone --recursive -b $BRANCH https://github.com/TomBric/stratux-radar-display.git"

cd ../../../
# run the configuration skript, that is also executed when setting up on target device
if [ "$V32" = true ]; then
  unshare -mpfu chroot mnt /bin/bash "$DISPLAY_SRC"/stratux-radar-display/image/mk_configure_radar.sh -i pico2tts
else
  unshare -mpfu chroot mnt /bin/bash "$DISPLAY_SRC"/stratux-radar-display/image/mk_configure_radar.sh
fi
unshare -mpfu chroot mnt /bin/bash "$DISPLAY_SRC"/stratux-radar-display/image/mk_config_webapp.sh

# mkdir -p out
umount mnt/boot
umount mnt

# Shrink the image to minimum size.. it's still larger than it really needs to be, but whatever
minsize=$(resize2fs -P ${lo}p2 | rev | cut -d' ' -f 1 | rev)
minsizeBytes=$(($minsize * 4096))
e2fsck -f ${lo}p2
resize2fs -p ${lo}p2 $minsize
zerofree ${lo}p2 # for smaller zip
bytesEnd=$(($partoffset + $minsizeBytes))
losetup -d ${lo}
# parted --script $IMGNAME resizepart 2 ${bytesEnd}B Yes doesn't seem tow rok any more... echo yes | parted .. neither. So we re-create partition with proper size
parted --script $IMGNAME rm 2
parted --script $IMGNAME unit B mkpart primary ext4 ${partoffset}B ${bytesEnd}B
truncate -s $(($bytesEnd + 4096)) $IMGNAME


cd "$SRCDIR" || die "cd failed"
# make sure the local version is also on current status
sudo -u pi git pull --rebase
release=$(git describe --tags --abbrev=0)
outname="-$release-$(git log -n 1 --pretty=%H | cut -c 1-8).img"
cd $TMPDIR || die "cd failed"

# Rename and zip webconfig version
mv $IMGNAME ${outprefix}-webconfig"${outname}"
zip out/${outprefix}-webconfig"${outname}".zip ${outprefix}-webconfig"${outname}"
# create os-list entry for pi imager
/bin/bash $SRCDIR/image/create-repo-list.sh "$outprefix"-webconfig"${outname}".zip "$REPONAME ${outname}" "Description" "$ICON_URL_WHITE" "$GITHUB_BASE_URL/releases/download/${release}/$outprefix-webconfig${outname}".zip "pi3-32bit" out/$outprefix-webconfig"${outname}.json"
# example for path of a release on github:
# https://github.com/TomBric/stratux-radar-display/releases/download/v2.12/v32-stratux-display-webconfig-v2.12-000d4f4b.img.zip
# example for logo path on github:
# https://github.com/TomBric/stratux-radar-display/raw/dev-trixie/pi-imager/stratux-logo-white192x192.png

if [ "${#USB_NAME}" -eq 0 ]; then
  echo "Final images have been placed into $TMPDIR/out. Please install and test the images."
else
  mv $TMPDIR/out/${outprefix}* /media/pi/"$USB_NAME"; umount /media/pi/"$USB_NAME"
  echo "Final images have been moved to usb stick $USB_NAME and umounted. Please install and test the images."
fi