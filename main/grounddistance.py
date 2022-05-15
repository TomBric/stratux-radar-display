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
import datetime
import asyncio
import json
import math

# constants
MEASUREMENTS_PER_SECOND = 5   # number of distance ranging meaurements per second
VL53L1X_TIMING_BUDGET = 60   # 60 ms timing for reading distance, shorter values did not improve performance
# statistic file
SAVED_STATISTICS = "stratux-radar.stat"
# BEEP VALUES
DISTANCE_BEEP_MAX = 60              # in cm, where beeper starts with a low tone
DISTANCE_BEEP_MIN = 10              # in cm, where beeper stops with a high tone
# GPS-Measurement of start-distance
DISTANCE_START_DETECTED = 20 * 10       # in mm where measurement assumes that plane is in the air
DISTANCE_LANDING_DETECTED = 7.5 * 10    # in mm where measurement assumes to be landed
# start distance with groundsensor
STATS_PER_SECOND = 5    # how many statistics are written per second
STATS_TOTAL_TIME = 120   # time in seconds how long statistic window is
OBSTACLE_HEIGHT = 50     # in feet, height value to calculate as obstacle clearance, 15 meters
STOP_SPEED = 3           # in kts, speed when before runup or after landing a stop is assumed

# globals
ground_distance_active = False    # True if sensor is found and activated
indicate_distance = False   # True if audio indication for ground distance is active
distance_sensor = None
zero_distance = 0.0    # distance of sensor when aircraft is on ground
value_debug_level = 0    # set during init
# statistics for calculating values
statistics = []   # values for calculating everything
stats_max_values = STATS_PER_SECOND * STATS_TOTAL_TIME
stats_next_store = 0
global_situation = None
fly_status = 0   # status for evaluating statistics 0 = run up  1 = start_detected 2 = 15 m detected
                 # 3 = landing detected  4 = stop detected
runup_situation = None      # situation values, for accelleration on runway started
start_situation = None      # situation values when wheels leave the ground
obstacle_up_clear = None    # situation values when obstacle clearance was reached when taking off
obstacle_down_clear = None  # situation values when obstacle clearance was last reached when landing
landing_situation = None    # situation when wheels touch the ground
stop_situation = None       # siuation values when the aircraft is stopped on the runway


def reset_values():
    global runup_situation
    global start_situation
    global obstacle_up_clear
    global obstacle_down_clear
    global landing_situation
    global stop_situation
    global zero_distance
    global fly_status

    runup_situation = None
    start_situation = None
    obstacle_up_clear = None
    obstacle_down_clear = None
    landing_situation = None
    stop_situation = None
    fly_status = 0

    if distance_sensor is not None:
        zero_distance = distance_sensor.get_measurement()
        rlog.debug('Ground Zero Distance reset to: {0:5.2f} cm'.format(zero_distance / 10))


def init(activate, debug_level, distance_indication, situation):
    global rlog
    global ground_distance_active
    global indicate_distance
    global distance_sensor
    global value_debug_level
    global global_situation
    global zero_distance

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
        # shorter values do not optimize timing, typical measure timing takes 70 ms on a Zero2
    except Exception as e:
        ground_distance_active = False
        rlog.debug("Ground Distance Measurement - VL53L1X sensor not found: " + str(e))
        return False

    ground_distance_active = True
    value_debug_level = debug_level
    global_situation = situation   # to be able to read and store situation info
    rlog.debug("Ground Distance Measurement - VL53L1X active.")
    for i in range(1,10):
        distance_sensor.get_measurement()  # first measurements are not accurate, so do itseveral times
    zero_distance = distance_sensor.get_measurement()  # distance in mm, call is blocking, this is zero
    rlog.debug('Ground Zero Distance: {0:5.2f} cm'.format(zero_distance / 10))
    if distance_indication:
        indicate_distance = True
        rlog.debug("Ground Distance Measurement: indication distance activated")
    return ground_distance_active


def write_stats():
    global rlog

    if rlog is None:   # may be called before init
        rlog = logging.getLogger('stratux-radar-log')
    try:
        with open(SAVED_STATISTICS, 'at') as out:
            json.dump(calculate_output_values(), out, indent=4, default=str)
    except (OSError, IOError, ValueError) as e:
        rlog.debug("Grounddistance: Error " + str(e) + " writing " + SAVED_STATISTICS)
    rlog.debug("Grounddistance: Statistics saved to " + SAVED_STATISTICS)


def distance_beeper(distance):
    if indicate_distance:
        if DISTANCE_BEEP_MIN <= distance <= DISTANCE_BEEP_MAX:
            # to do tone_pitch = radarbluez.beep()
            pass


def is_airborne():
    return global_situation['g_distance'] >= DISTANCE_START_DETECTED


def has_landed():
    return global_situation['g_distance'] <= DISTANCE_LANDING_DETECTED


def radians_rel(angle):
    if angle > 180:
        angle = angle - 360
    if angle <= -180:
        angle = angle + 360
    return angle * math.pi / 180


def calc_gps_distance_meters(fr, to):
    radius_earth = 6371008.8
    avglat = radians_rel((fr['latitude'] + to['latitude']) / 2)
    distlat = radians_rel(to['latitude'] - fr['latitude']) * radius_earth
    distlng = (radians_rel(to['longitude'] - fr['longitude']) * radius_earth) * abs(math.cos(avglat))
    distance = math.sqrt((distlat * distlat) + (distlng * distlng))
    return distance


def takeoff_alt():
    if start_situation is not None and start_situation['baro_valid']:
        return start_situation['own_altitude']
    else:
        return None


def calculate_output_values():   # return output lines
    output = {}
    if start_situation is not None:
        output['start_time'] = start_situation['Time']
        if start_situation['baro_valid']:
            output['start_altitude'] = start_situation['own_altitude']
        if runup_situation is not None and runup_situation['gps_active'] and start_situation['gps_active']:
            output['takeoff_distance'] = calc_gps_distance_meters(start_situation, runup_situation)
        if obstacle_up_clear is not None and obstacle_up_clear['gps_active'] and start_situation['gps_active']:
            output['obstacle_distance_start'] = calc_gps_distance_meters(obstacle_up_clear, runup_situation)
    if stop_situation is not None and landing_situation is not None:
        output['landing_time'] =  landing_situation['Time']
        if landing_situation['baro_valid']:
            output['landing_altitude'] = landing_situation['own_altitude']
        if landing_situation['gps_active'] and stop_situation['gps_active']:
            output['landing_distance'] = calc_gps_distance_meters(stop_situation, landing_situation)
        if obstacle_down_clear is not None and obstacle_down_clear['gps_active'] and stop_situation['gps_active']:
            output['obstacle_distance_landing'] = calc_gps_distance_meters(stop_situation, obstacle_down_clear)
    return output


def evaluate_statistics(latest_stat):
    global statistics
    global fly_status
    global runup_situation
    global start_situation
    global obstacle_up_clear
    global landing_situation
    global obstacle_down_clear
    global stop_situation

    if fly_status == 0:    # run up
        if is_airborne():
            fly_status = 1   # start detected
            start_situation = latest_stat   # store this value
            rlog.debug("Grounddistance: Start detected " +
                       json.dumps(start_situation, indent=4, sort_keys=True, default=str))
            for stat in reversed(statistics): # ... find begin of start where gps_speed <= STOP_SPEED
                if stat['gps_speed'] <= STOP_SPEED:
                    runup_situation = stat
                    break
    elif fly_status == 1:   # start was detected
        if obstacle_up_clear is None:   # do not search for if already set
            if latest_stat['own_altitude'] >= start_situation['own_altitude'] + OBSTACLE_HEIGHT:
                obstacle_up_clear = latest_stat
                rlog.debug("Grounddistance: Obstacle clearance up detected " +
                           json.dumps(obstacle_up_clear, indent=4, sort_keys=True, default=str))
        if has_landed():
            fly_status = 2
            landing_situation = latest_stat
            rlog.debug("Grounddistance: Landing detected " +
                       json.dumps(landing_situation, indent=4, sort_keys=True, default=str))
            if obstacle_down_clear is None:
                for stat in reversed(statistics):
                    if stat['own_altitude'] >= latest_stat['own_altitude'] + OBSTACLE_HEIGHT:
                        obstacle_down_clear = stat
                        rlog.debug("Grounddistance: Obstacle clearance down found " +
                                   json.dumps(obstacle_down_clear, indent=4, sort_keys=True, default=str))
                        break
    elif fly_status == 2:   # landing detected, waiting for stop to calculate distance
        if latest_stat['gps_speed'] <= STOP_SPEED:
            fly_status = 0
            stop_situation = latest_stat
            rlog.debug("Grounddistance: Stop detected " +
                       json.dumps(stop_situation, indent=4, sort_keys=True, default=str))
            write_stats()


def store_statistics(sit):
    global stats_next_store
    global statistics

    if time.perf_counter() > stats_next_store:
        stats_next_store = time.perf_counter() + (1 / STATS_PER_SECOND)
        now = datetime.datetime.now(datetime.timezone.utc)
        stat_value = {'Time': now, 'baro_valid': sit['baro_valid'], 'own_altitude': sit['own_altitude'],
                      'gps_active': sit['gps_active'], 'longitude': sit['longitude'], 'latitude': sit['latitude'],
                      'gps_speed': sit['gps_speed'], 'g_distance_valid': sit['g_distance_valid'],
                      'g_distance':sit['g_distance'] }
        statistics.append(stat_value)
        if len(statistics) > stats_max_values:  # sliding window, remove oldest values
            statistics.pop(0)
        evaluate_statistics(stat_value)


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
                global_situation['g_distance_valid'] = True
                global_situation['g_distance'] = distance - zero_distance
                rlog.log(value_debug_level, 'Ground Distance: {0:5.2f} cm'.format(global_situation['g_distance'] / 10))
                store_statistics(global_situation)
        except (asyncio.CancelledError, RuntimeError):
            rlog.debug("Ground distance reader terminating ...")
            distance_sensor.stop_ranging()
            distance_sensor.close_connection()
    else:
        rlog.debug("No ground distance sensor active ...")
