#!/bin/bash

# Thomas Breitbach 2026 for stratux-radar-display, modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:

# Run this script as root.

# call example:
#   sudo /bin/bash mk_build_stratux.sh

set -x

RASPIOS_VERSION="2025-05-07"
FILENAME="2025-05-06-raspios-bookworm-arm64-lite.img.xz"
RASPIOS_DOWNLOAD_URL="https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-${RASPIOS_VERSION}/${FILENAME}"
TMPDIR="/home/pi/image-tmp"
IMAGEDIR=$(dirname "$(readlink -f "$0")")
# directory were this script is located, typically /home/pi/stratux-radar-display/image
OUTPREFIX="stratux-bookworm"

die() {
    echo "$1"
    exit 1
}

echo "Building stratux image based on Raspios Bookworm Lite ARM64 version ${RASPIOS_VERSION}"

ZIPNAME="${FILENAME}"
IMGNAME="${ZIPNAME%.*}"

# cd to script directory
cd "$(dirname "$0")" || die "cd failed"
SRCDIR="/root/stratux"
mkdir -p $TMPDIR
cd $TMPDIR || die "cd failed"
mkdir -p $TMPDIR/out

# Download/extract image
wget -c $RASPIOS_DOWNLOAD_URL || die "Download failed"
# xz anyhow to get a fresh the .img file
unxz -kf "$ZIPNAME" || die "Extracting base Bookworm image failed"

echo "Bookworm arm64 lite image prepared at $IMGNAME"
# Check where in the image the root partition begins:
bootoffset=$(parted $IMGNAME unit B p | grep fat32 | awk -F ' ' '{print $2}')
partoffset=$(parted $IMGNAME unit B p | grep ext4 | awk -F ' ' '{print $2}')

[ -n "$bootoffset" ] || die "Boot partition offset not found in $IMGNAME"
[ -n "$partoffset" ] || die "Root partition offset not found in $IMGNAME"

bootoffset=${bootoffset::-1}
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
unshare -mpfu chroot mnt apt update
# unshare -mpfu chroot mnt apt full-upgrade -y

echo "Installing git for cloning repo (if not already installed) and pip"
unshare -mpfu chroot mnt apt install git -y

# use Virus Pilot modified build script under /home/pi/stratux-radar-display/image/mk_build_stratux_sub.sh to build stratux in the image
cp -f "$IMAGEDIR/mk_build_stratux_sub.sh" mnt/root/mk_build_stratux_sub.sh || die "Copying sub build script failed"
unshare -mpfu chroot mnt /bin/bash /root/mk_build_stratux_sub.sh || die "sub build script failed"

# do all things that need access to mnt/boot, like copying config.txt and cmdline.txt modifications
cp mnt/stratux/image_build/stage2/10-stratux-files/config.txt mnt/boot/config.txt  || die "Copying config.txt failed"
touch mnt/boot/.stratux-first-boot   || die "Creating .stratux-first-boot failed"
#disable serial console, disable rfkill state restore, enable wifi on boot
sed -i mnt/boot/cmdline.txt -e "s/console=serial0,[0-9]\+ /systemd.restore_state=0 rfkill.default_state=1 /" || die "Modifying cmdline.txt failed"
cp -f config.txt mnt/boot/config.txt  || die "Copying config.txt failed"

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

cd "$SRCDIR" || die "cd failed - $SRCDIR does not exist, install stratux in $SRCDIR"
# make sure the local version is also on current status
sudo -u pi git pull --rebase
release=$(git describe --tags --abbrev=0)
outname="-$release-$(git log -n 1 --pretty=%H | cut -c 1-8).img"
cd $TMPDIR || die "cd failed"

# Rename and zip with xz
echo "Starting xz of $IMGNAME to out/${OUTPREFIX}${outname}. This may take a while..."
mv $IMGNAME out/${OUTPREFIX}"${outname}"
xz -vf out/${OUTPREFIX}"${outname}"


echo "Stratux image build complete. Image is located in $TMPDIR/out"