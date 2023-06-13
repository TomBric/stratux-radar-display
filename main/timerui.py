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

import time
import radarbuttons
import math
import radarbluez
import flighttime
import datetime
import logging
import radarmodes

# constants
MAX_COUNTDOWN_TIME = 2 * 60 * 60   # maximum time for setting countdown in seconds

# global variables
left_text = ''
middle_text = 'Mode'
right_text = 'Start'
lap_head = 'Laptimer'

stoptime = 0
laptime = 0
timer_running = False
was_in_secs = 0.0       # last time displayed
timer_ui_changed = True
cdown_time = 0.0     # count down
cdown_spoken = False  # to speak zero only once
timer_mode = 0    # 0 = normal, 1 = countdown-set
g_config = {}


def init(config):
    global g_config

    g_config = config
    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("Timerui: timer initialized")


def reset_timer():
    # called when clock had to be recalibrated, to be safe, all timers are reset!
    global stoptime
    global laptime
    global timer_running
    global was_in_secs
    global timer_ui_changed
    global cdown_time
    global cdown_spoken
    global timer_mode
    global lap_head
    global right_text
    global middle_text
    global left_text

    stoptime = 0
    laptime = 0
    timer_running = False
    was_in_secs = 0.0  # last time displayed
    timer_ui_changed = True
    cdown_time = 0.0  # count down
    cdown_spoken = False  # to speak zero only once
    timer_mode = 0  # 0 = normal, 1 = countdown-set
    lap_head = "Laptimer"
    right_text = "Start"
    middle_text = "Mode"
    left_text = ""


def draw_timer(draw, display_control, refresh_time):
    global was_in_secs
    global timer_ui_changed
    global cdown_spoken
    global lap_head

    now_in_secs = math.floor(time.time())
    if not timer_ui_changed and now_in_secs < was_in_secs + math.ceil(refresh_time):
        return    # nothing to display if time has not changed or change would be quicker than display
    was_in_secs = now_in_secs
    timer_ui_changed = False
    display_control.clear(draw)
    utctimestr = time.strftime("%H:%M:%S", time.gmtime(now_in_secs))
    if timer_running:
        stoptimestr = time.strftime("%H:%M:%S", time.gmtime(now_in_secs-stoptime))
        if laptime != 0:
            laptimestr = time.strftime("%H:%M:%S", time.gmtime(now_in_secs-laptime))
        else:
            if cdown_time == now_in_secs and not cdown_spoken:
                cdown_spoken = True
                radarbluez.speak("Countdown finished")
            if cdown_time <= now_in_secs:    # Countdown Finished
                ft = flighttime.current_starttime()
                if ft is not None:
                    lap_head = "Flighttime"
                    delta = (datetime.datetime.now(datetime.timezone.utc) - ft).total_seconds()
                    hours, remainder = divmod(delta, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    laptimestr = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
                else:
                    laptimestr = "--:--:--"
            else:
                laptimestr = time.strftime("%H:%M:%S", time.gmtime(cdown_time - now_in_secs))
    else:
        if stoptime != 0:
            stoptimestr = time.strftime("%H:%M:%S", time.gmtime(stoptime))
        else:
            stoptimestr = "--:--:--"
        if cdown_time == 0.0:
            ft = flighttime.current_starttime()
            if ft is not None:
                lap_head = "Flighttime"
                delta = (datetime.datetime.now(datetime.timezone.utc) - ft).total_seconds()
                hours, remainder = divmod(delta, 3600)
                minutes, seconds = divmod(remainder, 60)
                laptimestr = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
            else:
                laptimestr = "--:--:--"
        else:
            laptimestr = time.strftime("%H:%M:%S", time.gmtime(cdown_time))

    display_control.timer(draw, utctimestr, stoptimestr, laptimestr, lap_head, left_text, middle_text, right_text,
                          timer_running)
    display_control.display()


def user_input():
    global left_text
    global right_text
    global middle_text
    global stoptime
    global laptime
    global timer_running
    global timer_ui_changed
    global cdown_time
    global lap_head
    global timer_mode
    global cdown_spoken

    btime, button = radarbuttons.check_buttons()
    # start of timer global behaviour
    if btime == 0:
        return 0  # stay in timer mode
    timer_ui_changed = True
    if button == 1 and btime == 2:  # middle and long
        return radarmodes.next_mode_sequence(2)  # Timer mode was 2
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!

    # situation dependent behavior
    if timer_mode == 0:   # normal timer mode
        if button == 1 and btime == 1:   # middle and short
            laptime = 0.0  # cdown-time is set, forget old laptime
            timer_mode = 1
            if timer_running and cdown_time <= math.floor(time.time()):    # Countdown was finished
                cdown_time = 0.0
        if button == 2 and btime == 1:   # short right
            if timer_running:   # timer already running
                stoptime = math.floor(time.time()) - stoptime
                if cdown_time >= math.floor(time.time()):
                    cdown_time = cdown_time - math.floor(time.time())
                else:
                    cdown_time = 0.0
                laptime = 0    # also stop lap time
                timer_running = False
            else:
                stoptime = math.floor(time.time()) - stoptime   # add time already on clock
                if cdown_time > 0:
                    cdown_time = math.floor(time.time()) + cdown_time
                laptime = 0
                timer_running = True
        if button == 0:   # left
            if btime == 2:  # left and long
                return 3    # start next mode shutdown!
            else:
                if timer_running:
                    laptime = math.floor(time.time())
                    cdown_time = 0.0     # now lap mode
                else:
                    stoptime = 0
                    laptime = 0
                    cdown_time = 0.0
    elif timer_mode == 1:   # countdown set mode
        if timer_running and cdown_time == 0.0:
            cdown_time = math.floor(time.time())
        if button == 1 and btime == 1:   # middle and short
            timer_mode = 0
        elif button == 0 and btime == 1:  # left short
            cdown_time = cdown_time + 600  # ten more minutes
            cdown_spoken = False
            if timer_running:
                if cdown_time >= math.floor(time.time()) + MAX_COUNTDOWN_TIME:
                    cdown_time = 0
            else:
                if cdown_time >= MAX_COUNTDOWN_TIME:
                    cdown_time = 0
        elif button == 2 and btime == 1:  # right short
            cdown_time = cdown_time + 60
            cdown_spoken = False
            if timer_running:
                if cdown_time >= math.floor(time.time()) + MAX_COUNTDOWN_TIME:
                    cdown_time = 0.0
            else:
                if cdown_time >= MAX_COUNTDOWN_TIME:
                    cdown_time = 0.0

    # prepare display for next round
    if timer_mode == 1:  # next will be countdown-set
        lap_head = "Set Countdown"
        right_text = "+1m"
        middle_text = "Back"
        left_text = "+10m"
    else:  # next will be normal mode
        if cdown_time > 0:
            laptime = 0  # stop laptimer and do countdown
            lap_head = "Countdown"
        else:
            lap_head = "Laptimer"
        if timer_running:
            right_text = "Stop"
            middle_text = "Mode"
            left_text = "Lap"
        else:
            if stoptime == 0.0:
                right_text = "Start"
                middle_text = "Mode"
                left_text = ""
            else:
                right_text = "Cont"
                middle_text = "Mode"
                left_text = "Reset"
    timer_ui_changed = True
    return 2   # no mode change, but refresh display
