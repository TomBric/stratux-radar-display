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

# constants
# globals
ahrs_ui_changed = True
calibrate_url = ""   # url of stratux to initiate AHRS calibration
cage_url = ""        # url of stratux to initation Zero Drift


MSG_GROUND_TEST = "No GPS,Ground ONLY!"
MSG_PSEUDO_AHRS = "PSEUDO AHRS ONLY!"
MSG_NO_AHRS = "NO IMU OR GPS!"
MSG_NO_CONNECTION = "NO CONNECTION!"
MSG_CALIBRATING = "CALIBRATING-FLY LEVEL"


def init(display_control, calib_url, cage):   # prepare everything
    global calibrate_url
    global cage_url

    calibrate_url = calib_url
    cage_url = cage


def draw_ahrs(draw, display_control, connected, was_changed, pitch, roll, heading, slip, gps_hor_accuracy,
              ahrs_sensor, is_caging):
    global ahrs_ui_changed

    if was_changed or ahrs_ui_changed:
        ahrs_ui_changed = False
        error_message = None
        if gps_hor_accuracy >= 30 and ahrs_sensor:
            error_message = MSG_GROUND_TEST
        if gps_hor_accuracy >= 30 and not ahrs_sensor:
            error_message = MSG_NO_AHRS
        if gps_hor_accuracy < 30 and not ahrs_sensor:
            error_message = MSG_PSEUDO_AHRS
        if not connected:
            error_message = MSG_NO_CONNECTION
        if is_caging:
            error_message = MSG_CALIBRATING
        display_control.clear(draw)
        display_control.ahrs(draw, pitch, roll, heading, slip, error_message)
        display_control.display()


def calibrate():
    rlog.debug("Calibration initiated by button press!")
    try:
        requests.post(calibrate_url)
    except requests.exceptions.RequestException as e:
        rlog.debug("Error posting calibration request: {0}".format(e))


def zero_drift():
    log.debug("Zero drift initiated by button press!")
    try:
        requests.post(cage_url)
    except requests.exceptions.RequestException as e:
        rlog.debug("Error posting zero drif request: {0}".format(e))


def user_input():
    global ahrs_ui_changed

    btime, button = radarbuttons.check_buttons()
    # start of ahrs global behaviour
    if btime == 0:
        return 0  # stay in timer mode
    ahrs_ui_changed = True
    if button == 1 and (btime == 2 or btime == 1):  # middle in any case
        return radarmodes.next_mode_sequence(5)  # next mode
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 2 and btime == 2:  # right and long: refresh
        return 6  # start next mode for display driver: refresh called from ahrs
    if button == 2 and btime == 1:  # right and short, start zero drift
        zero_drift()
        return 5
    if button == 0 and btime == 1:  # left and short: calibrate
        calibrate()
        return 5
    return 5  # no mode change
