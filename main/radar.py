#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2020, Thomas Breitbach
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

import signal
import argparse
import json
import asyncio
import socket
import websockets
import logging
import math
import time
import radarbluez
import radarui
import timerui
import shutdownui
import ahrsui
import statusui
import gmeterui
import compassui
import verticalspeed
import importlib
import subprocess
import radarbuttons
import stratuxstatus
import flighttime
import cowarner
import distance
import grounddistance
import radarmodes
import simulation
import checklist
from datetime import datetime, timezone

# logging
SITUATION_DEBUG = logging.DEBUG - 2  # another low level for debugging, DEBUG is 10
AIRCRAFT_DEBUG = logging.DEBUG - 1  # another low level for debugging below DEBUG
rlog = None  # radar specific logger
#

# constant definitions
RADAR_VERSION = "1.92"

RETRY_TIMEOUT = 1
LOST_CONNECTION_TIMEOUT = 0.3
RADAR_CUTOFF = 29
UI_REACTION_TIME = 0.1
MINIMAL_WAIT_TIME = 0.01  # give other coroutines some time to do their jobs
BLUEZ_CHECK_TIME = 3.0
SPEED_ARROW_TIME = 60  # time in seconds for the line that displays the speed
WATCHDOG_TIMER = 3.0  # time after "no connection" is assumed, if no new situation is received
CHECK_CONNECTION_TIMEOUT = 5.0
# timeout used for regular status request, necessary towards stratux to keep the websockets open
MIN_DISPLAY_REFRESH_TIME = 0.1
# minimal time to wait for a display refresh, to give time for situation and traffic
MAX_TIMER_OFFSET = 10
# max time the local system time and the received GPS-Time may differ. If they differ, system time will be set
OPTICAL_ALIVE_BARS = 10
# number of bars for an optical alive
OPTICAL_ALIVE_TIME = 3
# time in secs after which the optical alive bar moves on

# global variables
DEFAULT_URL_HOST_BASE = "192.168.10.1"
DEFAULT_MIXER = "Speaker"  # default mixer name to be used for sound output
CONFIG_DIR = "../../"
CONFIG_FILE = CONFIG_DIR + "stratux-radar.conf"
DEFAULT_CHECKLIST = CONFIG_DIR + "checklist.xls"
SAVED_FLIGHTS = CONFIG_DIR + "stratux-radar.flights"

url_host_base = DEFAULT_URL_HOST_BASE
url_situation_ws = ""
url_radar_ws = ""
url_status_ws = ""
url_settings_set = ""
url_status_get = ""
device = ""
sound_mixer = None
g_draw = None
all_ac = {}
aircraft_changed = True
ui_changed = True
situation = {'was_changed': True, 'last_update': 0.0, 'connected': False, 'gps_active': False, 'course': 0,
             'own_altitude': -99.0, 'latitude': 0.0, 'longitude': 0.0, 'RadarRange': 5, 'RadarLimits': 10000,
             'gps_quality': 0, 'gps_h_accuracy': 20000, 'gps_speed': -100.0, 'gps_altitude': -99.0,
             'vertical_speed': 0.0, 'baro_valid': False, 'g_distance_valid': False,
             'g_distance': grounddistance.INVALID_GDISTANCE}
vertical_max = 0.0  # max value for vertical speed
vertical_min = 0.0  # min valud for vertical spee

ahrs = {'was_changed': True, 'pitch': 0, 'roll': 0, 'heading': 0, 'slipskid': 0, 'gps_hor_accuracy': 20000,
        'ahrs_sensor': False}
# ahrs information, values are all rounded to integer
gmeter = {'was_changed': True, 'current': 0.0, 'max': 0.0, 'min': 0.0}
# status information as received from stratux
global_config = {}
last_bt_checktime = 0.0

max_pixel = 0
zerox = 0
zeroy = 0
last_arcposition = 0
display_refresh_time = 0
display_control = None
basemode = False  # True if display is always in north direction
fullcircle = False  # True if epaper display should display full circle centered
bt_devices = 0
sound_on = True  # user may toogle sound off by UI
global_mode = 1
# 1=Radar 2=Timer 3=Shutdown 4=refresh from radar 5=ahrs 6=refresh from ahrs
# 7=status 8=refresh from status  9=gmeter 10=refresh from gmeter 11=compass 12=refresh from compass
# 13=VSI 14=refresh from VSI 15=dispay stratux status 16=refresh from stratux status
# 17=flighttime 18=refresh flighttime 19=cowarner 20=refresh cowarner 21=situation 22=refresh situation 0=Init
# 23=checklist 24=refresh checklist
mode_sequence = []  # list of modes to display
bluetooth = False  # True if bluetooth is enabled by parameter -b
extsound_active = False  # external sound was successfully activated, if global_config >=0
bluetooth_active = False  # bluetooth successfully activated
optical_alive = -1
measure_flighttime = False  # True if automatic measurement of flighttime is enabled
co_warner_activated = False  # True if co-warner is activated
co_indication = False  # True if indication via GPIO Pin 16 is on for co
grounddistance_activated = False  # True if measurement of grounddistance via VL53L1x is activated
groundbeep = False  # True if indication of ground distance via audio
simulation_mode = False  # if true, do simulation mode for grounddistance (for testing purposes)


def draw_all_ac(draw, allac):
    dist_sorted = sorted(allac.items(), key=lambda el: el[1]['gps_distance'], reverse=True)
    for icao, ac in dist_sorted:
        # first draw mode-s
        if 'circradius' in ac:
            if global_config['display_tail'] and 'tail' in ac:
                tail = ac['tail']
            else:
                tail = None
            if ac['circradius'] <= max_pixel / 2:
                display_control.modesaircraft(draw, ac['circradius'], ac['height'], ac['arcposition'], ac['vspeed'],
                                              tail)
    for icao, ac in dist_sorted:
        # then draw adsb
        if 'x' in ac:
            if 0 < ac['x'] <= max_pixel and ac['y'] <= max_pixel:
                if 'nspeed_length' in ac:
                    line_length = ac['nspeed_length']
                else:
                    line_length = 0
                if global_config['display_tail'] and 'tail' in ac:
                    tail = ac['tail']
                else:
                    tail = None
                display_control.aircraft(draw, ac['x'], ac['y'], ac['direction'], ac['height'], ac['vspeed'],
                                         line_length, tail)


def draw_display(draw):
    global all_ac
    global situation
    global aircraft_changed
    global ui_changed
    global optical_alive
    global extsound_active

    rlog.log(AIRCRAFT_DEBUG, "List of all aircraft > " + json.dumps(all_ac))
    new_alive = int((int(time.time()) % (OPTICAL_ALIVE_BARS * OPTICAL_ALIVE_TIME)) / OPTICAL_ALIVE_TIME)
    if situation['was_changed'] or aircraft_changed or ui_changed or new_alive != optical_alive:
        # display is only triggered if there was a change
        optical_alive = new_alive
        display_control.clear(draw)
        display_control.situation(draw, situation['connected'], situation['gps_active'], situation['own_altitude'],
                                  situation['course'], situation['RadarRange'], situation['RadarLimits'], bt_devices,
                                  sound_on, situation['gps_quality'], situation['gps_h_accuracy'], optical_alive,
                                  basemode, extsound_active, cowarner.alarm_level()[0], cowarner.alarm_level()[1])
        draw_all_ac(draw, all_ac)
        display_control.display()
        situation['was_changed'] = False
        aircraft_changed = False
        ui_changed = False


def radians_rel(angle):
    if angle > 180:
        angle = angle - 360
    if angle <= -180:
        angle = angle + 360
    return angle * math.pi / 180


def calc_gps_distance(lat, lng):
    radius_earth = 6371008.8
    avglat = radians_rel((situation['latitude'] + lat) / 2)
    distlat = (radians_rel(lat - situation['latitude']) * radius_earth) / 1852
    distlng = ((radians_rel(lng - situation['longitude']) * radius_earth) / 1852) * abs(math.cos(avglat))
    distradius = math.sqrt((distlat * distlat) + (distlng * distlng))
    if distlat < 0:
        angle = math.degrees(math.pi - math.atan(distlng / (-distlat)))
    elif distlat > 0:
        angle = math.degrees(-math.atan(distlng / (-distlat)))
    else:
        angle = 0
    return distradius, angle


def speaktraffic(hdiff, direction=None, dist=None):
    if sound_on:
        feet = hdiff * 100
        sign = 'plus'
        if hdiff < 0:
            sign = 'minus'
        txt = 'Traffic '
        if direction:
            txt += str(direction) + ' o\'clock '
        txt += sign + ' ' + str(abs(feet)) + ' feet'
        if global_config['distance_warnings'] and dist:
            txt += str(dist) + ' miles '
        radarbluez.speak(txt)


def new_traffic(json_str):
    global last_arcposition
    global aircraft_changed

    aircraft_changed = True
    rlog.log(AIRCRAFT_DEBUG, "New Traffic" + json_str)
    traffic = json.loads(json_str)
    changed = False
    try:
        if 'RadarRange' in traffic or 'RadarLimits' in traffic:
            if situation['RadarRange'] != traffic['RadarRange']:
                situation['RadarRange'] = traffic['RadarRange']
                changed = True
            if situation['RadarLimits'] != traffic['RadarLimits']:
                situation['RadarLimits'] = traffic['RadarLimits']
                changed = True
            if changed:
                # refresh all_ac
                all_ac.clear()
            return
            # ignore rest of message
        if 'Icao_addr' not in traffic:
            # steering message without aircraft content
            rlog.log(AIRCRAFT_DEBUG, "No Icao_addr in message" + json_str)
            return

        is_new = False
        if traffic['Icao_addr'] not in all_ac.keys():
            # new traffic, insert
            all_ac[traffic['Icao_addr']] = {'gps_distance': 0, 'was_spoken': False}
            is_new = True
        ac = all_ac[traffic['Icao_addr']]
        if traffic['Age'] <= traffic['AgeLastAlt']:
            ac['last_contact_timestamp'] = time.time() - traffic['Age']
        else:
            ac['last_contact_timestamp'] = time.time() - traffic['AgeLastAlt']
        ac['height'] = round((traffic['Alt'] - situation['own_altitude']) / 100)

        if traffic['Speed_valid']:
            ac['nspeed'] = traffic['Speed']
        ac['vspeed'] = traffic['Vvel']
        if traffic['Tail']:
            ac['tail'] = traffic['Tail']

        if traffic['Position_valid'] and situation['gps_active']:
            # adsb traffic and stratux has valid gps signal
            rlog.log(AIRCRAFT_DEBUG, 'RADAR: ADSB traffic ' + hex(traffic['Icao_addr'])
                     + " at height " + str(ac['height']))
            if 'circradius' in ac:
                del ac['circradius']
                # was mode-s target before, now invalidate mode-s info
            gps_rad, gps_angle = calc_gps_distance(traffic['Lat'], traffic['Lng'])
            ac['gps_distance'] = gps_rad
            if 'Track' in traffic:
                ac['direction'] = traffic['Track'] - situation['course']
                # sometimes track is missing, then leave it as it is
            if gps_rad <= situation['RadarRange'] and abs(ac['height']) <= round(situation['RadarLimits'] / 100):
                res_angle = (gps_angle - situation['course']) % 360
                gpsx = math.sin(math.radians(res_angle)) * gps_rad
                gpsy = - math.cos(math.radians(res_angle)) * gps_rad
                ac['x'] = round(max_pixel / 2 * gpsx / situation['RadarRange'] + zerox)
                ac['y'] = round(max_pixel / 2 * gpsy / situation['RadarRange'] + zeroy)
                if 'nspeed' in ac:
                    nspeed_rad = ac['nspeed'] * SPEED_ARROW_TIME / 3600  # distance in nm in that time
                    ac['nspeed_length'] = round(max_pixel / 2 * nspeed_rad / situation['RadarRange'])
                # speech output
                if gps_rad <= situation['RadarRange'] / 2:
                    oclock = round(res_angle / 30)
                    if oclock <= 0:
                        oclock += 12
                    if oclock > 12:
                        oclock -= 12
                    if not ac['was_spoken']:
                        speaktraffic(ac['height'], oclock, round(gps_rad))
                        ac['was_spoken'] = True
                else:
                    # implement hysteresis, speak traffic again if aircraft was once outside 3/4 of display radius
                    if gps_rad >= situation['RadarRange'] * 0.75:
                        ac['was_spoken'] = False
            else:
                # do not display
                ac['x'] = -1
                ac['y'] = -1

        else:
            # mode-s traffic or no valid GPS position of stratux
            # unspecified altitude, nothing displayed for now, leave it as it is
            if traffic['DistanceEstimated'] == 0 or traffic['Alt'] == 0:
                return
                # unspecified altitude, nothing displayed for now, leave it as it is
            distcirc = traffic['DistanceEstimated'] / 1852.0
            rlog.log(AIRCRAFT_DEBUG, "RADAR: Mode-S traffic " + hex(traffic['Icao_addr'])
                     + " in " + str(distcirc) + " nm")
            distx = round(max_pixel / 2 * distcirc / situation['RadarRange'])
            if is_new or 'circradius' not in ac:
                # calc argposition if new or adsb before
                last_arcposition = display_control.next_arcposition(last_arcposition)  # display specific
                ac['arcposition'] = last_arcposition
            ac['gps_distance'] = distcirc
            ac['circradius'] = distx

            if ac['gps_distance'] <= situation['RadarRange'] / 2:
                if not ac['was_spoken']:
                    speaktraffic(ac['height'], None, round(ac['gps_distance']))
                    ac['was_spoken'] = True
            else:
                # implement hysteresis, speak traffic again if aircraft was once outside 3/4 of display radius
                if ac['gps_distance'] > situation['RadarRange'] * 0.75:
                    ac['was_spoken'] = False
    except KeyError:  # to be safe in case keys are changed in Stratux
        rlog.log(AIRCRAFT_DEBUG, "KeyError decoding:" + json_str)


def update_time(time_str):  # time_str has format "2021-04-18T15:58:58.1Z"
    global last_bt_checktime

    try:
        gps_datetime = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        # stratux will deliver "0001-01-01T00:00:00Z" if not time signal is valid, this will also raise an ValueError
        # rlog.debug("Radar: ERROR converting GPS-Time: " + time_str)
        # also full seconds, will not give fractions and raise this, but it's ok
        return
    gps_datetime = gps_datetime.replace(tzinfo=timezone.utc)  # make sure that time is interpreted as utc
    if abs(time.time() - gps_datetime.timestamp()) > MAX_TIMER_OFFSET:
        # raspi system timer differs from received GPSTime
        rlog.debug("Setting Time from GPS-Time to: " + time_str + ". System time was " +
                   time.strftime("%H:%M:%S", time.gmtime()))
        res = subprocess.run(["sudo", "date", "--utc", "-s", "@" + str(gps_datetime.timestamp())])
        if res.returncode != 0:
            rlog.debug("Radar: Error setting system time")
        else:
            timerui.reset_timer()  # all timers are reset to be on the safe side!
            radarbuttons.reset_buttons()  # reset button-timers (start-time)
            last_bt_checktime = 0.0  # reset timer


def new_situation(json_str):
    global situation
    global ahrs
    global vertical_max
    global vertical_min
    global global_mode

    rlog.log(SITUATION_DEBUG, "New Situation" + json_str)
    sit = json.loads(json_str)
    try:
        situation['last_update'] = time.time()
        if not situation['connected']:
            situation['connected'] = True
            situation['was_changed'] = True
            ahrs['was_changed'] = True  # connection also relevant for ahrs
            gmeter['was_changed'] = True  # connection also relevant for ahrs
        gps_active = sit['GPSHorizontalAccuracy'] < 19999
        if situation['gps_active'] != gps_active:
            situation['gps_active'] = gps_active
            situation['was_changed'] = True
        if not basemode:
            if situation['course'] != round(sit['GPSTrueCourse']):
                situation['course'] = round(sit['GPSTrueCourse'])
                situation['was_changed'] = True
        if situation['own_altitude'] != sit['BaroPressureAltitude']:
            situation['own_altitude'] = sit['BaroPressureAltitude']
            situation['was_changed'] = True
        if situation['latitude'] != sit['GPSLatitude']:
            situation['latitude'] = sit['GPSLatitude']
            situation['was_changed'] = True
        if situation['longitude'] != sit['GPSLongitude']:
            situation['longitude'] = sit['GPSLongitude']
            situation['was_changed'] = True
        if situation['gps_quality'] != sit['GPSFixQuality']:
            situation['gps_quality'] = sit['GPSFixQuality']
            situation['was_changed'] = True
        if situation['gps_h_accuracy'] != sit['GPSHorizontalAccuracy']:
            situation['gps_h_accuracy'] = sit['GPSHorizontalAccuracy']
            situation['was_changed'] = True
        if situation['gps_speed'] != sit['GPSGroundSpeed']:
            situation['gps_speed'] = sit['GPSGroundSpeed']
            situation['was_changed'] = True
        if situation['gps_altitude'] != sit['GPSAltitudeMSL']:
            situation['gps_altitude'] = sit['GPSAltitudeMSL']
            situation['was_changed'] = True

        if sit['BaroSourceType'] == 1 or sit['BaroSourceType'] == 2 or sit['BaroSourceType'] == 3:
            # 1 = BMP280, 2 = OGN device, 3 = NMEA device
            if situation['vertical_speed'] != sit['BaroVerticalSpeed']:
                situation['vertical_speed'] = sit['BaroVerticalSpeed']
                situation['was_changed'] = True
                if situation['vertical_speed'] > vertical_max:
                    vertical_max = situation['vertical_speed']
                if situation['vertical_speed'] < vertical_min:
                    vertical_min = situation['vertical_speed']
            if not situation['baro_valid']:
                situation['baro_valid'] = True
                situation['was_changed'] = True
                vertical_max = 0  # invalidate min/max
                vertical_min = 0
        else:  # no baro (=0) or ADSB estimation (=4), not enough data for vertical speed
            if situation['baro_valid']:
                situation['baro_valid'] = False
                situation['vertical_speed'] = 0.0
                situation['was_changed'] = True
                vertical_max = 0  # invalidate min/max
                vertical_min = 0
        # set system time if not synchronized properly
        if situation['gps_active']:
            if sit['GPSLastFixLocalTime'].split('.')[0] == sit['GPSLastGPSTimeStratuxTime'].split('.')[0]:
                # take GPSTime only if last fix time and last stratux time match (in seconds),
                # sometimes a fix is there, but
                # not yet an update time value from GPS, but the old one is transmitted by stratux
                update_time(sit['GPSTime'])
        # ahrs
        if ahrs['pitch'] != round(sit['AHRSPitch']):
            ahrs['pitch'] = round(sit['AHRSPitch'])
            ahrs['was_changed'] = True
        if ahrs['roll'] != round(sit['AHRSRoll']):
            ahrs['roll'] = round(sit['AHRSRoll'])
            ahrs['was_changed'] = True
        if ahrs['heading'] != round(sit['AHRSGyroHeading']):
            ahrs['heading'] = round(sit['AHRSGyroHeading'])
            ahrs['was_changed'] = True
        if ahrs['slipskid'] != round(sit['AHRSSlipSkid']):
            ahrs['slipskid'] = round(sit['AHRSSlipSkid'])
            ahrs['was_changed'] = True
        if ahrs['gps_hor_accuracy'] != round(sit['GPSHorizontalAccuracy']):
            ahrs['gps_hor_accuracy'] = round(sit['GPSHorizontalAccuracy'])
            ahrs['was_changed'] = True
        if sit['AHRSStatus'] & 0x02:
            ahrs_flag = True
        else:
            ahrs_flag = False
        if ahrs['ahrs_sensor'] != ahrs_flag:
            ahrs['ahrs_sensor'] = ahrs_flag
            ahrs['was_changed'] = True

        current = round(sit['AHRSGLoad'], 2)
        if gmeter['current'] != current:
            gmeter['current'] = current
            gmeter['was_changed'] = True
        maxv = round(sit['AHRSGLoadMax'], 2)
        if gmeter['max'] != maxv:
            gmeter['max'] = maxv
            gmeter['was_changed'] = True
        minv = round(sit['AHRSGLoadMin'], 2)
        if gmeter['min'] != minv:
            gmeter['min'] = minv
            gmeter['was_changed'] = True

        if simulation_mode:
            sim_data = simulation.read_simulation_data()
            if sim_data is not None:
                if 'gps_speed' in sim_data:
                    situation['gps_speed'] = sim_data['gps_speed']
                if 'own_altitude' in sim_data:
                    situation['own_altitude'] = sim_data['own_altitude']

        # automatic time measurement
        new_mode = flighttime.trigger_measurement(gps_active, situation, ahrs, global_mode)
        if new_mode > 0:
            global_mode = new_mode  # automatically change to display of flight times, or back

    except KeyError:  # to be safe when stratux changes its message-format
        rlog.log(SITUATION_DEBUG, "KeyError decoding situation:" + json_str)


async def listen_forever(path, name, callback, logger):
    logger.debug(name + " waiting for " + path)
    while True:
        # outer loop restarted every time the connection fails
        logger.debug(name + " active ...")
        try:
            async with websockets.connect(path, ping_timeout=None, ping_interval=None, close_timeout=2) as ws:
                # stratux does not respond to pings! close timeout set down to get earlier disconnect
                logger.debug(name + " connected on " + path)
                while True:
                    # listener loop
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=CHECK_CONNECTION_TIMEOUT)
                        # message = await ws.recv()
                    except asyncio.TimeoutError:
                        # No situation received or traffic in CHECK_CONNECTION_TIMEOUT seconds, retry to connect
                        # rlog.debug(name + ': TimeOut received waiting for message.')
                        if situation['connected'] is False:  # Probably connection lost
                            logger.debug(name + ': Watchdog detected connection loss.' +
                                         ' Retrying connect in {} sec '.format(LOST_CONNECTION_TIMEOUT))
                            await asyncio.sleep(LOST_CONNECTION_TIMEOUT)
                            break
                    except websockets.exceptions.ConnectionClosed:
                        logger.debug(
                            name + ' ConnectionClosed. Retrying connect in {} sec '.format(LOST_CONNECTION_TIMEOUT))
                        await asyncio.sleep(LOST_CONNECTION_TIMEOUT)
                        break
                    except asyncio.CancelledError:
                        logger.debug(name + " shutting down ... ")
                        return
                    else:
                        callback(message)
                    await asyncio.sleep(MINIMAL_WAIT_TIME)  # do a minimal wait to let others do their jobs

        except (socket.error, websockets.exceptions.WebSocketException, asyncio.TimeoutError):
            logger.debug(name + ' WebSocketException. Retrying connection in {} sec '.format(RETRY_TIMEOUT))
            if name == 'SituationHandler' and situation['connected']:
                situation['connected'] = False
                ahrs['was_changed'] = True
                situation['was_changed'] = True
                gmeter['was_changed'] = True
            await asyncio.sleep(RETRY_TIMEOUT)
            continue
        except asyncio.CancelledError:
            logger.debug(name + " shutting down in connect ... ")
            return


async def user_interface():
    global bt_devices
    global sound_on
    global ui_changed
    global global_mode
    global vertical_max
    global vertical_min
    global last_bt_checktime

    next_mode = 1

    try:
        while True:
            await asyncio.sleep(UI_REACTION_TIME)
            if global_mode == 1:  # Radar mode
                next_mode, toggle_sound = radarui.user_input(situation['RadarRange'], situation['RadarLimits'])
                if toggle_sound:
                    sound_on = not sound_on
                    if sound_on:
                        radarbluez.speak("Radar sound on")
                    else:
                        radarbluez.speak("Radar sound off")
                    ui_changed = True
            elif global_mode == 2:  # Timer mode
                next_mode = timerui.user_input()
            elif global_mode == 3:  # shutdown mode
                next_mode = shutdownui.user_input()
            elif global_mode == 5:  # ahrs
                next_mode = ahrsui.user_input()
            elif global_mode == 7:  # status
                next_mode = statusui.user_input(extsound_active, bluetooth_active)
            elif global_mode == 9:  # gmeter
                next_mode = gmeterui.user_input()
            elif global_mode == 11:  # compass
                next_mode = compassui.user_input()
            elif global_mode == 13:  # vertical speed indicator
                next_mode, reset_vsi = verticalspeed.user_input()
                if reset_vsi:
                    vertical_max = 0.0
                    vertical_min = 0.0
            elif global_mode == 15:  # stratux status
                stratuxstatus.start()  # starts status_listener couroutine if not yet running
                next_mode = stratuxstatus.user_input()
                if next_mode != 0 and next_mode != 15:
                    stratuxstatus.stop()  # stops status_listener
            elif global_mode == 17:  # display flighttimes
                next_mode = flighttime.user_input()
            elif global_mode == 19:  # co warner
                next_mode = cowarner.user_input()
            elif global_mode == 21:  # ground distance
                next_mode, reset_situation = distance.user_input()
                if reset_situation:
                    distance.reset_values(situation)
            if next_mode > 0:
                ui_changed = True
                rlog.debug("User Interface: global mode changing from: " + str(global_mode) + " to " + str(next_mode))
                global_mode = next_mode

            current_time = time.time()
            if bluetooth_active and current_time > last_bt_checktime + BLUEZ_CHECK_TIME:
                last_bt_checktime = current_time
                new_devices, devnames = radarbluez.connected_devices()
                if new_devices > 0:
                    rlog.debug("User Interface: Bluetooth " + str(new_devices) + " devices connected.")
                if new_devices != bt_devices:
                    if new_devices > bt_devices:  # new or additional device
                        radarbluez.speak("Radar connected")
                    bt_devices = new_devices
                    ui_changed = True
    except asyncio.CancelledError:
        rlog.debug("UI task terminating ...")
        radarbuttons.cleanup()


async def display_and_cutoff():
    global aircraft_changed
    global global_mode
    global display_control
    global ui_changed
    global situation

    try:
        while True:
            await asyncio.sleep(MIN_DISPLAY_REFRESH_TIME)
            if display_control.is_busy():
                await asyncio.sleep(display_refresh_time / 3)
                # try it several times to be as fast as possible
            else:
                if global_mode == 1:  # Radar
                    draw_display(g_draw)
                elif global_mode == 2:  # Timer'
                    timerui.draw_timer(g_draw, display_control, display_refresh_time)
                elif global_mode == 3:  # shutdown
                    final_shutdown = shutdownui.draw_shutdown(g_draw, display_control)
                    if final_shutdown:
                        rlog.debug("Shutdown triggered: Display task terminating ...")
                        return
                elif global_mode == 4:  # refresh display, only relevant for epaper, mode was radar
                    rlog.debug("Radar: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 1
                elif global_mode == 5:  # ahrs'
                    ahrsui.draw_ahrs(g_draw, display_control, situation['connected'], ui_changed or ahrs['was_changed'],
                                     ahrs['pitch'], ahrs['roll'], ahrs['heading'], ahrs['slipskid'],
                                     ahrs['gps_hor_accuracy'], ahrs['ahrs_sensor'])
                    ahrs['was_changed'] = False
                    ui_changed = False
                elif global_mode == 6:  # refresh display, only relevant for epaper, mode was radar
                    rlog.debug("AHRS: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 5
                elif global_mode == 7:  # status display
                    statusui.draw_status(g_draw, display_control, bluetooth_active, extsound_active)
                elif global_mode == 8:  # refresh display, only relevant for epaper, mode was status
                    rlog.debug("Status: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 7
                elif global_mode == 9:  # gmeter display
                    gmeterui.draw_gmeter(g_draw, display_control, ui_changed, situation['connected'], gmeter)
                    gmeter['was_changed'] = False
                    ui_changed = False
                elif global_mode == 10:  # refresh display, only relevant for epaper, mode was gmeter
                    rlog.debug("Gmeter: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 9
                elif global_mode == 11:  # compass display
                    compassui.draw_compass(g_draw, display_control, situation['was_changed'], situation['connected'],
                                           situation['course'])
                    situation['was_changed'] = False
                elif global_mode == 12:  # refresh display, only relevant for epaper, mode was gmeter
                    rlog.debug("Compass: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 11
                elif global_mode == 13:  # vsi display
                    verticalspeed.draw_vsi(g_draw, display_control, situation['was_changed'] or ui_changed,
                                           situation['connected'], situation['vertical_speed'],
                                           situation['own_altitude'], situation['gps_speed'],
                                           situation['course'], situation['gps_altitude'], vertical_max, vertical_min,
                                           situation['gps_active'],
                                           situation['baro_valid'])
                    situation['was_changed'] = False
                    ui_changed = False
                elif global_mode == 14:  # refresh display, only relevant for epaper, mode was gmeter
                    rlog.debug("VSI: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 13
                elif global_mode == 15:  # stratux_statux display
                    stratuxstatus.draw_status(g_draw, display_control, ui_changed, situation['connected'],
                                              situation['own_altitude'], situation['gps_altitude'],
                                              situation['gps_quality'])
                    ui_changed = False
                elif global_mode == 16:  # refresh display, only relevant for epaper, mode was stratux_status
                    rlog.debug("StratusStatus: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 15
                elif global_mode == 17:  # display flight time
                    flighttime.draw_flighttime(g_draw, display_control, ui_changed)
                    ui_changed = False
                elif global_mode == 18:  # refresh display, only relevant for epaper, mode was flighttime
                    rlog.debug("StratusStatus: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 17
                elif global_mode == 19:  # co-warner
                    cowarner.draw_cowarner(g_draw, display_control, ui_changed)
                    ui_changed = False
                elif global_mode == 20:  # refresh display, only relevant for epaper, mode was co-warner
                    rlog.debug("CO-Warner: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 19
                elif global_mode == 21:  # situation
                    distance.draw_distance(g_draw, display_control, situation['was_changed'] or ui_changed,
                                           situation['connected'], situation, ahrs)
                    ui_changed = False
                elif global_mode == 22:  # refresh display, only relevant for epaper, mode was situation
                    rlog.debug("Situation: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 21
                elif global_mode == 23:  # checklist
                    checklist.draw_checklist(g_draw, display_control, situation['was_changed'] or ui_changed)
                    ui_changed = False
                elif global_mode == 24:  # refresh display, only relevant for epaper, mode was situation
                    rlog.debug("Checklist: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 23

            to_delete = []
            cutoff = time.time() - RADAR_CUTOFF
            for icao, ac in all_ac.items():
                if ac['last_contact_timestamp'] < cutoff:
                    rlog.log(AIRCRAFT_DEBUG, "Cutting of " + hex(icao))
                    to_delete.append(icao)
                    aircraft_changed = True
            for i in to_delete:
                del all_ac[i]

            # watchdog
            if situation['last_update'] + WATCHDOG_TIMER < time.time():
                if situation['connected']:
                    situation['connected'] = False
                    situation['was_changed'] = True
                    ahrs['was_changed'] = True
                    gmeter['was_changed'] = True
                    rlog.debug("WATCHDOG: No situation update received in " + str(WATCHDOG_TIMER) + " seconds")
    except (asyncio.CancelledError, RuntimeError):
        rlog.debug("Display task terminating ...")


async def coroutines():
    tr_handler = asyncio.create_task(listen_forever(url_radar_ws, "TrafficHandler", new_traffic, rlog))
    sit_handler = asyncio.create_task(listen_forever(url_situation_ws, "SituationHandler", new_situation, rlog))
    dis_cutoff = asyncio.create_task(display_and_cutoff())
    sensor_reader = asyncio.create_task(cowarner.read_sensors())
    ground_sensor_reader = asyncio.create_task(grounddistance.read_ground_sensor())
    u_interface = asyncio.create_task(user_interface())
    await asyncio.wait([tr_handler, sit_handler, dis_cutoff, u_interface, sensor_reader, ground_sensor_reader])


def main():
    global max_pixel
    global zerox
    global zeroy
    global g_draw
    global display_refresh_time
    global extsound_active
    global bluetooth_active

    print("Stratux Radar Display " + RADAR_VERSION + " running ...")
    radarui.init(url_settings_set)
    shutdownui.init(url_shutdown, url_reboot)
    timerui.init(global_config)
    extsound_active, bluetooth_active = radarbluez.sound_init(global_config, bluetooth, sound_mixer)
    g_draw, max_pixel, zerox, zeroy, display_refresh_time = display_control.init(fullcircle)
    ahrsui.init(display_control)
    statusui.init(display_control, CONFIG_FILE, url_status_get, url_host_base, display_refresh_time, global_config)
    gmeterui.init(url_gmeter_reset)
    stratuxstatus.init(display_control, url_status_ws)
    flighttime.init(measure_flighttime, SAVED_FLIGHTS)
    cowarner.init(co_warner_activated, global_config, SITUATION_DEBUG, co_indication)
    grounddistance.init(grounddistance_activated, SITUATION_DEBUG, groundbeep, situation, simulation_mode)
    simulation.init(simulation_mode)
    checklist.init(excel_checklist)
    display_control.startup(g_draw, RADAR_VERSION, url_host_base, 4)
    try:
        asyncio.run(coroutines())
    except asyncio.CancelledError:
        rlog.debug("Main cancelled")


def quit_gracefully(*args):
    print("Keyboard interrupt or shutdown. Quitting ...")
    tasks = asyncio.all_tasks()
    for ta in tasks:
        ta.cancel()
    rlog.debug("CleanUp Display ...")
    display_control.cleanup()
    return 0


def logging_init():
    # Add file rotatin handler, with level DEBUG
    # rotatingHandler = logging.handlers.RotatingFileHandler(filename='rotating.log', maxBytes=1000, backupCount=5)
    # rotatingHandler.setLevel(logging.DEBUG)
    global rlog

    logging.basicConfig(level=logging.INFO, format='%(asctime)-15s > %(message)s')
    rlog = logging.getLogger('stratux-radar-log')
    logging.addLevelName(SITUATION_DEBUG, 'SITUATION_DEBUG')
    logging.addLevelName(AIRCRAFT_DEBUG, 'AIRCRAFT_DEBUG')


if __name__ == "__main__":
    # parse arguments for different configurations
    ap = argparse.ArgumentParser(description='Stratux radar display')
    ap.add_argument("-d", "--device", required=True, help="Display device to use")
    ap.add_argument("-b", "--bluetooth", required=False, help="Bluetooth speech warnings on", action='store_true',
                    default=False)
    ap.add_argument("-sd", "--speakdistance", required=False, help="Speech with distance", action='store_true',
                    default=False)
    ap.add_argument("-n", "--north", required=False, help="Ground mode: always display north up", action='store_true',
                    default=False)
    ap.add_argument("-t", "--timer", required=False, help="Start mode is timer", action='store_true', default=False)
    ap.add_argument("-a", "--ahrs", required=False, help="Start mode is ahrs", action='store_true', default=False)
    ap.add_argument("-x", "--status", required=False, help="Start mode is status", action='store_true', default=False)
    ap.add_argument("-g", "--gmeter", required=False, help="Start mode is g-meter", action='store_true', default=False)
    ap.add_argument("-o", "--compass", required=False, help="Start mode is compass", action='store_true', default=False)
    ap.add_argument("-i", "--vsi", required=False, help="Start mode is vertical speed indicator", action='store_true',
                    default=False)
    ap.add_argument("-z", "--strx", required=False, help="Start mode is stratux-status", action='store_true',
                    default=False)
    ap.add_argument("-w", "--cowarner", required=False, help="Start mode is CO warner", action='store_true',
                    default=False)
    ap.add_argument("-sit", "--situation", required=False, help="Start mode situation display", action='store_true',
                    default=False)
    ap.add_argument("-chl", "--checklist", required=False, help="Start mode checklist display", action='store_true',
                    default=DEFAULT_CHECKLIST)
    ap.add_argument("-c", "--connect", required=False, help="Connect to Stratux-IP", default=DEFAULT_URL_HOST_BASE)
    ap.add_argument("-v", "--verbose", type=int, required=False, help="Debug output level [0-3]",
                    default=0)
    ap.add_argument("-r", "--registration", required=False, help="Display registration no (epaper only)",
                    action="store_true", default=False)
    ap.add_argument("-e", "--fullcircle", required=False, help="Display full circle radar (3.7 epaper only)",
                    action="store_true", default=False)
    ap.add_argument("-y", "--extsound", type=int, required=False, help="Ext sound on with volume [0-100]",
                    default=0)
    ap.add_argument("-nf", "--noflighttime", required=False, help="Suppress detection and display of flighttime",
                    action="store_true", default=False)
    ap.add_argument("-nc", "--nocowarner", required=False, help="Suppress activation of co-warner",
                    action="store_true", default=False)
    ap.add_argument("-ci", "--coindicate", required=False, help="Indicate co warning via GPIO16",
                    action="store_true", default=False)
    ap.add_argument("-gd", "--grounddistance", required=False, help="Activate ground distance sensor",
                    action="store_true", default=False)
    ap.add_argument("-gb", "--groundbeep", required=False, help="Indicate ground distance via sound",
                    action="store_true", default=False)
    ap.add_argument("-sim", "--simulation", required=False, help="Simulation mode for testing",
                    action="store_true", default=False)
    ap.add_argument("-mx", "--mixer", required=False, help="Mixer name to be used for sound output",
                    default=DEFAULT_MIXER)
    ap.add_argument("-modes", "--displaymodes", required=False, help="Select display modes that you want to see "
        "R=radar T=timer A=ahrs D=display-status G=g-meter K=compass V=vsi I=flighttime S=stratux-status C=co-sensor "    
        "M=distance measurement L=checklist  Example: -modes RADCM", default="RTAGKVILCMDS")

    args = vars(ap.parse_args())
    # set up logging
    logging_init()
    if args['verbose'] == 0:
        rlog.setLevel(logging.INFO)
    elif args['verbose'] == 1:
        rlog.setLevel(logging.DEBUG)  # log events without situation and aircraft
    elif args['verbose'] == 2:
        rlog.setLevel(AIRCRAFT_DEBUG)  # log including aircraft
    else:
        rlog.setLevel(SITUATION_DEBUG)  # log including situation messages

    url_host_base = args['connect']
    display_control = importlib.import_module('displays.' + args['device'] + '.controller')
    bluetooth = args['bluetooth']
    basemode = args['north']
    fullcircle = args['fullcircle']
    measure_flighttime = not args['noflighttime']
    co_warner_activated = not args['nocowarner']
    co_indication = args['coindicate']
    grounddistance_activated = args['grounddistance']
    groundbeep = args['groundbeep']
    simulation_mode = args['simulation']
    excel_checklist = args['checklist']
    if args['timer']:
        global_mode = 2  # start_in_timer_mode
    if args['ahrs']:
        global_mode = 5  # start_in_ahrs mode
    if args['status']:
        global_mode = 7  # start in status mode
    if args['gmeter']:
        global_mode = 9  # start in g-meter mode
    if args['compass']:
        global_mode = 11  # start in compass mode
    if args['vsi']:
        global_mode = 13  # start in vsi mode
    if args['strx']:
        global_mode = 15  # start in stratux-status
    if args['cowarner']:
        global_mode = 19  # start in co-warner mode
    if args['situation']:
        global_mode = 21  # start in situation
    if args['checklist']:
        global_mode = 23  # start in checklist
    sound_mixer = args['mixer']
    radarmodes.parse_modes(args['displaymodes'])
    if global_mode == 1:  # no mode override set, take first mode in mode_sequence
        global_mode = radarmodes.first_mode_sequence()
    global_config['display_tail'] = args['registration']  # display registration if set
    global_config['distance_warnings'] = args['speakdistance']  # display registration if set
    global_config['sound_volume'] = args['extsound']  # 0 if not enabled
    if global_config['sound_volume'] < 0 or global_config['sound_volume'] > 100:
        global_config['sound_volume'] = 50  # set to a medium value if strange number used
    # check config file, if extistent use config from there
    url_host_base = args['connect']
    saved_config = statusui.read_config(CONFIG_FILE)
    if saved_config is not None:
        if 'stratux_ip' in saved_config:
            url_host_base = saved_config['stratux_ip']  # set stratux ip if interactively changed one time
        if 'display_tail' in saved_config:
            global_config['display_tail'] = saved_config['display_tail']
        if 'distance_warnings' in saved_config:
            global_config['distance_warnings'] = saved_config['distance_warnings']
        if 'sound_volume' in saved_config:
            global_config['sound_volume'] = saved_config['sound_volume']
        if 'CO_warner_R0' in saved_config:
            global_config['CO_warner_R0'] = saved_config['CO_warner_R0']
    url_situation_ws = "ws://" + url_host_base + "/situation"
    url_radar_ws = "ws://" + url_host_base + "/radar"
    url_status_ws = "ws://" + url_host_base + "/status"
    url_shutdown = "http://" + url_host_base + "/shutdown"
    url_reboot = "http://" + url_host_base + "/reboot"
    url_settings_set = "http://" + url_host_base + "/setSettings"
    url_gmeter_reset = "http://" + url_host_base + "/resetGMeter"
    url_status_get = "http://" + url_host_base + "/getStatus"

    try:
        signal.signal(signal.SIGINT, quit_gracefully)  # to be able to receive sigint
        signal.signal(signal.SIGTERM, quit_gracefully)  # shutdown initiated e.g. by stratux shutdown
        main()
    except KeyboardInterrupt:
        pass
