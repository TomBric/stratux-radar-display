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
# Run with optional argument "-w" to use bookworm images (either 32 bit or 64 bis)
# call examples:
#   sudo /bin/bash mk_stratux_display.sh
#   sudo /bin/bash mk_stratux_display.sh -b dev
#   sudo /bin/bash mk_stratux_display.sh -b dev -k v32

# set -x
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

echo "Building images for branch '$BRANCH' V32=$V32 based on Bookworm"

if [ "$V32" = true ]; then
  IMAGE_VERSION="armhf"
  outprefix="v32-stratux-display"
else
  IMAGE_VERSION="arm64"
  outprefix="stratux-display"
fi

ZIPNAME="2024-03-15-raspios-bookworm-${IMAGE_VERSION}-lite.img.xz"
BASE_IMAGE_URL="https://downloads.raspberrypi.org/raspios_lite_${IMAGE_VERSION}/images/raspios_lite_${IMAGE_VERSION}-2024-03-15/${ZIPNAME}"


IMGNAME="${ZIPNAME%.*}"

# cd to script directory
cd "$(dirname "$0")" || die "cd failed"
SRCDIR="$(realpath "$(pwd)"/..)"
mkdir -p $TMPDIR
cd $TMPDIR || die "cd failed"

# Download/extract image
wget -c $BASE_IMAGE_URL || die "Download failed"
xz -d $ZIPNAME || die "Extracting image failed"


# Check where in the image the root partition begins:
sector=$(fdisk -l $IMGNAME | grep Linux | awk -F ' ' '{print $2}')
partoffset=$(( 512*sector ))
bootoffset=$(fdisk -l $IMGNAME | grep W95 | awk -F ' ' '{print $2}')
if [[ $bootoffset == "*" ]]; then
    bootoffset=$(fdisk -l $IMGNAME | grep W95 | awk -F ' ' '{print $3}') # if boot flag is set...
fi
bootoffset=$(( 512*bootoffset ))

# Original image partition is too small to hold our stuff.. resize it to 5120 Mb
# Append one GB and truncate to size
truncate -s 4000M $IMGNAME || die "Image resize failed"
lo=$(losetup -f)
losetup "$lo" $IMGNAME
partprobe "$lo"
e2fsck -y -f "${lo}"p2
parted "${lo}" resizepart 2 100%
partprobe "$lo" || die "Partprobe failed failed"
resize2fs -p "${lo}"p2 || die "FS resize failed"

# Mount image locally, clone our repo, install packages..
mkdir -p mnt
mount -t ext4 "${lo}"p2 mnt/ || die "root-mount failed"
mount -t vfat "${lo}"p1 mnt/boot || die "boot-mount failed"


die "manually STOPPED for debugging"

# for groundsensor, disable ssh over serial cause it is needed for the sensor
# disable ssh over serial otherwise
# does not work in mk_configure_radar, since it is not mounted there when called via chroot mnt
sed -i mnt/boot/firmware/cmdline.txt -e "s/console=ttyAMA0,[0-9]\+ //"
sed -i mnt/boot/firmware/cmdline.txt -e "s/console=serial0,[0-9]\+ //"
sed -i mnt/boot/firmware/cmdline.txt -e "s/console=tty[0-9]\+ //"
# modify /boot/firmware/config.text for groundsensor
{
  echo "# modification for ultrasonic ground sensor"
  echo "enable_uart=1"
  echo "dtoverlay=miniuart-bt"
} | tee -a mnt/boot/firmware/config.txt


# install git for cloning repo (if not already installed) and pip
chroot mnt apt install git -y

cd mnt/$DISPLAY_SRC || die "cd failed"
sudo -u pi git clone --recursive -b "$BRANCH" https://github.com/TomBric/stratux-radar-display.git
cd ../../../
chroot mnt /bin/bash $DISPLAY_SRC/stratux-radar-display/image/mk_configure_radar.sh "$BRANCH"

# mkdir -p out
umount mnt/boot
umount mnt

# Shrink the image to minimum size.. it's still larger than it really needs to be, but whatever
minsize=$(resize2fs -P "${lo}"p2 | rev | cut -d' ' -f 1 | rev)
minsizeBytes=$((minsize * 4096))
e2fsck -f "${lo}"p2
resize2fs -p "${lo}"p2 "$minsize"

zerofree "${lo}"p2 # for smaller zip

bytesEnd=$((partoffset + minsizeBytes))
parted -s "${lo}" resizepart 2 ${bytesEnd}B yes
partprobe "$lo"

losetup -d "${lo}"
truncate -s $((bytesEnd + 4096)) $IMGNAME


cd "$SRCDIR" || die "cd failed"
# make sure the local version is also on current status
sudo -u pi git pull --rebase
outname="-$(git describe --tags --abbrev=0)-$(git log -n 1 --pretty=%H | cut -c 1-8).img"
cd $TMPDIR || die "cd failed"

# Rename and zip oled version
mv $IMGNAME ${outprefix}-oled"${outname}"
zip out/${outprefix}-oled"${outname}".zip ${outprefix}-oled"${outname}"


# Now create epaper 3.7 version.
mount -t ext4 -o offset=$partoffset ${outprefix}-oled"${outname}" mnt/ || die "root-mount failed"
# save old command line to put it back to oled later
sed -i 's/Epaper_3in7/TEMP_EP/g' mnt/$DISPLAY_SRC/stratux-radar-display/image/stratux_radar.sh
sed -i 's/Oled_1in5/Epaper_3in7 -r/g' mnt/$DISPLAY_SRC/stratux-radar-display/image/stratux_radar.sh
sed -i 's/TEMP_EP/Oled_1in5/g' mnt/$DISPLAY_SRC/stratux-radar-display/image/stratux_radar.sh
umount mnt
mv ${outprefix}-oled"${outname}" ${outprefix}-epaper_3in7"${outname}"
zip out/${outprefix}-epaper_3in7"${outname}".zip ${outprefix}-epaper_3in7"${outname}"

# Now create epaper 1.54 version.
mount -t ext4 -o offset=$partoffset ${outprefix}-epaper_3in7"${outname}" mnt/ || die "root-mount failed"
# save old command line to put it back to oled later
sed -i 's/Epaper_1in54/TEMP_EP/g' mnt/$DISPLAY_SRC/stratux-radar-display/image/stratux_radar.sh
sed -i 's/Epaper_3in7 -r/Epaper_1in54/g' mnt/$DISPLAY_SRC/stratux-radar-display/image/stratux_radar.sh
sed -i 's/TEMP_EP/Epaper_1in54/g' mnt/$DISPLAY_SRC/stratux-radar-display/image/stratux_radar.sh
umount mnt
mv ${outprefix}-epaper_3in7"${outname}" ${outprefix}-epaper_1in54"${outname}"
zip out/${outprefix}-epaper_1in54"${outname}".zip ${outprefix}-epaper_1in54"${outname}"
# remove last unzipped image
rm ${outprefix}-epaper_1in54"${outname}"

if [ "${#USB_NAME}" -eq 0 ]; then
  echo "Final images have been placed into $TMPDIR/out. Please install and test the images."
else
  mv $TMPDIR/out/${outprefix}* /media/pi/"$USB_NAME"; umount /media/pi/"$USB_NAME"
  echo "Final images have been moved to usb stick $USB_NAME and umounted. Please install and test the images."
fi