#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2022-2024, Thomas Breitbach
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

# To use Ultrasonic sensor, which is connected via UART add the following lines to /boot/config.txt
# enable_uart=1
# dtoverlay=miniuart-bt

# start and landing statistics are stored in stratux-radar.stat
# This file has json coded statistics for every flight, see this example
# {
#    "start_time": "2023-01-15 12:57:21.873912+00:00",
#    "start_altitude": 879.8726,
#    "takeoff_distance": 0.0,
#    "landing_time": "2023-01-15 12:57:22.106499+00:00",
#    "landing_altitude": 879.8606,
#    "landing_distance": 0.0
# }{
#    "start_time": "2023-01-15 12:57:28.223856+00:00",
#    "start_altitude": 880.92865,
#    "takeoff_distance": 0.0,
#    "landing_time": "2023-01-15 12:57:28.444494+00:00",
#    "landing_altitude": 880.77216,
#    "landing_distance": 0.0
# }

import logging
import radarmodes
import time
import datetime
import asyncio
import json
import math
import serial
import simulation
import radarbluez
import radarbuttons
import binascii

rlog = None  # radar specific logger

# constants
MEASUREMENTS_PER_SECOND = 10     # number of distance ranging meaurements per second
# A22 usonic sensor allows approx. 10 per second
# TFMini-Plus sensor allows 100 per second
UART_WAIT_TIME = 100   # wait time if no data is coming from the sensor
UART_BREAK_TIME = 1000   # time to break waiting

# GPS-Measurement of start-distance
DISTANCE_START_DETECTED = 30 * 10  # in mm where measurement assumes that plane is in the air
DISTANCE_LANDING_DETECTED = 15 * 10  # in mm where measurement assumes to be landed
OBSTACLE_HEIGHT = 50  # in feet, height value to calculate as obstacle clearance, 15 meters
STOP_SPEED = 5  # in kts, speed when before runup or after landing a stop is assumed

# start distance with groundsensor
STATS_PER_SECOND = 5  # how many statistics are written per second
STATS_FOR_SITUATION_CHANGE = 3  # no of values in a row before a situation is changed (landing/flying)
STATS_TOTAL_TIME = 120  # time in seconds how long statistic window is
INVALID_GDISTANCE = -9999   # indicates no valid grounddistance
INVALID_GPS_DISTANCE = -9999 # indicates no valid gps-distance

MIN_GPS_V_ACCURACY = 150   # minimum horizontal accuracy of gps, if not met, no speech warnings are spoken

GEAR_DOWN_WARNING = '<pitch level="110"> Gear down! </pitch>'    # warning to be spoken, when gear_
GEAR_NOT_DOWN_GO_AROUND = '<pitch level="130"> Go around! Gear not down! </pitch>'


# globals
ground_distance_active = False  # True if sensor is found and activated
indicate_distance = False  # True if audio indication for ground distance is active
distance_sensor = None
zero_distance = 0.0  # distance of sensor when aircraft is on ground
value_debug_level = 0  # set during init
simulation_mode = False  # set during init
# statistics for calculating values
statistics = []  # values for calculating everything
stats_max_values = STATS_PER_SECOND * STATS_TOTAL_TIME
stats_next_store = 0
global_situation = None
global_config = None
fly_status = 0  # status for evaluating statistics 0 = run up  1 = start_detected 2 = 15 m detected
# 3 = landing detected  4 = stop detected
runup_situation = None  # situation values, for accelleration on runway started
start_situation = None  # situation values when wheels leave the ground
obstacle_up_clear = None  # situation values when obstacle clearance was reached when taking off
obstacle_down_clear = None  # situation values when obstacle clearance was last reacheds when landing
landing_situation = None  # situation when wheels touch the ground
stop_situation = None  # siuation values when the aircraft is stopped on the runway

stats_before_airborne = 0
stats_before_landing = 0
stats_before_stop = 0
stats_before_obstacle_clear = 0
saved_statistics = None    # filename for statistics, set in init

gps_warnings = (1000, 500)    # speech warnings in feet, when calculated with gps
gps_upper = [False] * len(gps_warnings)  # is true, if height + hysteresis was met
sensor_warnings = (10, 5, 4, 3, 2, 1)   # speech warnings in feet, when calculated with groundsensor
sensor_upper = [False] * len(sensor_warnings) # is true, if height + hysteresis was met

gear_gps_warnings = (1000, 500, 400, 300, 200, 100)  # speech warnings if gear is not down, calculated with gps
gear_gps_upper = [False] * len(gear_gps_warnings)  # is true, if height + hysteresis was met
gear_sensor_warnings= (10, 5)   # speech warnings if gear is not down based on sensor
gear_sensor_upper = [False] * len(gear_sensor_warnings)  # is true, if height + hysteresis was met

hysteresis = 1.3    # hysteresis 10% for speech warnings,
# this means a ground warning is only repeated if more than 10% more of height was reached in between

INVALID_DEST_ELEVATION = 9999.0
MIN_ELEVATION = -999.0
dest_elevation = INVALID_DEST_ELEVATION
# elevation for destination airport for height warnings, set to maximum if not set

# sound variable for prepared pygame sounds
gps_warnings_sounds = None
sensor_warnings_sounds = None
gear_not_down_warning_sound = None
go_around_warning_sound = None


def set_dest_elevation(dest_increment):
    global dest_elevation
    if dest_elevation == INVALID_DEST_ELEVATION:
        if global_situation['gps_active']:
            dest_elevation = math.ceil (global_situation['gps_altitude'] / 10) * 10   # round up to 10
        else:
            dest_elevation = dest_increment   # start with the first values, 100 or 10
    else:
        dest_elevation = dest_elevation + dest_increment
        if dest_elevation >= INVALID_DEST_ELEVATION or dest_elevation <= MIN_ELEVATION:
            # set to invalid if too high or too low
            dest_elevation = INVALID_DEST_ELEVATION
    rlog.debug('Grounddistance: Destination Altitude set to {0:5.0f}'.format(dest_elevation))


class UsonicSensor:   # definition adapted from DFRobot code
    distance_max = 3000
    distance_min = 5
    ser = None
    distance = 0

    def init(self):
        self.ser = serial.Serial("/dev/ttyAMA0", 115200)     # A22 module has 115200 baud
        self.ser.flushInput()
        if not self.ser.isOpen():
            return False
        return True

    def set_dis_range(self, mini, maxi):
        self.distance_max = maxi
        self.distance_min = mini

    @staticmethod
    def _check_sum(le):
        return (le[0] + le[1] + le[2]) & 0x00ff

    def last_distance(self):
        return self.distance

    async def calc_distance(self):
        data = [0] * 4
        timenow = time.time()
        while self.ser.inWaiting() < 4:
            await asyncio.sleep(UART_WAIT_TIME)
            if (time.time() - timenow) > UART_BREAK_TIME:
                break
        rlt = self.ser.read(self.ser.inWaiting())
        if len(rlt) >= 4:
            index = len(rlt) - 4
            while True:
                try:
                    data[0] = ord(rlt[index])
                except TypeError:
                    data[0] = rlt[index]
                if data[0] == 0xFF:
                    break
                elif index > 0:
                    index = index - 1
                else:
                    break
            if data[0] == 0xFF:
                try:
                    data[1] = ord(rlt[index + 1])
                    data[2] = ord(rlt[index + 2])
                    data[3] = ord(rlt[index + 3])
                except TypeError:
                    data[1] = rlt[index + 1]
                    data[2] = rlt[index + 2]
                    data[3] = rlt[index + 3]
                sumd = self._check_sum(data)
                if sumd == data[3]:
                    self.distance = data[1] * 256 + data[2]
                    if self.distance > self.distance_max or self.distance < self.distance_min:
                        self.distance = 0


class LidarSensor:   # Implementation for TFMini-Plus Lidar Sensor
    lidar_bytes = 9
    distance_max = 5000    # sensor is able to detect till 12 meters but reliable only to 4 m in bad conditions
    distance_min = 100     # 10 cm min
    ser = None
    distance = 0
    strength = 0
    celsius = 0

    def init(self):
        self.ser = serial.Serial("/dev/ttyAMA0", 115200)     # Lidar module has 115200 baud
        self.ser.flushInput()
        if not self.ser.isOpen():
            return False
        return True

    def last_distance(self):
        return self.distance
    def calc_distance(self):
        if  self.ser.inWaiting() < self.lidar_bytes:
            rlog.debug("Error, no data received from Lidar sensor")
            return
        result = self.ser.read(self.ser.inWaiting())
        rlog.log(value_debug_level, f"Lidar sensor - Bytes received: {len(result)} : {binascii.hexlify(result)} ")
        if len(result) >= self.lidar_bytes:
            index = len(result) - self.lidar_bytes
            while True:   # find last 0x59 0x59
                 if result[index] == 0x59 and result[index + 1] == 0x59:
                     break
                 else:
                     if index > 0:
                         index = index - 1
                     else:
                         rlog.debug("Lidar-Sensor: Frame Header not found")
                         return
            # here we found two 0x59, now check checksum
            checksum = 0x00
            for i in range(self.lidar_bytes - 1):
                checksum += result[index + i]
            if (checksum & 0xFF) == result[index + 8]:  # checksum check
                # now calculate distance and strength
                self.distance = 10 * (result[index + 2] + result[index + 3] * 256)
                if self.distance > self.distance_max or self.distance < self.distance_min:
                    self.distance = 0
                self.strength = result[index + 4] + result[index + 3] * 256
                self.celsius = result[index + 6] + result[index + 7] * 256
                #  Convert temp code to degrees Celsius.
                self.celsius =  self.celsius / 8 - 256
                rlog.log(value_debug_level, "Lidar-Sensor: Distance {self.distance} Strength {self.strength} Celsius {self.celsius}")
            else:
                 rlog.debug(f"Lidar-Sensor: Invalid checksum")
        else:
              rlog.debug(f"Lidar-Sensor: Error less bytes read than expected")



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

    if ground_distance_active:
        new_zero_distance = distance_sensor.last_distance()   # take last value, don't wait (no async function)
        if new_zero_distance > 0:
            zero_distance = new_zero_distance
            rlog.debug('Ground Zero Distance reset to: {0:5.2f} cm'.format(zero_distance / 10))
        else:
            rlog.debug('Error resetting gound zero distance')


def init(activate, stat_file, debug_level, distance_indication, situation, sim_mode, g_config):
    global rlog
    global ground_distance_active
    global indicate_distance
    global distance_sensor
    global value_debug_level
    global global_situation
    global zero_distance
    global simulation_mode
    global saved_statistics
    global global_config

    simulation_mode = sim_mode
    global_config = g_config
    rlog = logging.getLogger('stratux-radar-log')
    if not activate:
        rlog.debug("Ground Distance Measurement - not activated.")
        ground_distance_active = False
        return False
    try:
        distance_sensor = LidarSensor()
        if not distance_sensor.init():
            rlog.debug("Ground Distance Measurement - Error init ultrasonic sensor, serial not found")
            ground_distance_active = False
            return False
    except Exception as e:
        ground_distance_active = False
        rlog.debug("Ground Distance Measurement - Ultrasonic sensor not found: " + str(e))
        return False

    ground_distance_active = True
    value_debug_level = debug_level
    saved_statistics = stat_file
    global_situation = situation  # to be able to read and store situation info
    rlog.debug("Ground Distance Measurement - Ground sensor active.")

    if distance_indication:
        indicate_distance = True
        rlog.debug("Ground Distance Measurement: indication distance activated")
        prepare_sounds()
    return ground_distance_active


def write_stats():
    global rlog

    if rlog is None:  # may be called before init
        rlog = logging.getLogger('stratux-radar-log')
    try:
        with open(saved_statistics, 'at') as out:
            json.dump(calculate_output_values(), out, indent=4, default=str)
    except (OSError, IOError, ValueError) as e:
        rlog.debug("Grounddistance: Error " + str(e) + " writing " + saved_statistics)


def read_stats(stats_file=None):   # returns a list of all written stats
    global rlog
    
    if rlog is None:
        rlog = logging.getLogger('stratux-radar-log')
    if stats_file is None:
        stats_file = saved_statistics
        if stats_file is None:
            return []    # groundsensor not initialized, return empty
    try:
        with open(stats_file, 'rt') as f:
            # Read the entire file and split by '}{' to handle multiple JSON objects
            content = f.read()
            # Replace '}{' with '}\n{' to properly separate JSON objects
            json_objects = content.replace('}{', '}\n{')
            # Parse each JSON object
            stats = [json.loads(obj) for obj in json_objects.split('\n') if obj.strip()]
            return stats
    except FileNotFoundError:
        rlog.debug(f"Grounddistance: Statistics file {stats_file} not found")
        return []
    except json.JSONDecodeError as e:
        rlog.debug(f"Grounddistance: Error decoding JSON from {stats_file}: {str(e)}")
        return []
    except (OSError, IOError) as e:
        rlog.debug(f"Grounddistance: Error reading {stats_file}: {str(e)}")
        return []


def prepare_sounds():
    global gps_warnings_sounds
    global sensor_warnings_sounds
    global gear_not_down_warning_sound
    global go_around_warning_sound

    gps_warnings_sounds = radarbluez.prepare_sounds_tuple(gps_warnings)
    sensor_warnings_sounds = radarbluez.prepare_sounds_tuple(sensor_warnings)
    gear_not_down_warning_sound = radarbluez.prepare_sounds_string(GEAR_DOWN_WARNING)
    go_around_warning_sound = radarbluez.prepare_sounds_string(GEAR_NOT_DOWN_GO_AROUND)


def calc_distance_speaker(stat):
    if stat['gps_active'] and stat['gps_v_accuracy'] < MIN_GPS_V_ACCURACY:
        gps_distance = stat['gps_altitude'] - dest_elevation   # both are in ft
    else:
        gps_distance = INVALID_GPS_DISTANCE
    if stat['g_distance_valid']:
        ground_distance = stat['g_distance'] / 328.1    # g_distance is in mm, here we need ft
    else:
        ground_distance = 0.0
    if indicate_distance and fly_status == 1:
        for (i, height) in enumerate(gps_warnings):
            if gps_distance != INVALID_GPS_DISTANCE:
                if gps_distance <= height and gps_upper[i]:
                    # distance is reached and was before higher than hysteresis
                    if gps_warnings_sounds is not None:
                        radarbluez.speak_sound(gps_warnings_sounds[i])
                    gps_upper[i] = False
                if gps_distance >= height * hysteresis:
                    gps_upper[i] = True
        for (i, height) in enumerate(sensor_warnings):
            if stat['g_distance_valid']:
                if ground_distance <= height and sensor_upper[i]:
                    # distance is reached and was before higher than hysteresis
                    if sensor_warnings_sounds is not None:
                        radarbluez.speak_sound(sensor_warnings_sounds[i])
                    sensor_upper[i] = False
                if ground_distance >= height * hysteresis:
                    sensor_upper[i] = True
    if global_config['gear_indication_active'] and fly_status == 1:
        for (i, height) in enumerate(gear_gps_warnings):
            if gps_distance != INVALID_GPS_DISTANCE:
                if gps_distance <= height and gear_gps_upper[i]:
                    if stat['gear_down'] is False and gear_not_down_warning_sound is not None:
                        radarbluez.speak_sound(gear_not_down_warning_sound, GEAR_DOWN_WARNING)
                    gear_gps_upper[i] = False
                if gps_distance >= height * hysteresis:
                    gear_gps_upper[i] = True
        for (i, height) in enumerate(gear_sensor_warnings):
            if stat['g_distance_valid']:
                if ground_distance <= height and gear_sensor_upper[i]:
                    # distance is reached and was before higher than hysteresis
                    if stat['gear_down'] is False and go_around_warning_sound is not None:
                        radarbluez.speak_sound(go_around_warning_sound, GEAR_NOT_DOWN_GO_AROUND)
                    gear_sensor_upper[i] = False
                if ground_distance >= height * hysteresis:
                    gear_sensor_upper[i] = True


def is_airborne():
    global stats_before_airborne

    if global_situation['g_distance_valid'] and global_situation['g_distance'] >= DISTANCE_START_DETECTED:
        stats_before_airborne += 1
        if stats_before_airborne >= STATS_FOR_SITUATION_CHANGE:
            stats_before_airborne = 0
            return True
    else:
        stats_before_airborne = 0
    return False


def has_landed():
    global stats_before_landing

    if global_situation['g_distance_valid'] and global_situation['g_distance'] <= DISTANCE_LANDING_DETECTED:
        stats_before_landing += 1
        if stats_before_landing >= STATS_FOR_SITUATION_CHANGE:
            stats_before_landing = 0
            return True
    else:
        stats_before_landing = 0
    return False


def has_stopped():
    global stats_before_stop

    if global_situation['gps_speed'] <= STOP_SPEED:
        stats_before_stop += 1
        if stats_before_stop >= STATS_FOR_SITUATION_CHANGE:
            stats_before_stop = 0
            return True
    else:
        stats_before_stop = 0
    return False


def obstacle_is_clear(current_alt, alt_to_clear):
    global stats_before_obstacle_clear

    if current_alt >= alt_to_clear:
        stats_before_obstacle_clear += 1
        if stats_before_obstacle_clear >= STATS_FOR_SITUATION_CHANGE:
            stats_before_obstacle_clear = 0
            return True
    else:
        stats_before_obstacle_clear = 0
    return False


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


def calculate_output_values():  # return output lines
    output = {}
    if start_situation is not None:
        output['start_time'] = start_situation['Time']
        if start_situation['baro_valid']:
            output['start_altitude'] = start_situation['own_altitude']
        if runup_situation is not None and runup_situation['gps_active'] and start_situation['gps_active']:
            output['takeoff_distance'] = calc_gps_distance_meters(start_situation, runup_situation)
        if runup_situation is not None and obstacle_up_clear is not None and\
                obstacle_up_clear['gps_active'] and runup_situation['gps_active']:
            output['obstacle_distance_start'] = calc_gps_distance_meters(obstacle_up_clear, runup_situation)
    if landing_situation is not None:
        output['landing_time'] = landing_situation['Time']
        if landing_situation['baro_valid']:
            output['landing_altitude'] = landing_situation['own_altitude']
        if stop_situation is not None and landing_situation['gps_active'] and stop_situation['gps_active']:
            output['landing_distance'] = calc_gps_distance_meters(stop_situation, landing_situation)
        if stop_situation is not None and obstacle_down_clear is not None and \
                obstacle_down_clear['gps_active'] and stop_situation['gps_active']:
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

    if fly_status == 0:  # run up
        if is_airborne():
            fly_status = 1  # start detected
            start_situation = latest_stat  # store this value
            obstacle_down_clear = None  # in case a second start is done, clear all values
            obstacle_up_clear = None
            landing_situation = None
            stop_situation = None
            rlog.debug("Grounddistance: Start detected " +
                       json.dumps(start_situation, indent=4, sort_keys=True, default=str))
            for stat in reversed(statistics):  # ... find begin of start where gps_speed <= STOP_SPEED
                if stat['gps_active'] and stat['gps_speed'] <= STOP_SPEED:
                    runup_situation = stat
                    break
    elif fly_status == 1:  # start was detected
        if obstacle_up_clear is None:  # do not search for if already set
            if latest_stat['baro_valid'] and start_situation['baro_valid'] and \
                    obstacle_is_clear(latest_stat['own_altitude'], start_situation['own_altitude'] + OBSTACLE_HEIGHT):
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
                    if stat['baro_valid'] and landing_situation['baro_valid'] and \
                      obstacle_is_clear(stat['own_altitude'], landing_situation['own_altitude'] + OBSTACLE_HEIGHT):
                        obstacle_down_clear = stat
                        rlog.debug("Grounddistance: Obstacle clearance down found " +
                                   json.dumps(obstacle_down_clear, indent=4, sort_keys=True, default=str))
                        break
    elif fly_status == 2:  # landing detected, waiting for stop to calculate distance
        if has_stopped():
            fly_status = 0
            stop_situation = latest_stat
            rlog.debug("Grounddistance: Stop detected " +
                       json.dumps(stop_situation, indent=4, sort_keys=True, default=str))
            write_stats()
            statistics.clear()  # start fresh with statistics
        elif is_airborne():  # touch and go performed!
            fly_status = 1  # go back to flying mode
            landing_situation = None  # clear landing situation, only last landing is recorded
            obstacle_down_clear = None  # clear obstacle down, only last landing is recorded
            rlog.debug("Grounddistance: Re-Start detected without stop, keeping first start " +
                       json.dumps(start_situation, indent=4, sort_keys=True, default=str))
    calc_distance_speaker(latest_stat)

def store_statistics(sit):
    global stats_next_store

    if simulation_mode:
        sim_data = simulation.read_simulation_data()
        if sim_data is not None:
            if 'g_distance' in sim_data and sim_data['g_distance'] > 0:
                sit['g_distance_valid'] = True
                sit['g_distance'] = sim_data['g_distance']
            else:
                sit['g_distance_valid'] = False
                sit['g_distance'] = INVALID_GDISTANCE
            if 'gps_speed' in sim_data:
                sit['gps_speed'] = sim_data['gps_speed']
                sit['gps_active'] = True
            if 'gps_altitude' in sim_data:
                sit['gps_altitude'] = sim_data['gps_altitude']
                sit['gps_active'] = True
                sit['gps_hor_accuracy'] = 50  # just any nice valud
            if 'own_altitude' in sim_data:
                sit['own_altitude'] = sim_data['own_altitude']
                sit['baro_valid'] = True
            if 'gear_down' in sim_data:
                sit['gear_down'] = sim_data['gear_down']
            else:
                sit['gear_down'] = False
    if time.perf_counter() > stats_next_store:
        stats_next_store = time.perf_counter() + (1 / STATS_PER_SECOND)
        now = datetime.datetime.now(datetime.timezone.utc)
        stat_value = {'Time': now, 'baro_valid': sit['baro_valid'], 'own_altitude': sit['own_altitude'],
                      'gps_active': sit['gps_active'], 'longitude': sit['longitude'], 'latitude': sit['latitude'],
                      'gps_speed': sit['gps_speed'], 'gps_altitude': sit['gps_altitude'],
                      'gps_h_accuracy': sit['gps_h_accuracy'], 'gps_v_accuracy': sit['gps_v_accuracy'],
                      'g_distance_valid': sit['g_distance_valid'], 'g_distance': sit['g_distance'],
                      'gear_down': sit['gear_down']}
        statistics.append(stat_value)
        if len(statistics) > stats_max_values:     # sliding window, remove old values
            statistics.pop(0)
        evaluate_statistics(stat_value)


async def read_ground_sensor():
    global zero_distance

    if ground_distance_active:
        rlog.debug("Ground distance reader active ...")
        distance_sensor.calc_distance()
        new_zero_distance = distance_sensor.last_distance()  # distance in mm this is zero
        if new_zero_distance > 0:
            zero_distance = new_zero_distance  # distance in mm this is zero
            rlog.debug('Ground Zero Distance: {0:5.2f} cm'.format(zero_distance / 10))
        else:
            rlog.debug('Ground Zero Distance: Error reading ground distance, not set')
        try:
            next_read = time.perf_counter() + (1 / MEASUREMENTS_PER_SECOND)
            while True:
                now = time.perf_counter()
                await asyncio.sleep(next_read - now)  # wait for next time of measurement
                next_read = next_read + (1 / MEASUREMENTS_PER_SECOND)
                distance_sensor.calc_distance()
                distance = distance_sensor.last_distance()  # distance in mm
                if distance > 0:
                    global_situation['g_distance_valid'] = True
                    global_situation['g_distance'] = distance - zero_distance
                    rlog.log(value_debug_level,
                             'Ground Distance: {0:5.2f} cm'.format(global_situation['g_distance'] / 10))
                else:
                    global_situation['g_distance_valid'] = False
                    global_situation['g_distance'] = INVALID_GDISTANCE   # just to be safe
                    rlog.log(value_debug_level, 'Ground Distance: Sensor value invalid, maybe out of range')
                if global_config['gear_indication_active']:
                    global_situation['gear_down'] = radarbuttons.gear_is_down()
                    rlog.log(value_debug_level, 'Ground Distance: gear-down: {0}'.format(global_situation['gear_down']))
                else:
                    global_situation['gear_down'] = False   # default value if not to be indicated
                store_statistics(global_situation)
        except (asyncio.CancelledError, RuntimeError):
            rlog.debug("Ground distance reader terminating ...")
    else:
        rlog.debug("No ground distance sensor active.")

