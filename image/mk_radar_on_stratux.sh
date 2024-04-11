#!/bin/bash

# Thomas Breitbach 2024 configures an stratux image with radar-display-software installed
# modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:
# sudo apt install --yes parted zip unzip zerofree
# Run this script as root.
#  sudo /bin/bash mk_radar_on_stratux.sh [-b <branch>][-u <USB-stick-name>]
# Run with argument "-b dev" to get the dev branch from github, otherwise with main
# Run with optional argument "-u <USB-stick-name>" to move created images on the usb stick and then umount this
# call examples:
#   sudo /bin/bash mk_radar_on_stratux.sh
#   sudo /bin/bash mk_radar_on_stratux.sh -b dev

set -x
TMPDIR="/home/pi/image-tmp"
DISPLAY_SRC="home/pi"
LOCAL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

die() {
    echo "$1"
    exit 1
}

# set defaults
BRANCH=main
USB_NAME=""

# check parameters
while getopts ":b:u" opt; do
  case $opt in
    b)
      BRANCH="$OPTARG"
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

echo "Building stratux image for branch '$BRANCH' "

ZIPNAME="stratux-v1.6r1-eu030-150f2828.img.zip"
BASE_IMAGE_URL="https://github.com/b3nn0/stratux/releases/download/v1.6r1-eu030/${ZIPNAME}"
outprefix="stratux-eu30-with-display_3in7"
IMGNAME="${ZIPNAME%.*}"

# cd to script directory
cd "$(dirname "$0")" || die "cd failed"
SRCDIR="$(realpath "$(pwd)"/..)"
mkdir -p $TMPDIR
cd $TMPDIR || die "cd failed"

# Download/extract image
wget -c "$BASE_IMAGE_URL" || die "Download failed"
unzip "$ZIPNAME" || die "Extracting image failed"

# Check where in the image the root partition begins:
sector=$(fdisk -l "$IMGNAME" | grep Linux | awk -F ' ' '{print $2}')
partoffset=$(( 512*sector ))
bootoffset=$(fdisk -l "$IMGNAME" | grep W95 | awk -F ' ' '{print $2}')
if [[ $bootoffset == "*" ]]; then
    bootoffset=$(fdisk -l "$IMGNAME" | grep W95 | awk -F ' ' '{print $3}') # if boot flag is set...
fi
bootoffset=$(( 512*bootoffset ))

# Original image partition is too small to hold our stuff.. resize it to 5120 Mb
# Append one GB and truncate to size
truncate -s 6144M "$IMGNAME" || die "Image resize failed"
lo=$(losetup -f)
losetup "$lo" "$IMGNAME"
partprobe "$lo"
e2fsck -f "${lo}"p2
parted "${lo}" resizepart 2 100%
partprobe "$lo" || die "Partprobe failed failed"
resize2fs -p "${lo}"p2 || die "FS resize failed"

# Mount image locally, clone our repo, install packages..
mkdir -p mnt
mount -t ext4 "${lo}"p2 mnt/ || die "root-mount failed"
mount -t vfat "${lo}"p1 mnt/boot || die "boot-mount failed"

# copy configurations of stratux
# persistend logging on and OGN transmission I2C off
cp "$LOCAL_DIR"/stratux.conf.radar mnt/boot/stratux.conf

# install git for cloning repo (if not already installed) and pip
chroot mnt apt install git -y
# enable persistent logging
chroot mnt overlayctl disable

cd mnt/$DISPLAY_SRC || die "cd failed"
sudo -u pi git clone --recursive -b "$BRANCH" https://github.com/TomBric/stratux-radar-display.git
# set display to Epaper_3in7 only, at the moment just create this image
sudo -u pi sed -i 's/Oled_1in5/Epaper_3in7 -r/g' stratux-radar-display/image/stratux_radar.sh
# back to root directory of stratux image
cd ../../../
# run stratux configuration skript
chroot mnt /bin/bash $DISPLAY_SRC/stratux-radar-display/image/configure_radar_on_stratux.sh


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
truncate -s $((bytesEnd + 4096)) "$IMGNAME"


cd "$SRCDIR" || die "cd failed"
# make sure the local version is also on current status
sudo -u pi git pull --rebase
outname="-$(git describe --tags --abbrev=0)-$(git log -n 1 --pretty=%H | cut -c 1-8).img"
cd $TMPDIR || die "cd failed"

# Rename and zip oled version
mount -t ext4 -o offset=$partoffset "$IMGNAME" mnt/ || die "root-mount failed"


mv "$IMGNAME" ${outprefix}"${outname}"
zip out/${outprefix}"${outname}".zip ${outprefix}"${outname}"


if [ "${#USB_NAME}" -eq 0 ]; then
  echo "Final image has been placed into $TMPDIR/out. Please install and test the images."
else
  cp $TMPDIR/out/${outprefix}* /media/pi/"$USB_NAME"
  umount /media/pi/"$USB_NAME"
  rm $TMPDIR/out/${outprefix}*
  echo "Final image has been moved to usb stick $USB_NAME and umounted. Please install and test the image."
fi