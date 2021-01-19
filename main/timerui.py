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

# global variables
left_text = ''
middle_text = 'Mode'
right_text = 'Start'
timerui_changed = True
timer_changed = True

stoptime = 0
laptime = 0
timer_running = False


def draw_timer(draw, display_control):
    if timerui_changed or timer_changed:
        # display is only triggered if there was a change
        display_control.clear(draw)
        utctimestr = time.strftime("%H:%M:%S", time.gmtime())
        if timer_running:
            stoptimestr = time.strftime("%H:%M:%S", time.gmtime(time.time()-stoptime))
        elif stoptime != 0:
            stoptimestr = time.strftime("%H:%M:%S", tim.gmtime(stoptime))
        else:
            stoptimestr = "--:--:--"
        if laptime != 0:
            laptimestr = time.strftime("%H:%M:%S", time.gmtime(laptime))
        else:
            laptimestr = "--:--:--"
        display_control.timer(draw, utctimestr, stoptimestr, laptimestr, left_text, middle_text, right_text)
        display_control.display()


def user_input():
    global left_text
    global right_text
    global middle_text
    global stoptime
    global laptime
    global timer_running
    global timerui_changed

    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        timerui_changed = 0
        return False
    if button == 1 and btime == 2:  # middle and long
            return True   # next mode
    if button == 2:   # right
        if timer_running:   # timer already running
            stoptime = time.time() - stoptime
            timer_running = False
            right_text = "Start"
            left_text = "Reset"
        else:
            stoptime = time.time()
            timer_running = True
            right_text = "Stop"
            left_text = "Lap"
    if button == 0:   # left
        if timer_running:
            laptime = time.time() - stoptime
            left_text = "Cont"
        else:
            stoptime = 0
            laptime = 0
    timerui_changed = True
    return False   # no mode change
