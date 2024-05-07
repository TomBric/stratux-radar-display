#!/bin/bash

# Thomas Breitbach 2024 for stratux-radar-display, modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:
# Do NOT run directly. This is called from mk_stratux_display.sh via chroot
# This is used to trigger systemctl commands inside a chrooted environmen

# set -x
mount -t proc proc /proc
# enable ssh
raspi-config nonint do_ssh 0
# enable spi and i2c (for cowarner)
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0
# enable linger so that services will stay alive