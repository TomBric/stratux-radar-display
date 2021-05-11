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
import time
import RPi.GPIO as GPIO

# global constants
HOLD_TIME = 1.0  # time to trigger the hold activity if one button is pressed longer
LEFT = 26
MIDDLE = 20
RIGHT = 21

# status
rlog = None
time_left = 0.0
time_middle = 0.0
time_right = 0.0
status_left = False
status_middle = False
status_right = False

io_status = {LEFT: {'virtualno': 0, 'status': False, 'starttime': 0.0, 'already_triggered': False},
             MIDDLE: {'virtualno': 1, 'status': False, 'starttime': 0.0, 'already_triggered': False},
             RIGHT: {'virtualno': 2, 'status': False, 'starttime': 0.0, 'already_triggered': False}}


def init():
    global io_status
    global rlog

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for iopin in io_status:
        GPIO.setup(iopin, GPIO.IN, GPIO.PUD_UP)
        GPIO.add_event_detect(iopin, GPIO.FALLING, bouncetime=300)

    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("Radarbuttons: Initialized.")


def reset_buttons():   # called if timer was modified. Reset of all timestamps necessary
    global io_status

    for button in io_status:
        io_status[button]['starttime'] = 0.0


def check_one_button(button):
    global io_status

    if GPIO.event_detected(button):   # triggers on pull down
        if GPIO.input(button) != GPIO.LOW:  # not pressed anymore
            io_status[button]['status'] = False
            if not io_status[button]['already_triggered']:
                return 1  # short press
            else:
                io_status[button]['already_triggered'] = False
                return 0  # unfortunately falling edge is triggered again if a long press is finished
        else:   # event detected and still pressed
            io_status[button]['starttime'] = time.time()
            io_status[button]['status'] = True
            return 0
    if GPIO.input(button) == GPIO.LOW:
        # pressed, but was already pressed, since no event was detected
        if time.time() - io_status[button]['starttime'] >= HOLD_TIME:  # pressed for a long time
            if not io_status[button]['already_triggered']:  # long hold was not triggered yet
                io_status[button]['already_triggered'] = True
                io_status[button]['status'] = False
                return 2  # long
            else:  # long press but already triggered
                return 0
        else:
            return 0  # press time shorter, but not yet released, nothing to do
    else:  # no more pressed
        io_status[button]['already_triggered'] = False
        if io_status[button]['status']:    # but was pressed before and did not trigger long press
            io_status[button]['status'] = False
            return 1  # short press
    return 0   # no event, nothing pressed anymore


def check_buttons():  # returns 0=nothing 1=short press 2=long press and returns Button (0,1,2)
    global io_status

    for button in io_status:
        stat = check_one_button(button)
        if stat > 0:
            rlog.debug("Button press: button " + str(io_status[button]['virtualno'])
                          + " presstime " + str(stat) + " (1=short, 2=long)")
            return stat, io_status[button]['virtualno']
    return 0, 0
