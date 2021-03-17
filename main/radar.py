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
import importlib

# constant definitions
RADAR_VERSION = "1.0f"

RETRY_TIMEOUT = 1
LOST_CONNECTION_TIMEOUT = 0.3
RADAR_CUTOFF = 29
UI_REACTION_TIME = 0.1
MINIMAL_WAIT_TIME = 0.01   # give other coroutines some time to to their jobs
BLUEZ_CHECK_TIME = 3.0
SPEED_ARROW_TIME = 60  # time in seconds for the line that displays the speed
WATCHDOG_TIMER = 3.0   # time after "no connection" is assumed, if no new situation is received
CHECK_CONNECTION_TIMEOUT = 5.0
# timeout used for regular status request, necessary towards stratux to keep the websockets open
MIN_DISPLAY_REFRESH_TIME = 0.1
# minimal time to wait for a display refresh, to give time for situation and traffic

# global variables
DEFAULT_URL_HOST_BASE = "192.168.10.1"
url_host_base = DEFAULT_URL_HOST_BASE
url_situation_ws = ""
url_radar_ws = ""
url_settings_set = ""
url_status_get = ""
device = ""
draw = None
all_ac = {}
aircraft_changed = True
ui_changed = True
situation = {'was_changed': True, 'last_update': 0.0,  'connected': False, 'gps_active': False, 'course': 0,
             'own_altitude': -99.0, 'latitude': 0.0, 'longitude': 0.0, 'RadarRange': 5, 'RadarLimits': 10000,
             'gps_quality': 0, 'gps_h_accuracy': 20000}
ahrs = {'was_changed': True, 'pitch': 0, 'roll': 0, 'heading': 0, 'slipskid': 0, 'gps_hor_accuracy': 20000,
        'ahrs_sensor': False}
gmeter = {'was_changed': True, 'current:': 0.0, 'max': 0.0, 'min': 0.0}
# ahrs information, values are all rounded to integer
global_config = {}

max_pixel = 0
zerox = 0
zeroy = 0
last_arcposition = 0
display_refresh_time = 0
display_control = None
speak = False  # BT is generally enabled
bt_devices = 0
sound_on = True  # user may toogle sound off by UI
global_mode = 1
# 1=Radar 2=Timer 3=Shutdown 4=refresh from radar 5=ahrs 6=refresh from ahrs
# 7=status 8=refresh from status  9=gmeter 10=refresh from gmeter 0=Init
bluetooth_active = False


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

    logging.debug("List of all aircraft > " + json.dumps(all_ac))
    if situation['was_changed'] or aircraft_changed or ui_changed:
        # display is only triggered if there was a change
        display_control.clear(draw)
        display_control.situation(draw, situation['connected'], situation['gps_active'], situation['own_altitude'],
                                  situation['course'], situation['RadarRange'], situation['RadarLimits'], bt_devices,
                                  sound_on, situation['gps_quality'], situation['gps_h_accuracy'])
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


def speaktraffic(hdiff, direction=None):
    if sound_on:
        feet = hdiff * 100
        sign = 'plus'
        if hdiff < 0:
            sign = 'minus'
        txt = 'Traffic '
        if direction:
            txt += str(direction) + ' o\'clock '
        txt += sign + ' ' + str(abs(feet)) + ' feet'
        radarbluez.speak(txt)


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

    if traffic['Speed_valid']:
        ac['nspeed'] = traffic['Speed']
    ac['vspeed'] = traffic['Vvel']
    if traffic['Tail']:
        ac['tail'] = traffic['Tail']

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
        logging.debug("RADAR: Mode-S traffic " + hex(traffic['Icao_addr']) + " in " + str(distcirc) + " nm")
        distx = round(max_pixel / 2 * distcirc / situation['RadarRange'])
        if is_new or 'circradius' not in ac:
            # calc argposition if new or adsb before
            last_arcposition = display_control.next_arcposition(last_arcposition)   # display specific
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
    global ahrs

    logging.debug("New Situation" + json_str)
    sit = json.loads(json_str)
    situation['last_update'] = time.time()
    if not situation['connected']:
        situation['connected'] = True
        situation['was_changed'] = True
        ahrs['was_changed'] = True   # connection also relevant for ahrs
        gmeter['was_changed'] = True  # connection also relevant for ahrs
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
    if situation['gps_quality'] != sit['GPSFixQuality']:
        situation['gps_quality'] = sit['GPSFixQuality']
        situation['was_changed'] = True
    if situation['gps_h_accuracy'] != sit['GPSHorizontalAccuracy']:
        situation['gps_h_accuracy'] = sit['GPSHorizontalAccuracy']
        situation['was_changed'] = True

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
    max = round(sit['AHRSGLoadMax'], 2)
    if gmeter['max'] != max:
        gmeter['max'] = max
        gmeter['was_changed'] = True
    min = round(sit['AHRSGLoadMin'], 2)
    if gmeter['min'] != min:
        gmeter['min'] = min
        gmeter['was_changed'] = True


async def listen_forever(path, name, callback):
    print(name + " waiting for " + path)
    while True:
        # outer loop restarted every time the connection fails
        logging.debug(name + " active ...")
        try:
            async with websockets.connect(path, ping_timeout=None, ping_interval=None, close_timeout=2) as ws:
                # stratux does not respond to pings! close timeout set down to get earlier disconnect
                logging.debug(name + " connected on " + path)
                while True:
                    # listener loop
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=CHECK_CONNECTION_TIMEOUT)
                        # message = await ws.recv()
                    except asyncio.TimeoutError:
                        # No situation received or traffic in CHECK_CONNECTION_TIMEOUT seconds, retry to connect
                        logging.debug(name + ': TimeOut received waiting for message.')
                        if situation['connected'] is False:  # Probably connection lost
                            logging.debug(name + ': Watchdog detected connection loss.' +
                                                 ' Retrying connect in {} sec '.format(LOST_CONNECTION_TIMEOUT))
                            await asyncio.sleep(LOST_CONNECTION_TIMEOUT)
                            break
                    except websockets.exceptions.ConnectionClosed:
                        logging.debug(
                            name + ' ConnectionClosed. Retrying connect in {} sec '.format(LOST_CONNECTION_TIMEOUT))
                        await asyncio.sleep(LOST_CONNECTION_TIMEOUT)
                        break
                    except asyncio.CancelledError:
                        print(name + " shutting down ... ")
                        return
                    else:
                        callback(message)
                    await asyncio.sleep(MINIMAL_WAIT_TIME)  # do a minimal wait to let others do their jobs

        except (socket.error, websockets.exceptions.WebSocketException):
            logging.debug(name + ' WebSocketException. Retrying connection in {} sec '.format(RETRY_TIMEOUT))
            if name == 'SituationHandler' and situation['connected']:
                situation['connected'] = False
                ahrs['was_changed'] = True
                situation['was_changed'] = True
                gmeter['was_changed'] = True
            await asyncio.sleep(RETRY_TIMEOUT)
            continue


async def user_interface():
    global bt_devices
    global sound_on
    global ui_changed
    global global_mode

    last_bt_checktime = 0.0
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
            elif global_mode == 4:  # refresh mode
                next_mode = 0   # wait for display to change next mode
                await asyncio.sleep(UI_REACTION_TIME*2)   # give display driver time ...
            elif global_mode == 5:  # ahrs
                next_mode = ahrsui.user_input()
            elif global_mode == 7:  # status
                next_mode = statusui.user_input(bluetooth_active)
            elif global_mode == 9:  # gmeter
                next_mode = gmeterui.user_input()


            if next_mode > 0:
                ui_changed = True
                global_mode = next_mode

            current_time = time.time()
            if speak and current_time > last_bt_checktime + BLUEZ_CHECK_TIME:
                last_bt_checktime = current_time
                new_devices, devnames = radarbluez.connected_devices()
                logging.debug("User Interface: Bluetooth " + str(new_devices) + " devices connected.")
                if new_devices != bt_devices:
                    if new_devices > bt_devices:  # new or additional device
                        radarbluez.speak("Radar connected")
                    bt_devices = new_devices
                    ui_changed = True
    except asyncio.CancelledError:
        print("UI task terminating ...")
        logging.debug("Display task terminating ...")


async def display_and_cutoff():
    global aircraft_changed
    global global_mode
    global display_control

    try:
        while True:
            await asyncio.sleep(MIN_DISPLAY_REFRESH_TIME)
            if display_control.is_busy():
                await asyncio.sleep(display_refresh_time / 3)
                # try it several times to be as fast as possible
            else:
                if global_mode == 1:   # Radar
                    draw_display(draw)
                elif global_mode == 2:   # Timer'
                    timerui.draw_timer(draw, display_control, display_refresh_time)
                elif global_mode == 3:   # shutdown
                    final_shutdown = shutdownui.draw_shutdown(draw, display_control)
                    if final_shutdown:
                        logging.debug("Shutdown triggered: Display task terminating ...")
                        return
                elif global_mode == 4:   # refresh display, only relevant for epaper, mode was radar
                    logging.debug("Radar: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 1
                elif global_mode == 5:   # ahrs'
                    ahrsui.draw_ahrs(draw, display_control, situation['connected'], ahrs['was_changed'], ahrs['pitch'],
                                     ahrs['roll'], ahrs['heading'], ahrs['slipskid'], ahrs['gps_hor_accuracy'],
                                     ahrs['ahrs_sensor'])
                    ahrs['was_changed'] = False
                elif global_mode == 6:   # refresh display, only relevant for epaper, mode was radar
                    logging.debug("AHRS: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 5
                elif global_mode == 7:  # status display
                    statusui.draw_status(draw, display_control, bluetooth_active)
                elif global_mode == 8:   # refresh display, only relevant for epaper, mode was status
                    logging.debug("Status: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 7
                elif global_mode == 9:  # gmeter display
                    gmeterui.draw_gmeter(draw, display_control, situation['connected'], gmeter)
                elif global_mode == 10:   # refresh display, only relevant for epaper, mode was gmeter
                    logging.debug("Gmeter: Display driver - Refreshing")
                    display_control.refresh()
                    global_mode = 9

            to_delete = []
            cutoff = time.time() - RADAR_CUTOFF
            for icao, ac in all_ac.items():
                if ac['last_contact_timestamp'] < cutoff:
                    logging.debug("Cutting of " + hex(icao))
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
                    logging.debug("WATCHDOG: No update received in " + str(WATCHDOG_TIMER) + " seconds")
    except (asyncio.CancelledError, RuntimeError):
        print("Display task terminating ...")
        logging.debug("Display task terminating ...")


async def courotines():
    await asyncio.wait([listen_forever(url_radar_ws, "TrafficHandler", new_traffic),
                        listen_forever(url_situation_ws, "SituationHandler", new_situation),
                        display_and_cutoff(), user_interface()])


def main():
    global max_pixel
    global zerox
    global zeroy
    global draw
    global display_refresh_time
    global bluetooth_active

    radarui.init(url_settings_set)
    if speak:
        bluetooth_active = radarbluez.bluez_init()
    draw, max_pixel, zerox, zeroy, display_refresh_time = display_control.init()
    ahrsui.init(display_control)
    statusui.init(display_control, url_status_get, url_host_base, display_refresh_time, global_config)
    gmeterui.init(url_gmeter_reset)
    display_control.startup(draw, RADAR_VERSION, url_host_base, 4)
    try:
        asyncio.run(courotines())
    except asyncio.CancelledError:
        logging.debug("Main cancelled")


def quit_gracefully(*args):
    print("Keyboard interrupt. Quitting ...")
    tasks = asyncio.all_tasks()
    for ta in tasks:
        ta.cancel()
    print("CleanUp Display ...")
    display_control.cleanup()
    return 0


if __name__ == "__main__":
    # parse arguments for different configurations
    ap = argparse.ArgumentParser(description='Stratux web radar for separate displays')
    ap.add_argument("-d", "--device", required=True, help="Display device to use")
    ap.add_argument("-s", "--speak", required=False, help="Speech warnings on", action='store_true', default=False)
    ap.add_argument("-t", "--timer", required=False, help="Start mode is timer", action='store_true', default=False)
    ap.add_argument("-a", "--ahrs", required=False, help="Start mode is ahrs", action='store_true', default=False)
    ap.add_argument("-x", "--status", required=False, help="Start mode is status", action='store_true', default=False)
    ap.add_argument("-g", "--gmeter", required=False, help="Start mode is g-meter", action='store_true', default=False)
    ap.add_argument("-c", "--connect", required=False, help="Connect to Stratux-IP", default=DEFAULT_URL_HOST_BASE)
    ap.add_argument("-v", "--verbose", required=False, help="Debug output on", action="store_true", default=False)
    ap.add_argument("-r", "--registration", required=False, help="Display registration no",
                    action="store_true", default=False)
    args = vars(ap.parse_args())
    if args['verbose']:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s > %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)-15s > %(message)s')
    url_host_base = args['connect']
    display_control = importlib.import_module('displays.' + args['device'] + '.controller')
    speak = args['speak']
    if args['timer']:
        global_mode = 2   # start_in_timer_mode
    if args['ahrs']:
        global_mode = 5   # start_in_ahrs mode
    if args['status']:
        global_mode = 7   # start in status mode
    if args['gmeter']:
        global_mode = 9   # start in g-meter mode
    global_config['display_tail'] = args['registration'] # display registration if set
    # check config file, if extistent use config from there
    url_host_base = args['connect']
    saved_config = statusui.read_config()
    if saved_config is not None:
        if 'stratux_ip' in saved_config:
            url_host_base = saved_config['stratux_ip']   # set stratux ip if interactively changed one time
        if 'display_tail' in saved_config:
            global_config['display_tail'] = saved_config['display_tail']
    url_situation_ws = "ws://" + url_host_base + "/situation"
    url_radar_ws = "ws://" + url_host_base + "/radar"
    url_settings_set = "http://" + url_host_base + "/setSettings"
    url_status_get = "http://" + url_host_base + "/getStatus"
    url_gmeter_reset = "http://" + url_host_base + "/resetGMeter"

    try:
        signal.signal(signal.SIGINT, quit_gracefully)  # to be able to receive sigint
        main()
    except KeyboardInterrupt:
        pass
