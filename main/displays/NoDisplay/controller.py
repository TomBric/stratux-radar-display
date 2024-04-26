#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2024, Thomas Breitbach
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
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE


# just the skeleton of all functions to be able to start without display
def display():
    pass


def is_busy():
    pass


def init(fullcircle=False):
    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("Running Radar with NoDisplay! ")
    max_pixel = 100   # some numbers
    zerox=50
    zeroy=50
    display_refresh = 0.1
    return max_pixel, zerox, zeroy, display_refresh


def cleanup():
    pass

def refresh():
    pass



def startup(version, target_ip, seconds):
    pass


def aircraft(x, y, direction, height, vspeed, nspeed_length, tail):
    pass

def modesaircraft(radius, height, arcposition, vspeed, tail):
    pass

def situation(connected, gpsconnected, ownalt, course, range, altdifference, bt_devices, sound_active,
              gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
    pass

def timer(utctime, stoptime, laptime, laptime_head, left_text, middle_text, right_t, timer_runs):
    pass

def meter(current, start_value, end_value, from_degree, to_degree, size, center_x, center_y,
          marks_distance, small_marks_distance, middle_text1, middle_text2):
    pass

def gmeter(current, maxg, ming, error_message):
    pass

def compass(heading, error_message):
    pass

def vsi(vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
        error_message):
    pass

def shutdown(countdown, shutdownmode):
    pass


def ahrs(pitch, roll, heading, slipskid, error_message):
    pass

def text_screen(headline, subline, text, left_text, middle_text, r_text):
    pass

def screen_input(headline, subline, text, left, middle, right, prefix, inp, suffix):
    pass



def stratux(stat, altitude, gps_alt, gps_quality):
    pass


def flighttime(last_flights):
    pass


def cowarner(co_values, co_max, r0, timeout, alarmlevel, alarmppm, alarmperiod):   # draw graph and co values
    pass


def distance(now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
             own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
             ground_distance_valid, grounddistance, error_message):
    pass


def distance_statistics(values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
    pass


def checklist(checklist_name, checklist_items, current_index, last_list):
    pass