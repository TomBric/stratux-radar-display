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


import logging
import melopero_vl53l1x as mp   # https://github.com/melopero/Melopero_VL53L1X
import time
import asyncio

# constants
MEASUREMENTS_PER_SECOND = 5   # number of distance ranging meaurements per second
VL53L1X_TIMING_BUDGET = 60   # 60 ms timing for reading distance, shorter values did not improve performance

# BEEP VALUES
DISTANCE_BEEP_MAX = 60              # in cm, where beeper starts with a low tone
DISTANCE_BEEP_MIN = 10              # in cm, where beeper stops with a high tone
# GPS-Measurement of start-distance
DISTANCE_START_DETECTED = 20        # in cm where measurement assumes that plane is in the air
DISTANCE_LANDING_DETECTED = 7.5     # in cm where measurement assumes to be landed

# globals
ground_distance_active = False    # True if sensor is found and activated
indicate_distance = False   # True if audio indication for ground distance is active
distance_sensor = None
value_debug_level = 0    # set during init
#


def init(activate, debug_level, distance_indication, situation):
    global rlog
    global ground_distance_active
    global indicate_distance
    global distance_sensor
    global value_debug_level
    global global_situation

    rlog = logging.getLogger('stratux-radar-log')
    if not activate:
        rlog.debug("Ground Distance Measurement - not activated")
        ground_distance_active = False
        return False
    try:
        distance_sensor = mp.VL53L1X()
        distance_sensor.start_ranging(mp.VL53L1X.SHORT_DST_MODE)
        # short distance mode is better in ambient light conditions and the range is up to 130 cm
        distance_sensor.set_measurement_timing_budget(50)
        # shorter values do not optimize timing
        # typical measure timing takes 70 ms on a Zero2
    except OSError:
        ground_distance_active = False
        rlog.debug("Ground Distance Measurement - VL53L1X sensor not found")
        return False

    ground_distance_active = True
    value_debug_level = debug_level
    global_situation = situation   # to be able to read and store situation info
    rlog.debug("Ground Distance Measurement - VL53L1X active.")
    if distance_indication:
        indicate_distance = True
        rlog.debug("Ground Distance Measurement: indication distance activated")
    return ground_distance_active


def distance_beeper(distance):
    if indicate_distance:
        if DISTANCE_BEEP_MIN <= distance <= DISTANCE_BEEP_MAX:
            # to do tone_pitch = radarbluez.beep()
            pass


def is_airborne():
    return global_situation['g_distance'] >= DISTANCE_START_DETECTED


def has_landed():
    return global_situation['g_distance'] <= DISTANCE_LANDING_DETECTED


async def read_ground_sensor():
    global distance_sensor
    global global_situation

    if ground_distance_active:
        try:
            rlog.debug("Ground distance reader active ...")
            next_read = time.perf_counter() + (1/MEASUREMENTS_PER_SECOND)
            while True:
                now = time.perf_counter()
                await asyncio.sleep(next_read - now)   # wait for next time of measurement
                next_read = now + (1/MEASUREMENTS_PER_SECOND)
                distance = distance_sensor.get_measurement()   # distance in mm, call is blocking!
                rlog.log(value_debug_level, 'Ground Distance: {0:5.2f} cm'.format(distance/10))
                global_situation['g_distance'] = distance
        except (asyncio.CancelledError, RuntimeError):
            rlog.debug("Ground distance reader terminating ...")
            distance_sensor.stop_ranging()
            distance_sensor.close_connection()
    else:
        rlog.debug("No ground distance sensor active ...")
