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
MSG_NO_CONNECTION = "No Connection!"
MSG_NO_BARO = "No Barosensor!"
# globals


def init():
    pass


def draw_vsi(draw, display_control, was_changed, connected, vertical_speed, flight_level, gps_speed, gps_course,
             gps_altitude, vert_max, vert_min, gps_fixed, baro_valid):
    if was_changed:
        error_message = None
        if not connected:
            error_message = MSG_NO_CONNECTION
        if not baro_valid:
            error_message = MSG_NO_BARO
        if not gps_fixed:
            gps_course = 0.0   # no error message, just set all figures to zero
            gps_altitude = 0.0
            gps_speed = 0.0

        display_control.clear(draw)
        display_control.vsi(draw, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude,
                            vert_max, vert_min, error_message)
        display_control.display()


def user_input():
    btime, button = radarbuttons.check_buttons()
    # start of vsi global behaviour
    if btime == 0:
        return 0, False  # stay in current mode
    if button == 1 and (btime == 2 or btime == 1):  # middle
        return 7, False  # next mode to be status
    if button == 0 and btime == 2:  # left and long
        return 3, False  # start next mode shutdown!
    if button == 2 and btime == 1:  # right and short- reset values
        return 13, True  # start next mode for display driver: refresh called from vsi
    if button == 2 and btime == 2:  # right and long- refresh
        return 14, False  # start next mode for display driver: refresh called from vsi
    return 13, False  # no mode change for any other interaction
