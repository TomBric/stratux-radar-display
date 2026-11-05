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

from globals import rlog, Modes
import requests
import radarbuttons
import radarmodes
import json
import dispatcher
from button_input import get_button_event, is_left_long, is_left_short, is_right_long, is_right_short, is_middle_long, is_middle_short

# status variables for state machine
display_radius = (2, 3, 5, 10, 20, 40)
height_diff = (1000, 2000, 5000, 10000, 50000)
sound_on = True
button_api_active = False

url_settings_set = ""
ble_address = None


def init(url, button_api, ble_address_param):
    global url_settings_set, ble_address

    if not radarbuttons.init(button_api):   # error occured, e.g. gpio pins are buse
        return False
    url_settings_set = url
    ble_address = ble_address_param
    rlog.debug("Radar UI: Initialized POST settings to " + url_settings_set)
    return True


def shutdown():
    radarbuttons.explicit_release_on_exit()


def communicate_limits(radarrange, threshold):
    if ble_address is None:
        rlog.debug("COMMUNICATE LIMITS: Radius " + str(radarrange) + " Height " + str(threshold))
        try:
            requests.post(url_settings_set, json={'RadarLimits': threshold, 'RadarRange': radarrange})
        except requests.exceptions.RequestException as e:
            rlog.debug("Posting limits exception", e)
    else:  # ble mode communicate via traffic msg
        traffic_msg = json.dumps({ 'RadarLimits': threshold, 'RadarRange': radarrange })
        rlog.debug(f"BLE COMMUNICATE LIMITS: {traffic_msg}")
        dispatcher.emit_traffic(traffic_msg)


def user_input(rrange, rlimits):   # return Nextmode, toogleSound  (Bool)
    try:
        radius = display_radius.index(rrange)
        height = height_diff.index(rlimits)
    except ValueError:
        radius = 2
        height = 0

    event = get_button_event()
    if event is None:
        return Modes.NO_CHANGE, False
    if is_left_long(event):
        return Modes.SHUTDOWN, False
    if is_left_short(event):
        radius += 1
        if radius >= len(display_radius):
            radius = 0
        communicate_limits(display_radius[radius], height_diff[height])
    elif is_right_long(event):
        return Modes.REFRESH_RADAR, False
    elif is_right_short(event):
        height += 1
        if height >= len(height_diff):
            height = 0
        communicate_limits(display_radius[radius], height_diff[height])
    elif is_middle_long(event):
        return radarmodes.next_mode_sequence(Modes.RADAR), False
    elif is_middle_short(event):
        rlog.debug("Sound toggled by UI")
        return Modes.RADAR, True
    return Modes.RADAR, False
