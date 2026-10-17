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

# This mode is for flight testing. It enables to measure the starting distance.
# Just press "Start" before starting runup and then check when you are airborne,
# or to measure 15m obstacle clearance, check till 1.3*Vs1 is reached
# (see flight-testing handbook). You need to video record your EFIS or speed indicator
# along with the display

import math
import radarbuttons
import grounddistance
import datetime
import radarmodes
from globals import Modes
import radarmodes
from button_input import get_button_event, is_middle, is_middle_short, is_middle_long, is_left, is_left_short, is_left_long, is_right, is_right_short, is_right_long

# constants
MSG_NO_CONNECTION = "No Connection!"
# globals
gps_distance_zero = {'gps_active': False, 'longitude': 0.0, 'latitude': 0.0}
start_distance = 0.0    # runway needed till airborne, starts when "start" button is pressed
dist_user_mode = 0      # user input mode for distance display, 0 = normal, start   1=statistics display
statistic_index = 0
statistic_list = []
# gps-starting point in meters for situation and flight testing
baro_diff_zero = {}
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
    baro_diff_zero = {'own_altitude': situation['own_altitude']}

    grounddistance.reset_values()


def draw_distance(display_control, was_changed, connected, situation, ahrs):
    global start_distance

    # display in any case, even if there is no change, since time is running anyhow
    display_control.clear()
    if dist_user_mode == 0:
        error_message = None
        gps_distance = 0.0
        alt_diff = 0.0
        alt_diff_takeoff = 0.0
        if not connected:
            error_message = MSG_NO_CONNECTION
        else:
            if situation['baro_valid']:
                pressure_alt = situation['own_altitude']
                if baro_diff_zero:
                    alt_diff = pressure_alt - baro_diff_zero['own_altitude']
                else:
                    alt_diff = None
                if grounddistance.takeoff_alt() is not None:
                    alt_diff_takeoff = pressure_alt - grounddistance.takeoff_alt()
                else:
                    alt_diff_takeoff = None
            if situation['gps_active'] and gps_distance_zero['gps_active']:
                gps_distance = calc_gps_distance_meters(gps_distance_zero['latitude'], gps_distance_zero['longitude'],
                                                        situation['latitude'], situation['longitude'])
        now = datetime.datetime.now(datetime.timezone.utc)
        display_control.distance(now, situation['gps_active'], situation['gps_quality'],
                                 situation['gps_h_accuracy'],
                                 gps_distance_zero['gps_active'], gps_distance, situation['gps_speed'],
                                 situation['baro_valid'], situation['own_altitude'], alt_diff, alt_diff_takeoff,
                                 situation['vertical_speed'], ahrs['ahrs_sensor'],
                                 ahrs['pitch'], ahrs['roll'], situation['g_distance_valid'], situation['g_distance'],
                                 error_message)
    elif dist_user_mode == 1:   # show current statistics
        display_control.distance_statistics(grounddistance.calculate_output_values(), situation['gps_active'],
                                            situation['gps_altitude'], grounddistance.dest_elevation,
                                            grounddistance.dest_elevation != grounddistance.INVALID_DEST_ELEVATION,
                                            grounddistance.indicate_distance, current_stats=True)
    elif dist_user_mode == 2:  # show stored statistics
        if len(statistic_list) > statistic_index:
            display_control.distance_statistics(statistic_list[statistic_index],
                                                situation['gps_active'],situation['gps_altitude'],
                                                grounddistance.dest_elevation,
                                                grounddistance.dest_elevation != grounddistance.INVALID_DEST_ELEVATION,
                                                grounddistance.indicate_distance, current_stats=False,
                                                prev_stat=statistic_index != 0,
                                                next_stat=statistic_index != len(statistic_list) - 1,
                                                index=statistic_index)
        else: # no data available till now
            display_control.distance_statistics({}, situation['gps_active'], situation['gps_altitude'],
                                            grounddistance.dest_elevation,
                                            grounddistance.dest_elevation != grounddistance.INVALID_DEST_ELEVATION,
                                            grounddistance.indicate_distance, current_stats=False,
                                            prev_stat=False, next_stat=False, index=-1)
    elif dist_user_mode == 3:  # delete all statistics
        display_control.text_screen("Delete Statistics","", "Confirm to delete all statistics?", "YES", "Cancel", "NO")
    display_control.display()


def draw_countdown_distance(display_control, situation):
    # display in any case, even if there is no change, since values are constantly changing
    display_control.clear()
    if situation['g_distance_valid']:
        feet = situation['g_distance'] * grounddistance.MM_TO_FEET   # round down
        display_control.countdown_distance(feet)    # switch back is done by ground sensor reader
    display_control.display()


def user_input():
    global dist_user_mode
    global statistic_index
    global statistic_list

    event = get_button_event()
    if event is None:
        return Modes.NO_CHANGE, False
    if dist_user_mode == 0:
        if is_middle_long(event):
            return radarmodes.next_mode_sequence(Modes.SITUATION), False
        if is_middle_short(event):
            dist_user_mode = 2
            statistic_list = grounddistance.read_stats()
            if len(statistic_list) > 0:
                statistic_index = len(statistic_list) - 1
            else:
                statistic_index = 0
            return Modes.SITUATION, False
        if is_left_long(event):
            return Modes.SHUTDOWN, False
        if is_left_short(event):
            dist_user_mode = 1
            return Modes.SITUATION, False
        if is_right_short(event):
            return Modes.SITUATION, True
        if is_right_long(event):
            return Modes.REFRESH_SITUATION, False
        return Modes.SITUATION, False
    elif dist_user_mode == 1:
        if is_middle(event):
            dist_user_mode = 0
            return Modes.SITUATION, False
        if is_left_short(event):
            grounddistance.set_dest_elevation(+100)
            return Modes.SITUATION, False
        if is_left_long(event):
            grounddistance.set_dest_elevation(-100)
            return Modes.SITUATION, False
        if is_right_short(event):
            grounddistance.set_dest_elevation(+10)
            return Modes.SITUATION, False
        if is_right_long(event):
            grounddistance.set_dest_elevation(-10)
            return Modes.SITUATION, False
        return Modes.SITUATION, False
    elif dist_user_mode == 2:
        if is_middle(event):
            dist_user_mode = 0
            return Modes.SITUATION, False
        if is_right_short(event):
            statistic_list = grounddistance.read_stats()
            if len(statistic_list) > 0:
                statistic_index = (statistic_index + 1) % len(statistic_list)
            else:
                statistic_index = 0
            return Modes.SITUATION, False
        if is_left(event):
            statistic_list = grounddistance.read_stats()
            if len(statistic_list) > 0:
                statistic_index = (statistic_index - 1) % len(statistic_list)
            else:
                statistic_index = 0
            return Modes.SITUATION, False
        if is_right_long(event):
            dist_user_mode = 3
            return Modes.SITUATION, False
    elif dist_user_mode == 3:
        if is_left(event):
            grounddistance.delete_stats()
            statistic_index = 0
            statistic_list = []
            dist_user_mode = 2
            return Modes.SITUATION, False
        if is_middle(event) or is_right(event):
            dist_user_mode = 2
            return Modes.SITUATION, False
    return Modes.NO_CHANGE, False
