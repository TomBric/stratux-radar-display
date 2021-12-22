#!/bin/bash

# Thomas Breitbach 2021 for stratux-radar-display, modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:
# sudo apt install --yes parted zip unzip zerofree
# If you want to build on x86 with aarch64 emulation, additionally install qemu-user-static qemu-system-arm
# Run this script as root.
# Run with argument "dev" to not clone the stratux repository from remote, but instead copy this current local checkout onto the image
# call examples:
#   sudo /bin/bash mk_stratux_display.sh "Create failed" dev
#   sudo /bin/bash mk_stratux_display.sh "Create failed" main

set -x
BASE_IMAGE_URL="https://downloads.raspberrypi.org/raspios_armhf/images/raspios_armhf-2021-11-08/2021-10-30-raspios-bullseye-armhf.zip"
ZIPNAME="2021-10-30-raspios-bullseye-armhf.zip"
IMGNAME="${ZIPNAME%.*}.img"
TMPDIR="/home/pi/stratux-display-tmp"
DISPLAY_SRC="home/pi"


die() {
    echo $1
    exit 1
}

if [ "$#" -lt 2 ]; then
    echo "Usage: " $0 "  <fail output> dev|main"
    exit 1
fi

# cd to script directory
cd "$(dirname "$0")"
SRCDIR="$(realpath $(pwd)/..)"
mkdir -p $TMPDIR
cd $TMPDIR

# Download/extract image
wget -c $BASE_IMAGE_URL || die "Download failed"
unzip $ZIPNAME || die "Extracting image failed"


# Check where in the image the root partition begins:
sector=$(fdisk -l $IMGNAME | grep Linux | awk -F ' ' '{print $2}')
partoffset=$(( 512*sector ))
bootoffset=$(fdisk -l $IMGNAME | grep W95 | awk -F ' ' '{print $2}')
if [[ $bootoffset == "*" ]]; then
    bootoffset=$(fdisk -l $IMGNAME | grep W95 | awk -F ' ' '{print $3}') # if boot flag is set...
fi
bootoffset=$(( 512*bootoffset ))

# Original image partition is too small to hold our stuff.. resize it to 4000 Mb
# Append one GB and truncate to size
truncate -s 4000M $IMGNAME || die "Image resize failed"
lo=$(losetup -f)
losetup $lo $IMGNAME
partprobe $lo
e2fsck -f ${lo}p2
parted ${lo} resizepart 2 100%
partprobe $lo || die "Partprobe failed failed"
resize2fs -p ${lo}p2 || die "FS resize failed"

# Mount image locally, clone our repo, install packages..
mkdir -p mnt
mount -t ext4 ${lo}p2 mnt/ || die "root-mount failed"
mount -t vfat ${lo}p1 mnt/boot || die "boot-mount failed"

cd mnt/$DISPLAY_SRC
git clone --recursive -b $2 https://github.com/TomBric/stratux-radar-display.git
cd ../../../
chroot mnt /bin/bash $DISPLAY_SRC/stratux-radar-display/image/mk_configure_radar.sh
mkdir -p out

# copy wpa_config and create empty ssh
cp mnt/$DISPLAY_SRC/stratux-radar-display/image/wpa_supplicant.conf mnt/boot
touch mnt/boot/ssh

umount mnt/boot
umount mnt

# Shrink the image to minimum size.. it's still larger than it really needs to be, but whatever
minsize=$(resize2fs -P ${lo}p2 | rev | cut -d' ' -f 1 | rev)
minsizeBytes=$(($minsize * 4096))
e2fsck -f ${lo}p2
resize2fs -p ${lo}p2 $minsize

zerofree ${lo}p2 # for smaller zip

bytesEnd=$((partoffset + $minsizeBytes))
parted -s ${lo} resizepart 2 ${bytesEnd}B yes
partprobe $lo

losetup -d ${lo}
truncate -s $(($bytesEnd + 4096)) $IMGNAME


cd $SRCDIR
outname="stratux-display-$(git describe --tags --abbrev=0)-$(git log -n 1 --pretty=%H | cut -c 1-8).img"
cd $TMPDIR

# Rename and zip EU version
mv $IMGNAME ${outname}_oled
zip out/${outname}_oled.zip ${outname}_oled


# Now create epaper version.
mount -t vfat -o offset=$bootoffset $outname mnt/ || die "boot-mount failed"
sed -i 's/Oled_1in5/Epaper_3in7/g' mnt/$DISPLAY_SRC/stratux-radar-display/image/stratux_radar.sh
umount mnt
mv $outname ${outname}_epaper
zip out/${outname_epaper}.zip ${outname}_epaper


echo "Final images have been placed into $TMPDIR/out. Please install and test the image."