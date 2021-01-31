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

# constants
# globals
ahrs_ui_changed = True


def init(display_control):   # prepare everything
    display_control.init_ahrs()


def draw_ahrs(draw, display_control, was_changed, pitch, roll, heading, slip):
    global ahrs_ui_changed

    if was_changed or ahrs_ui_changed:
        ahrs_ui_changed = False
        display_control.clear(draw)
        display_control.ahrs(draw, pitch, roll, heading, slip)
        display_control.display()


def user_input():
    global ahrs_ui_changed

    btime, button = radarbuttons.check_buttons()
    # start of ahrs global behaviour
    if btime == 0:
        return 0  # stay in timer mode
    ahrs_ui_changed = True
    if button == 1 and btime == 2:  # middle and long
        print("AHRS UI: long middle pressed")
        return 1  # next mode to be radar
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    return 5  # no mode change
