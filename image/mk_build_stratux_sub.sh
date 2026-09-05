#!/bin/bash

# Thomas Breitbach 2026 for stratux-radar-display, modified, but mainly based on work from VirusPilot
# Run this script as root.
# call example:
#   sudo /bin/bash mk_build_stratux_sub.sh

#!/bin/bash
set -x

# prepare libs
apt install \
  libjpeg62-turbo-dev \
  libconfig9 \
  rpi-update \
  dnsmasq \
  git \
  libusb-1.0-0-dev \
  build-essential \
  autoconf \
  libtool \
  i2c-tools \
  libfftw3-dev \
  libncurses-dev \
  python3-serial \
  jq \
  ifplugd \
  iptables \
  libttspico-utils \
  libdbus-1-dev \
  libglib2.0-dev \
  libudev-dev \
  libical-dev \
  libreadline-dev \
  automake \
  pkg-config \
  python3-pygments \
  cmake \
  python3-pip \
  debhelper -y

# install esptool for tracker flashing
pip install --break-system-packages esptool

# install latest golang
cd /root
wget https://go.dev/dl/go1.27.0.linux-arm64.tar.gz
tar xzf *.gz
rm *.gz

# compile and install librtlsdr from source (latest)
cd /root
git clone https://github.com/osmocom/rtl-sdr
cd rtl-sdr
sed -i '$a\\noverride_dh_autoreconf:\n\t:' debian/rules # prevent autoreconf from running
dpkg-buildpackage -b --no-sign
cd ..
dpkg -i librtlsdr0_*.deb
dpkg -i librtlsdr-dev_*.deb
dpkg -i rtl-sdr_*.deb
rm -f *.deb
rm -f *.buildinfo
rm -f *.changes

# legacy DVB-T TV drivers need to be properly blacklisted (e.g. they will activate the bias tee by default)
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee --append /etc/modprobe.d/blacklist-dvb_usb_rtl28xxu.conf

# install bluez
cd /root
wget https://github.com/stratux/bluez/releases/download/v1.0/bluez_5.79-1_arm64.deb
dpkg -i *.deb
rm -f *.deb

# install kalibrate-rtl
cd /root
git clone https://github.com/steve-m/kalibrate-rtl
cd kalibrate-rtl
./bootstrap && ./configure && make && sudo make install

# Prepare wiringpi for ogn trx via GPIO
cd /root
git clone https://github.com/WiringPi/WiringPi.git
cd WiringPi
./build

# clone stratux
cd /root && git clone --recursive https://github.com/stratux/stratux.git /root/stratux

# checkout v1.6 (5283a06)
# cd /root/stratux && git checkout 5283a06

# checkout latest dump1090
cd /root/stratux/dump1090 && git pull origin master

# checkout latest ogn
# cd /root/stratux && git fetch origin && git restore --source=origin/master -- ogn/

# copy various files
# cd /root/stratux/image (for v1.6)
cd /root/stratux/image_build/stage2/10-stratux/files
cp -f config.txt /boot/firmware/config.txt
cp -f bashrc.txt /root/.bashrc
cp -f rc.local /etc/rc.local
cp -f modules.txt /etc/modules
cp -f motd /etc/motd
cp -f rtl-sdr-blacklist.conf /etc/modprobe.d/
cp -f stxAliases.txt /root/.stxAliases
cp -f stratux-dnsmasq.conf /etc/dnsmasq.d/stratux-dnsmasq.conf
cp -f wpa_supplicant_ap.conf /etc/wpa_supplicant/wpa_supplicant_ap.conf
cp -f interfaces /etc/network/interfaces
cp -f sshd_config /etc/ssh/sshd_config

#rootfs overlay stuff
cp -f overlayctl init-overlay /sbin/
overlayctl install
# init-overlay replaces raspis initial partition size growing.. Make sure we call that manually (see init-overlay script)
#touch /var/grow_root_part
mkdir -p /overlay/robase # prepare so we can bind-mount root even if overlay is disabled

# So we can import network settings if needed
touch /boot/firmware/.stratux-first-boot

# Optionally mount /dev/sda1 as /var/log - for logging to USB stick
#echo -e "\n/dev/sda1             /var/log        auto    defaults,nofail,noatime,x-systemd.device-timeout=1ms  0       2" >> /etc/fstab

#disable serial console, disable rfkill state restore, enable wifi on boot
sed -i /boot/firmware/cmdline.txt -e "s/console=serial0,[0-9]\+ /systemd.restore_state=0 rfkill.default_state=1 /"

# prepare services
systemctl enable ssh
systemctl disable dnsmasq # we start it manually on respective interfaces
#systemctl disable hciuart
systemctl disable triggerhappy
systemctl disable wpa_supplicant
systemctl disable apt-daily.timer
systemctl disable apt-daily-upgrade.timer
systemctl disable man-db.timer
systemctl disable systemd-timesyncd

# Run DHCP on eth0 when cable is plugged in
sed -i -e 's/INTERFACES=""/INTERFACES="eth0"/g' /etc/default/ifplugd

# Generate ssh key for all installs. Otherwise it would have to be done on each boot, which takes a couple of seconds
ssh-keygen -A -v
systemctl disable regenerate_ssh_host_keys
# This is usually done by the console-setup service that takes quite long of first boot..
/lib/console-setup/console-setup.sh

# build Stratux Europe
source /root/.bashrc
cd /root/stratux
make
make install

# disable swapfile
systemctl disable dphys-swapfile
apt purge dphys-swapfile -y

# purge list from stratux image_build/stage2/10-stratux/files/purge-list.txt

apt autoremove -y
apt clean

# disable autologin
rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf
