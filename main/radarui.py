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

import logging
import time
from gpiozero import Button

# global constants
HOLD_TIME = 1.0   # time to trigger the hold activity if one button is pressed longer


# global variables
left = Button(0)
middle = Button(0)
right = Button(0)
time_left = 0.0
status_left = False
time_right = 0.0
status_right = False
time_middle = 0.0
status_middle = False

# status variables for state machine
display_mode = ('init', 'radar', 'setup', 'ahrs', 'clock')
display_radius = (2, 5, 10, 20, 40)
height_diff = (10, 20, 50, 100, 500)
sound_on = True
mode = 0      # index in display mode
radius = 0    # index in display_radius
height = 0    # index in height_diff


def init():
    global left
    global middle
    global right

    left = Button(26)
    middle = Button(20)
    right = Button(21)


def start_radar_mode():
    global mode
    mode = 1


def communicate_limits(r, h):
    print("COMMUNICATE LIMITS: Radius " + str(r) + " Height " + str(h))


def check_user_input():
    global left
    global middle
    global right
    global status_middle
    global status_right
    global status_left
    global time_middle
    global time_right
    global time_left
    global radius
    global height

    radius = 0
    height = 0
    current_time = time.time()
    if mode == 1:  # radar mode

        if left.is_pressed():
            radius += 1 if radius < len(display_radius) else 0
            communicate_limits(display_radius[radius], height_diff[height])

        if right.is_pressed():
            radius += 1 if radius < len(display_radius) else 0
            communicate_limits(display_radius[radius], height_diff[height])

        if middle.is_pressed():
            if not status_middle:
                time_middle = current_time
                status_middle = True
            else:
                if current_time - time_middle > HOLD_TIME:   # pressed for a long time
                    print("Starting AHRS MODE")
        else:
            status_middle = False
