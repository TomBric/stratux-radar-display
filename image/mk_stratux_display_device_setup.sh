#!/bin/bash

# Thomas Breitbach 2024 for stratux-radar-display, modified, but mainly based on work for stratux europe by b3nn0
# To run this, make sure that this is installed:
# Do NOT run directly. This is called from mk_stratux_display.sh via chroot
# This is used to trigger systemctl commands inside a chrooted environmen

set -x
mount -t proc proc /proc
systemctl --user -M pi@ enable autostart-radar
# enable linger so that services will stay alive
loginctl enable-linger pi