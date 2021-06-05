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


# constants

# globals
status = {}
status_url = ""
rlog = None
status_listener = None   # couroutine task for querying statux
strx_status = {'was_changed': True, 'version': "0.0", 'ES_messages_last_minute': 0, 'ES_messages_max': 0,
               'OGN_messages_last_minute': 0, 'OGN_messages_max': 0, 'UAT_messages_last_minute': 0,
               'UAT_messages_max': 0, 'CPUTemp': "unavail", 'GPS_satellites_locked': 0, 'GPS_satellites_tracked': 0,
               'GPS_satellites_seen': 0}
left = ""
middle = ""
right = ""


def init(display_control, url):   # prepare everything
    global status_url
    global rlog

    status_url = url
    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("StratuxStatus UI: Initialized with URL " + status_url)


def start():  # start listening on status websocket
    global status_listener

    if status_listener is None:
        print("Listener was none, starting")
        loop = asyncio.get_event_loop()
        status_listener = loop.create_task(radar.listen_forever(status_url, "StatusListener", status_callback))
        print("Listener ", status_listener)


def stop():  # stop listening on status websocket
    print("Stopping status ws ")
    if status_listener is not None:
        status_listener.cancel()


def draw_status(draw, display_control, ui_changed, connected):
    global strx_status

    headline = "Stratux Status"
    if strx_status['was_changed'] or ui_changed:
        display_control.clear(draw)
        if connected:
            subline = strx_status['version']
            text = \
                "Messages\n" +\
                " 1090: Cur " + str(strx_status['ES_messages_last_minute']) + "Pea " + str(strx_status['ES_messages_max']) + "\n" +\
                " OGN : Cur " + str(strx_status['OGN_messages_last_minute']) + "Pea " + str(strx_status['OGN_messages_max']) + "\n" +\
                " UAT:  Cur " + str(strx_status['UAT_messages_last_minute']) + "Pea " + str(strx_status['UAT_messages_max']) + "\n" +\
                "CPU_Temp: " + strx_status['CPUTemp'] + "\n" + \
                "Sat: " + str(strx_status['GPS_satellites_locked']) + "lock " + str(strx_status['GPS_satellites_tracked']) +\
                " trac" + str(strx_status['GPS_satellites_seen']) + " seen"
            strx_status['was_changed'] = False
        else:
            subline = "Not connected"
            text = ""
        display_control.text_screen(draw, headline, subline, text, "", "Mode", "")


def status_callback(json_str):
    global strx_status

    print("Status callback received.")
    rlog.debug("New status" + json_str)
    stat = json.loads(json_str)

    strx_status['was_changed'] = True

    strx_status['version'] = stat['Version']
    strx_status['devices'] = stat['Devices']

    strx_status['UAT_messages_last_minute'] = stat['UAT_messages_last_minute']
    strx_status['UAT_messages_max'] = stat['UAT_messages_max']
    strx_status['ES_messages_last_minute'] = stat['ES_messages_last_minute']
    strx_status['ES_messages_max'] = stat['ES_messages_max']
    strx_status['OGN_messages_last_minute'] = stat['OGN_messages_last_minute']
    strx_status['OGN_messages_max'] = stat['OGN_messages_max']

    strx_status['GPS_satellites_locked'] = stat['GPS_satellites_locked']
    strx_status['GPS_satellites_tracked'] = stat['GPS_satellites_tracked']
    strx_status['GPS_satellites_seen'] = stat['GPS_satellites_seen']
    strx_status['GPS_solution'] = stat['GPS_solution']

    strx_status['OGN_noise_db'] = stat['OGN_noise_db']
    strx_status['OGN_gain_db'] = stat['OGN_gain_db']

    if 'CPUTemp' in stat:
        strx_status['CPUTemp'] = str(round(stat['CPUTemp'], 1)) + "°C / " + str(round(stat['CPUTemp']*9/5+32.0, 1)) + "°F"
    else:
        strx_status['CPUTemp'] = "unaivalable"


def user_input():
    global left
    global middle
    global right

    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        return 0  # stay in current mode
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 1 and (btime == 2 or btime == 1):  # middle
        return 1  # next mode to be radar
    return 15  # no mode change
