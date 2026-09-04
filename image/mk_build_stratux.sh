#!/bin/bash

# Thomas Breitbach 2026 for stratux-radar-display, modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:

# Run this script as root.

# call example:
#   sudo /bin/bash mk_build_stratux.sh


RASPIOS_VERSION="2025-05-07"
RASPIOS_DOWNLOAD_URL="https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-${RASPIOS_VERSION}/2025-05-06-raspios-bookworm-arm64-lite.img.xz"
TMPDIR="/home/pi/image-tmp"
OUTPREFIX="stratux-bookworm"

die() {
    echo "$1"
    exit 1
}

# set defaults
BRANCH=main
V32=false
USB_NAME=""

echo "Building stratux image based on Raspios Bookworm Lite ARM64 version ${RASPIOS_VERSION}"

ZIPNAME="${RASPIOS_FILE}"
IMGNAME="${ZIPNAME%.*}"

# cd to script directory
cd "$(dirname "$0")" || die "cd failed"
SRCDIR="/root/stratux"
mkdir -p $TMPDIR
cd $TMPDIR || die "cd failed"
mkdir -p $TMPDIR/out

# Download/extract image
wget -c $RASPIOS_DOWNLOAD_URL || die "Download failed"
# Nur entpacken, wenn die IMG-Datei noch nicht existiert
if [ ! -f "$IMGNAME" ]; then
    unxz -k "$ZIPNAME" || die "Extracting base Trixie image failed"
else
    echo "Image already exists, skipping extract: $IMGNAME"
fi

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
unshare -mpfu chroot mnt apt update
unshare -mpfu chroot mnt apt full-upgrade -y

echo "Installing git for cloning repo (if not already installed) and pip"
unshare -mpfu chroot mnt apt install git -y

# download and use Virus Pilot build script
unshare -mpfu chroot mnt bash -c "$(wget -nv -O - https://raw.githubusercontent.com/VirusPilot/stratux-pi4/master/setup-pi4-latest.sh)"

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

# Rename and zip with xz
echo "Starting xz of $IMAGENAME to out/${OUTPREFIX}${outname}. This may take a while..."
mv $IMGNAME out/${OUTPREFIX}"${outname}"
xz -v -k out/${OUTPREFIX}"${outname}"


echo "Stratux image build complete. Image is located in $TMPDIR/out"