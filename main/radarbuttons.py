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
time_middle = 0.0
status_middle = False


def init():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(LEFT, GPIO.IN, GPIO.PUD_UP)  # left
    GPIO.setup(MIDDLE, GPIO.IN, GPIO.PUD_UP)  # middle
    GPIO.setup(RIGHT, GPIO.IN, GPIO.PUD_UP)  # right

    GPIO.add_event_detect(LEFT, GPIO.FALLING, bouncetime=300)  # toggle
    GPIO.add_event_detect(RIGHT, GPIO.FALLING, bouncetime=300)  # toggle

    logging.debug("Radarbuttons: Initialized.")

def check_buttons():  # returns 0=nothing 1=short press 2=long press and returns Button (0,1,2)
    global time_middle
    global status_middle

    if GPIO.event_detected(LEFT):
        logging.debug("UI: Button press short left")
        return 1, 0   # short + left
    elif GPIO.event_detected(RIGHT):
        logging.debug("UI: Button press short right")
        return 1, 2   # short + right
    if GPIO.input(MIDDLE) == GPIO.LOW:
        if not status_middle:  # now it is pressed
            time_middle = time.time()
            status_middle = True
        else:
            if time.time() - time_middle > HOLD_TIME:  # pressed for a long time
                status_middle = False  # reset
                logging.debug("UI: Button press long middle")
                return 2, 1   # long + middle
    else:
        if status_middle:  # it was only a short press
            status_middle = False
            logging.debug("UI: Button press short middle")
            return 1, 1
        status_middle = False
    return 0, 0


