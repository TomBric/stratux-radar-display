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

import logging
import radar
import radarbuttons
import asyncio
import json
import radarmodes

# constants
SITUATION_DEBUG = logging.DEBUG-2

# globals
status = {}
status_url = ""
rlog = None
status_listener = None  # couroutine task for querying statux
strx = {'was_changed': True, 'version': "0.0", 'ES_messages_last_minute': 0, 'ES_messages_max': 0,
        'OGN_connected': False, 'OGN_messages_last_minute': 0, 'OGN_messages_max': 0,
        'UATRadio_connected': False, 'UAT_messages_last_minute': 0, 'UAT_messages_max': 0,
        'CPUTemp': -300, 'CPUTempMax': -300,
        'GPS_connected': False, 'GPS_satellites_locked': 0, 'GPS_satellites_tracked': 0, 'GPS_position_accuracy': 0,
        'GPS_satellites_seen': 0, 'OGN_noise_db': 0.0, 'OGN_gain_db': 0.0,
        'IMUConnected': False, 'BMPConnected': False, 'GPS_detected_type': "Unknown"}
left = ""
middle = ""
right = ""


def init(display_control, url):  # prepare everything
    global status_url
    global rlog

    status_url = url
    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("StratuxStatus UI: Initialized with URL " + status_url)


def start():  # start listening on status websocket
    global status_listener

    if status_listener is None:
        loop = asyncio.get_event_loop()
        status_listener = loop.create_task(radar.listen_forever(status_url, "StatusListener", status_callback, rlog))
        if status_listener is None:
            rlog.debug("Error: Stratux status listener not started.")


def stop():  # stop listening on status websocket
    global status_listener

    if status_listener is not None:
        status_listener.cancel()
        status_listener = None


hardware = [
    "Not installed",  # 0
    "Serial port",   # 1
    "Prolific USB-serial bridge",  # 2
    "OGN Tracker",  # 3
    "Not installed",  # 4
    "Not installed",  # 5
    "USB u-blox 6 GPS receiver",  # 6
    "USB u-blox 7 GNSS receiver",  # 7
    "USB u-blox 8 GNSS receiver",  # 8
    "USB u-blox 9 GNSS receiver",  # 9
    "USB Serial IN",  # 10
    "SoftRF Dongle",  # 11
    "Network",  # 12
    "Not installed", # 13
    "Not installed", # 14
    "GxAirCom", # 15
]


def decode_gps_hardware(detected_type):
    code = detected_type & 0x0f
    if code < len(hardware):
        s = hardware[code]
    else:
        s = "unknown"
    gps_prot = detected_type >> 4
    if gps_prot == 1:
        s += " (NMEA prot)"
    else:
        s += " (Not comm)"
    return s


def draw_status(draw, display_control, ui_changed, connected, altitude, gps_alt, gps_quality):
    global strx
    if strx['was_changed'] or ui_changed or not connected:
        display_control.clear(draw)
        if connected:
            display_control.stratux(draw, strx, altitude, gps_alt, gps_quality)
        else:
            headline = "Stratux"
            subline = "not connected"
            text = ""
            display_control.text_screen(draw, headline, subline, text, "", "Mode", "")
        display_control.display()
        strx['was_changed'] = False


def status_callback(json_str):
    global strx

    rlog.log(SITUATION_DEBUG, "New status" + json_str)
    stat = json.loads(json_str)

    strx['was_changed'] = True

    strx['version'] = stat['Version']
    strx['devices'] = stat['Devices']

    strx['UATRadio_connected'] = stat['UATRadio_connected']
    strx['UAT_messages_last_minute'] = stat['UAT_messages_last_minute']
    strx['UAT_messages_max'] = stat['UAT_messages_max']

    strx['ES_messages_last_minute'] = stat['ES_messages_last_minute']
    strx['ES_messages_max'] = stat['ES_messages_max']

    strx['OGN_connected'] = stat['OGN_connected']
    strx['OGN_messages_last_minute'] = stat['OGN_messages_last_minute']
    strx['OGN_messages_max'] = stat['OGN_messages_max']

    strx['GPS_connected'] = stat['GPS_connected']
    strx['GPS_satellites_locked'] = stat['GPS_satellites_locked']
    strx['GPS_satellites_tracked'] = stat['GPS_satellites_tracked']
    strx['GPS_satellites_seen'] = stat['GPS_satellites_seen']
    strx['GPS_solution'] = stat['GPS_solution']
    strx['GPS_position_accuracy'] = stat['GPS_position_accuracy']

    strx['OGN_noise_db'] = stat['OGN_noise_db']
    strx['OGN_gain_db'] = stat['OGN_gain_db']

    strx['BMPConnected'] = stat['BMPConnected']
    strx['IMUConnected'] = stat['IMUConnected']
    strx['GPS_detected_type'] = decode_gps_hardware(stat['GPS_detected_type'])

    if 'CPUTemp' in stat:
        strx['CPUTemp'] = stat['CPUTemp']
        strx['CPUTempMax'] = stat['CPUTempMax']
    else:
        strx['CPUTemp'] = -300


def user_input():
    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        return 0  # stay in current mode
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 2 and btime == 2:  # right and long, refresh
        return 16  # start next mode for display driver: refresh called from gmeter
    if button == 1 and (btime == 2 or btime == 1):  # middle
        return radarmodes.next_mode_sequence(15)
    return 15  # no mode change
