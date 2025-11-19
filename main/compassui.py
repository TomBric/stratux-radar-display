#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2021, Thomas Breitbach
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import radarbuttons
import radarmodes
from globals import Modes

# constants
MSG_NO_CONNECTION = "No Connection!"
# globals
compassui_changed = True


def init(url):
    pass   # nothing to do right now


def draw_compass(display_control, changed, connected, heading):
    global compassui_changed

    if changed or compassui_changed:
        error_message = None
        compassui_changed = False
        if not connected:
            error_message = MSG_NO_CONNECTION
        display_control.clear()
        display_control.compass(heading, error_message)
        display_control.display()


def user_input():
    global compassui_changed

    btime, button = radarbuttons.check_buttons()
    # start of ahrs global behaviour
    if btime == 0:
        return Modes.NO_CHANGE  # stay in current mode
    compassui_changed = True
    if button == 1 and (btime == 1 or btime == 2):  # middle in any case
        return radarmodes.next_mode_sequence(Modes.COMPASS)    # next mode
    if button == 0 and btime == 2:  # left and long
        return Modes.SHUTDOWN  # start next mode shutdown!
    if button == 2 and btime == 2:  # right and long: refresh
        return Modes.REFRESH_COMPASS  # start next mode for display driver: refresh called
    return Modes.COMPASS  # no mode change
