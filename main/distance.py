#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2022, Thomas Breitbach
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

import math
import radarbuttons
import datetime

# constants
MSG_NO_CONNECTION = "No Connection!"
# globals
gps_distance_zero = {'gps_active': False, 'longitude': 0.0, 'latitude': 0.0}
# gps-starting point in meters for situation and flight testing
baro_diff_zero = {'own_altitude': 0.0}
# height starting point based on baro in feet for situation and flight testing


def radians_rel(angle):
    if angle > 180:
        angle = angle - 360
    if angle <= -180:
        angle = angle + 360
    return angle * math.pi / 180


def calc_gps_distance_meters(from_lat, from_lng, to_lat, to_lng):
    radius_earth = 6371008.8
    avglat = radians_rel((from_lat + to_lat) / 2)
    distlat = radians_rel(to_lat - from_lat) * radius_earth
    distlng = (radians_rel(to_lng - from_lng) * radius_earth) * abs(math.cos(avglat))
    distance = math.sqrt((distlat * distlat) + (distlng * distlng))
    return distance


def init():
    pass


def reset_values(situation):
    global gps_distance_zero
    global baro_diff_zero

    gps_distance_zero['gps_active'] = situation['gps_active']
    gps_distance_zero['longitude'] = situation['longitude']
    gps_distance_zero['latitude'] = situation['latitude']
    baro_diff_zero['own_altitude'] = situation['own_altitude']


def draw_distance(draw, display_control, was_changed, connected, situation, ahrs):
    # display in any case, even if there is no change, since time is running anyhow
    error_message = None
    gps_distance = 0.0
    alt_diff = 0.0
    if not connected:
        error_message = MSG_NO_CONNECTION
    else:
        if situation['baro_valid']:
            pressure_alt = situation['own_altitude']
            alt_diff = pressure_alt - baro_diff_zero['own_altitude']
        if situation['gps_active'] and gps_distance_zero['gps_active']:
            gps_distance = calc_gps_distance_meters(gps_distance_zero['latitude'], gps_distance_zero['longitude'],
                                                    situation['latitude'], situation['longitude'])
    now = datetime.datetime.now(datetime.timezone.utc)
    display_control.clear(draw)
    display_control.distance(draw, now, situation['gps_active'], situation['gps_quality'], situation['gps_h_accuracy'],
                              gps_distance_zero['gps_active'], gps_distance, situation['gps_speed'],
                              situation['baro_valid'], situation['own_altitude'], alt_diff,
                              situation['vertical_speed'], ahrs['ahrs_sensor'],
                              ahrs['pitch'], ahrs['roll'], error_message)
    display_control.display()


def user_input():
    btime, button = radarbuttons.check_buttons()
    # start of situation global behaviour, status is 21
    if btime == 0:
        return 0, False  # stay in current mode
    if button == 1 and (btime == 2 or btime == 1):  # middle
        return 1, False  # next mode to be radar
    if button == 0 and btime == 2:  # left and long
        return 3, False  # start next mode shutdown!
    if button == 2 and btime == 1:  # right and short- reset values
        return 21, True  # reset values in radar.py
    if button == 2 and btime == 2:  # right and long- refresh
        return 22, False  # start next mode for display driver: refresh called from vsi
    return 21, False  # no mode change for any other interaction
