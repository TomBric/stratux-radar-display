#!/bin/bash

# Thomas Breitbach 2026 configures an stratux image with radar-display-software installed
# modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:
# sudo apt install --yes parted zip unzip zerofree
# Run this script as root.
#  sudo /bin/bash mk_radar_on_stratux.sh stratux_image [-b <branch>][-u <USB-stick-name>]
# Run with argument "-b dev" to get the dev branch from github, otherwise with main
# Run with argument "-d <display>" to create an image for <display>, otherwise default is 'NoDisplay'
# The stratux version is read automatically from the stratux image
# Run with optional argument "-u <USB-stick-name>" to move created images on the usb stick and then umount this
# call examples:
#   sudo /bin/bash mk_radar_on_stratux.sh -i ../stratux_image/image_2026_09_09
#   sudo /bin/bash mk_radar_on_stratux.sh -i ../stratux_image/image_2026_09_09 -b dev
#   sudo /bin/bash mk_radar_on_stratux.sh -i ../stratux_image/image_2026_09_09 -d Epaper_1in54
# install a first time flashing of the t-beam, copies the content of the specified directory to /home/pi/stratux-radar-display/to_flash
#   sudo /bin/bash mk_radar_on_stratux.sh -i ../stratux_image/image_2026_09_09 -f /home/pi/GxAirCom81
# Enable sound output and UART Ground Sensor
#   sudo /bin/bash mk_radar_on_stratux.sh -i ../stratux_image/image_2026_09_09 -s


# REMARK: How to build a stratux image on your raspberry pi:
# git clone --recursive github.com/stratux/stratux.git
# install docker:curl -fsSL https://get.docker.com -o get-docker.sh
# run:   stratux/image_build/build.sh

# set -x
set -Eeuo pipefail
trap 'status=$?; echo "Command failed at line ${LINENO}: ${BASH_COMMAND}" >&2; exit "$status"' ERR

TMPDIR="/home/pi/image-tmp"
DISPLAY_SRC="home/pi"
LOCAL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

die() {
    echo "$1" >&2
    exit 1
}

# e2fsck returns 1 if errors were corrected, which is fine
check_e2fsck() {
    local status=0
    e2fsck "$@" || status=$?
    if [ "$status" -gt 1 ]; then
        die "e2fsck failed with status $status"
    fi
}

# set defaults
BRANCH=main
USB_NAME=""
DISPLAY_NAME="NoDisplay"
UART=false
FLASH=""
BASE_IMAGE_DIR=""
ZIPNAME=""

# pi imager settings
GITHUB_BASE_URL="https://github.com/TomBric/stratux-radar-display"
DEVICE_LIST="pi3-64bit, pi4-64bit"

# check parameters
while getopts ":i:b:d:u:f:s" opt; do
      case $opt in
        i)
          BASE_IMAGE_DIR="$(dirname "$OPTARG")"
          ZIPNAME="$(basename "$OPTARG")"
          ;;
        b) BRANCH="$OPTARG" ;;
        u) USB_NAME="$OPTARG" ;;
        d) DISPLAY_NAME="$OPTARG" ;;
        f) FLASH="$OPTARG" ;;
        s) UART=true ;;
        \?) echo "Invalid option: -$OPTARG"; exit 1 ;;
        :) echo "Option -$OPTARG requires a value."; exit 1 ;;
      esac
    done

# the stratux image is mandatory, it is used as base image for radar display installation
if [ -z "$ZIPNAME" ]; then
  echo "Usage: $0 -i <stratux_image> [-b <branch>] [-d <display>] [-u <USB-stick-name>] [-f <flash_dir>] [-s]" >&2
  exit 1
fi
[ -f "$BASE_IMAGE_DIR/$ZIPNAME" ] || die "Stratux image '$BASE_IMAGE_DIR/$ZIPNAME' not found"
# make path absolute, since the script changes the working directory
BASE_IMAGE="$(realpath "$BASE_IMAGE_DIR/$ZIPNAME")"
if [ -n "$FLASH" ]; then
  FLASH="$(realpath "$FLASH")"
fi

ICON_URL="$GITHUB_BASE_URL/raw/$BRANCH/pi-imager/stratux-logo-black192x192.png"

echo "Building stratux radar image for branch '$BRANCH' and display '$DISPLAY_NAME'"
if [ "$UART" = true ]; then
  echo "Enabling UART Ground Sensor support"
fi

IMGNAME="tmp-stratux.img"

# cd to script directory
cd "$(dirname "$0")" || die "cd failed"
SRCDIR="$(realpath "$(pwd)"/..)"
mkdir -p "$TMPDIR"
cd "$TMPDIR" || die "cd failed"
mkdir -p "$TMPDIR/out"

# Extract image
unzip -p "$BASE_IMAGE" > "$IMGNAME" || die "Extracting image failed"

# Check where in the image the root partition begins:
partoffset=$(parted "$IMGNAME" unit B p | grep ext4 | awk -F ' ' '{print $2}')
partoffset=${partoffset%B}
[[ "$partoffset" =~ ^[0-9]+$ ]] || die "Could not determine root partition offset"

# Original image partition is too small to hold our stuff.. resize it to 6gb
truncate -s 6144M "$IMGNAME" || die "Image resize failed"
lo=$(losetup -f)
ROOT_PART="${lo}p2"
losetup "$lo" "$IMGNAME"
partprobe "$lo"
check_e2fsck -y -f "$ROOT_PART"
parted --script "$lo" resizepart 2 100%
partprobe "$lo" || die "Partprobe failed"
resize2fs -p "$ROOT_PART" || die "FS resize failed"

# Mount image locally, clone our repo, install packages..
mkdir -p mnt
mount -t ext4 "$ROOT_PART" mnt/ || die "root-mount failed"
mount -t vfat "${lo}p1" mnt/boot || die "boot-mount failed"

# stratux is installed as debian package, read its version from the dpkg database of the image
VERSION=$(dpkg-query --admindir=mnt/var/lib/dpkg -W -f='${Version}' stratux) || die "Could not read stratux version from image"
[[ "$VERSION" =~ ^[0-9A-Za-z][0-9A-Za-z._+~-]*$ ]] || die "Unexpected stratux version '$VERSION'"
outprefix="stratux-$VERSION-radar"
REPONAME="Stratux $VERSION with Radar Display preinstalled(64-bit)"
echo "Stratux version in image: $VERSION"
# copy configurations of stratux
# persistend logging on and OGN transmission I2C off
cp "$LOCAL_DIR"/stratux.conf.radar mnt/boot/stratux.conf

# install git for cloning repo (if not already installed) and pip
chroot mnt apt update
chroot mnt apt install git python3-pip -y

# enable persistent logging
chroot mnt overlayctl disable

cd "mnt/$DISPLAY_SRC" || die "cd failed"
su pi -c "git clone --recursive -b ${BRANCH} https://github.com/TomBric/stratux-radar-display.git" || die "git clone failed"
IMAGE_REPO="$TMPDIR/mnt/$DISPLAY_SRC/stratux-radar-display"
release=$(git -C "$IMAGE_REPO" describe --tags --abbrev=0)
commit=$(git -C "$IMAGE_REPO" rev-parse --short=8 HEAD)
# copy T-Beam flash directory
if [ -n "$FLASH" ]; then
  su pi -c "cp -r '$FLASH' stratux-radar-display/to_flash"
  # modify stratux_radar.sh to execute flash-t-beam-once.sh during first startup
  sed -i "/\/bin\/bash/a\/bin\/bash \/$DISPLAY_SRC\/stratux-radar-display\/image\/flash-once.sh \/$DISPLAY_SRC\/stratux-radar-display\/to_flash" stratux-radar-display/image/stratux_radar.sh
fi
# set display
sed -i "s/NoDisplay/${DISPLAY_NAME}/g" stratux-radar-display/image/stratux_radar.sh
# back to root directory of stratux image
cd ../../../
# run stratux configuration skript
if [ "$UART" = true ]; then
  chroot mnt /bin/bash "$DISPLAY_SRC"/stratux-radar-display/image/configure_radar_on_stratux.sh -u
else
  chroot mnt /bin/bash "$DISPLAY_SRC"/stratux-radar-display/image/configure_radar_on_stratux.sh
fi

umount mnt/boot || die "umount boot failed"
umount mnt || die "umount root failed"


# Shrink the image to minimum size.. it's still larger than it really needs to be, but whatever
check_e2fsck -f "$ROOT_PART"
minsize=$(resize2fs -P "$ROOT_PART" | awk -F': ' '{print $2}')
blocksize=$(tune2fs -l "$ROOT_PART" | awk -F': *' '/Block size:/ {print $2; exit}')
blocksize=${blocksize:-4096}
minsizeBytes=$((minsize * blocksize))
resize2fs -p "$ROOT_PART" "$minsize"
zerofree "$ROOT_PART" # for smaller zip
bytesEnd=$((partoffset + minsizeBytes))
losetup -d "$lo"
# parted --script $IMGNAME resizepart 2 ${bytesEnd}B Yes doesn't seem tow rok any more... echo yes | parted .. neither. So we re-create partition with proper size
parted --script "$IMGNAME" rm 2
parted --script "$IMGNAME" unit B mkpart primary ext4 "${partoffset}B" "${bytesEnd}B"
truncate -s "$((bytesEnd + 4096))" "$IMGNAME"

outname="-$release-$commit.img"

mv "$IMGNAME" "out/${outprefix}${outname}"
echo "Starting xz of $IMGNAME to out/${outprefix}${outname}. This may take a while ..."
xz -v -k "out/${outprefix}${outname}"

# create os-list entry for pi imager
/bin/bash "$SRCDIR/image/create-repo-list.sh" "out/${outprefix}${outname}" "out/${outprefix}${outname}.xz" "$REPONAME ${release}" "Description" "$ICON_URL" "$GITHUB_BASE_URL/releases/download/${release}/${outprefix}${outname}.xz" "$DEVICE_LIST" "out/${outprefix}${outname}.json"
# example for path of a release on github:
# https://github.com/TomBric/stratux-radar-display/releases/download/v2.12/v32-stratux-display-webconfig-v2.12-000d4f4b.img.xz
rm "out/${outprefix}${outname}"

if [ "${#USB_NAME}" -eq 0 ]; then
  echo "Final image has been placed into $TMPDIR/out. Please install and test the images."
else
  cp "$TMPDIR"/out/"${outprefix}"* "/media/pi/$USB_NAME"
  umount "/media/pi/$USB_NAME"
  rm "$TMPDIR"/out/"${outprefix}"*
  echo "Final image has been moved to usb stick $USB_NAME and umounted. Please install and test the image."
fi