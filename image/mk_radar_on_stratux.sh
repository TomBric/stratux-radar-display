#!/bin/bash

# Thomas Breitbach 2024 configures an stratux image with radar-display-software installed
# modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:
# sudo apt install --yes parted zip unzip zerofree
# Run this script as root.
#  sudo /bin/bash mk_radar_on_stratux.sh [-b <branch>][-u <USB-stick-name>]
# Run with argument "-b dev" to get the dev branch from github, otherwise with main
# Run with argument "-d <display>" to create an image for <display>, otherwise default is 'Epaper_3in7'
# Run with optional argument "-u <USB-stick-name>" to move created images on the usb stick and then umount this
# call examples:
#   sudo /bin/bash mk_radar_on_stratux.sh
#   sudo /bin/bash mk_radar_on_stratux.sh -b dev
#   sudo /bin/bash mk_radar_on_stratux.sh -d Epaper_1in54

# set -x
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
DISPLAY_NAME="Epaper_3in7"

# check parameters
while getopts ":b:d:u:" opt; do
  case $opt in
    b)
      BRANCH="$OPTARG"
      ;;
    u)
      USB_NAME="$OPTARG"
      ;;
    d)
      DISPLAY_NAME="$OPTARG"
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

echo "Building stratux image for branch '$BRANCH' and display '$DISPLAY_NAME'"

ZIPNAME="stratux-v1.6r1-eu032-ff1f01dc.img.zip"
BASE_IMAGE_URL="https://github.com/b3nn0/stratux/releases/download/v1.6r1-eu032/${ZIPNAME}"
outprefix="stratux-eu32-radar-webconfig"
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
bootoffset=$(parted $IMGNAME unit B p | grep fat32 | awk -F ' ' '{print $2}')
bootoffset=${bootoffset::-1}
partoffset=$(parted $IMGNAME unit B p | grep ext4 | awk -F ' ' '{print $2}')
partoffset=${partoffset::-1}

# Original image partition is too small to hold our stuff.. resize it to 4gb
truncate -s 4096M $IMGNAME || die "Image resize failed"
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

# copy configurations of stratux
# persistend logging on and OGN transmission I2C off
cp "$LOCAL_DIR"/stratux.conf.radar mnt/boot/stratux.conf

# install git for cloning repo (if not already installed) and pip
chroot mnt apt update
chroot mnt apt install git python3-pip -y
# Disable swap...
chroot systemctl disable dphys-swapfile
chroot apt purge -y dphys-swapfile
# Generate ssh key for all installs. Otherwise it would have to be done on each boot, which takes a couple of seconds
chroot ssh-keygen -A -v
chroot systemctl disable regenerate_ssh_host_keys




# enable persistent logging
chroot mnt overlayctl disable

cd mnt/$DISPLAY_SRC || die "cd failed"
su pi -c "git clone --recursive -b ${BRANCH} https://github.com/TomBric/stratux-radar-display.git"
# set display
sed -i "s/Oled_1in5/${DISPLAY_NAME}/g" stratux-radar-display/image/stratux_radar.sh
# back to root directory of stratux image
cd ../../../
# run stratux configuration skript
chroot mnt /bin/bash $DISPLAY_SRC/stratux-radar-display/image/configure_radar_on_stratux.sh

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
outname="-$(git describe --tags --abbrev=0)-$(git log -n 1 --pretty=%H | cut -c 1-8).img"
cd $TMPDIR || die "cd failed"

# Rename and zip oled version
mount -t ext4 -o offset=$partoffset "$IMGNAME" mnt/ || die "root-mount failed"


mv "$IMGNAME" "${outprefix}""${outname}"
zip out/"${outprefix}""${outname}".zip "${outprefix}""${outname}"
rm "${outprefix}""${outname}"


if [ "${#USB_NAME}" -eq 0 ]; then
  echo "Final image has been placed into $TMPDIR/out. Please install and test the images."
else
  cp $TMPDIR/out/"${outprefix}"* /media/pi/"$USB_NAME"
  umount /media/pi/"$USB_NAME"
  rm $TMPDIR/out/"${outprefix}"*
  echo "Final image has been moved to usb stick $USB_NAME and umounted. Please install and test the image."
fi