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

from espeakng import ESpeakNG
import importlib

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)-15s > %(message)s'
)

# constant definitions
RETRY_TIMEOUT = 1
LOST_CONNECTION_TIMEOUT = 1.0
RADAR_CUTOFF = 29
ARCPOSITION_EXCLUDE_FROM = 130
ARCPOSITION_EXCLUDE_TO = 230

# global variables
DEFAULT_URL_HOST_BASE = "192.168.10.1"
url_situation_ws = ""
url_radar_ws = ""
device = ""
draw = None
all_ac = {}
aircraft_changed = True
situation = {'was_changed': True, 'connected': False, 'gps_active': False, 'course': 0, 'own_altitude': -99.0,
             'latitude': 0.0, 'longitude': 0.0, 'RadarRange': 5, 'RadarLimits': 10000}
max_pixel = 0
zerox = 0
zeroy = 0
last_arcposition = 0
display_refresh_time = 0
quit_display_task = False
esng = None
display_control = None
speak = False


def init_espeak():
    global esng
    if speak:
        esng = ESpeakNG(voice='en-us', pitch=30, speed=175)
        if esng:
            esng.say("Stratux Radar connected")
            print("SPEAK: Stratux Radar connected")


def draw_all_ac(draw, allac):
    # print("List aircraft" + json.dumps(allac))
    dist_sorted = sorted(allac.items(), key=lambda el: el[1]['gps_distance'], reverse=True)
    # print("dist_sorted" + json.dumps(dist_sorted))
    for icao, ac in dist_sorted:
        # first draw mode-s
        if 'circradius' in ac:
            if ac['circradius'] <= max_pixel / 2:
                display_control.modesaircraft(draw, ac['circradius'], ac['height'], ac['arcposition'])
    for icao, ac in dist_sorted:
        # then draw adsb
        if 'x' in ac:
            if 0 < ac['x'] <= max_pixel and ac['y'] <= max_pixel:
                display_control.aircraft(draw, ac['x'], ac['y'], ac['direction'], ac['height'])


def draw_display(draw):
    global all_ac
    global situation
    global aircraft_changed

    logging.debug("List of all aircraft > " + json.dumps(all_ac))
    if situation['was_changed'] or aircraft_changed:
        # display is only triggered if there was a change
        display_control.clear(draw)
        display_control.situation(draw, situation['connected'], situation['gps_active'], situation['own_altitude'],
                                  situation['course'], situation['RadarRange'], situation['RadarLimits'])
        draw_all_ac(draw, all_ac)
        display_control.display()
        situation['was_changed'] = False
        aircraft_changed = False


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


def speaktraffic(hdiff, direction=None):
    global esng
    global speak

    feet = hdiff * 100
    sign = 'plus'
    if hdiff < 0:
        sign = 'minus'
    txt = 'Traffic '
    if direction:
        txt += str(direction) + ' o\'clock '
    txt += sign + ' ' + str(abs(feet)) + ' feet'
    print("SPEAK: " + txt)
    if speak:
        esng.say(txt)


def new_traffic(json_str):
    global last_arcposition
    global aircraft_changed

    aircraft_changed = True
    logging.debug("New Traffic" + json_str)
    traffic = json.loads(json_str)
    changed = False
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
        logging.debug("No Icao_addr in message" + json_str)
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

    if traffic['Position_valid'] and situation['gps_active']:
        # adsb traffic and stratux has valid gps signal
        logging.debug('RADAR: ADSB traffic ' + hex(traffic['Icao_addr']) + " at height " + str(ac['height']))
        if 'circradius' in ac:
            del ac['circradius']
            # was mode-s target before, now invalidate mode-s info
        gps_rad, gps_angle = calc_gps_distance(traffic['Lat'], traffic['Lng'])
        ac['gps_distance'] = gps_rad
        if 'Track' in traffic:
            ac['direction'] = traffic['Track'] - situation['course']
            # sometimes track is missing, than leave it as it is
        if gps_rad <= situation['RadarRange'] and abs(ac['height']) <= situation['RadarLimits']:
            res_angle = gps_angle - situation['course']
            gpsx = math.sin(math.radians(res_angle)) * gps_rad
            gpsy = - math.cos(math.radians(res_angle)) * gps_rad
            ac['x'] = round(max_pixel / 2 * gpsx / situation['RadarRange'] + zerox)
            ac['y'] = round(max_pixel / 2 * gpsy / situation['RadarRange'] + zeroy)
            # speech output
            if gps_rad <= situation['RadarRange'] / 2:
                oclock = round(res_angle / 30)
                if oclock <= 0:
                    oclock += 12
                if oclock > 12:
                    oclock -= 12
                if not ac['was_spoken']:
                    speaktraffic(ac['height'], oclock)
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
        logging.debug("Mode-S Traffic " + hex(traffic['Icao_addr']) + " in " + str(distcirc) + " nm")
        distx = round(max_pixel / 2 * distcirc / situation['RadarRange'])
        if is_new or 'circradius' not in ac:
            # calc argposition if new or adsb before
            last_arcposition = (last_arcposition + 210) % 360
            if ARCPOSITION_EXCLUDE_TO >= last_arcposition >= ARCPOSITION_EXCLUDE_FROM:
                last_arcposition = (last_arcposition + 210) % 360
            ac['arcposition'] = last_arcposition
        ac['gps_distance'] = distcirc
        ac['circradius'] = distx

        if ac['gps_distance'] <= situation['RadarRange'] / 2:
            if not ac['was_spoken']:
                speaktraffic(ac['height'])
                ac['was_spoken'] = True
        else:
            # implement hysteresis, speak traffic again if aircraft was once outside 3/4 of display radius
            if ac['gps_distance'] > situation['RadarRange'] * 0.75:
                ac['was_spoken'] = False


def new_situation(json_str):
    global situation
    logging.debug("New Situation" + json_str)
    sit = json.loads(json_str)
    if not situation['connected']:
        situation['connected'] = True
        situation['was_changed'] = True
    gps_active = sit['GPSHorizontalAccuracy'] < 19999
    if situation['gps_active'] != gps_active:
        situation['gps_active'] = gps_active
        situation['was_changed'] = True
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


async def listen_forever(path, name, callback):
    print(name + " waiting for " + path)
    while True:
        # outer loop restarted every time the connection fails
        logging.debug(name + " active ...")
        try:
            async with websockets.connect(path) as ws:
                logging.debug(name + " connected on " + path)
                while True:
                    # listener loop
                    try:
                        message = await ws.recv()
                    except websockets.exceptions.ConnectionClosed:
                        logging.debug(name + ' ConnectionClosed. Retrying connect in {} sec '.format(LOST_CONNECTION_TIMEOUT))
                        await asyncio.sleep(LOST_CONNECTION_TIMEOUT)
                        break
                    except asyncio.CancelledError:
                        print(name + " shutting down ... ")
                        return

                    callback(message)

        except (socket.error, websockets.exceptions.WebSocketException):
            logging.debug(name + ' WebSocketException. Retrying connection in {} sec '.format(RETRY_TIMEOUT))
            if name == 'SituationHandler' and situation['connected']:
                    situation['connected'] = False
                    situation['was_changed'] = True
            await asyncio.sleep(RETRY_TIMEOUT)
            continue


async def display_and_cutoff():
    global aircraft_changed

    while True:
        if quit_display_task:
            print("Display task terminating ...")
            return

        if display_control.is_busy():
            await asyncio.sleep(display_refresh_time / 3)
            # try it several times to be as fast as possible
        else:
            draw_display(draw)
            # wait 300 ms in any case to make sure driver is ready for busy flag
            await asyncio.sleep(0.3)

        logging.debug("CutOff running and cleaning ac with age older than " + str(RADAR_CUTOFF) + " seconds")
        to_delete = []
        cutoff = time.time() - RADAR_CUTOFF
        for icao, ac in all_ac.items():
            if ac['last_contact_timestamp'] < cutoff:
                logging.debug("Cutting of " + str(icao))
                to_delete.append(icao)
                aircraft_changed = True
        for i in to_delete:
            del all_ac[i]


async def courotines():
    await asyncio.wait([listen_forever(url_radar_ws, "TrafficHandler", new_traffic),
                        listen_forever(url_situation_ws, "SituationHandler", new_situation), display_and_cutoff()])


def main():
    global max_pixel
    global zerox
    global zeroy
    global draw
    global display_refresh_time

    init_espeak()
    draw, max_pixel, zerox, zeroy, display_refresh_time = display_control.init()
    display_control.startup(draw, url_host_base, 4)
    try:
        asyncio.run(courotines())
    except asyncio.CancelledError:
        logging.debug("Main cancelled")


def quit_gracefully(*args):
    global quit_display_task

    print("Keyboard interrupt. Quitting ...")
    quit_display_task = True
    tasks = asyncio.all_tasks()
    for ta in tasks:
        ta.cancel()
    print("CleanUp Epaper ...")
    display_control.cleanup()


if __name__ == "__main__":
    # parse arguments for different configurations
    ap = argparse.ArgumentParser(description='Stratux web radar for separate displays')
    ap.add_argument("-d", "--device", required=True, help="Display device to use")
    ap.add_argument("-s", "--speak", required=False, help="Speech warnings on", action='store_true', default=False)
    ap.add_argument("-c", "--connect", required=False, help="Connect to Stratux-IP", default=DEFAULT_URL_HOST_BASE)
    args = vars(ap.parse_args())
    display_control = importlib.import_module('displays.' + args['device'] + '.controller')
    speak = args['speak']
    url_host_base = args['connect']
    url_situation_ws = "ws://" + url_host_base + "/situation"
    url_radar_ws = "ws://" + url_host_base + "/radar"
    try:
        signal.signal(signal.SIGINT, quit_gracefully)  # to be able to receive sigint
        main()
    except KeyboardInterrupt:
        pass
