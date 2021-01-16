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
import requests

# global constants
HOLD_TIME = 1.0  # time to trigger the hold activity if one button is pressed longer
LEFT = 26
MIDDLE = 20
RIGHT = 21

# status
time_middle = 0.0
status_middle = False

# status variables for state machine
display_mode = ('init', 'radar', 'setup', 'ahrs', 'clock')
display_radius = (2, 5, 10, 20, 40)
height_diff = (10, 20, 50, 100, 500)
sound_on = True
mode = 1  # index in radar mode
radius = 0  # index in display_radius
height = 0  # index in height_diff

url_settings_set = ""


def init(url):
    global url_settings_set

    print("UI-Init")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(LEFT, GPIO.IN, GPIO.PUD_UP)  # left
    GPIO.setup(MIDDLE, GPIO.IN, GPIO.PUD_UP)  # middle
    GPIO.setup(RIGHT, GPIO.IN, GPIO.PUD_UP)  # right

    GPIO.add_event_detect(LEFT, GPIO.FALLING, bouncetime=300)  # toggle
    GPIO.add_event_detect(RIGHT, GPIO.FALLING, bouncetime=300)  # toggle

    url_settings_set = url
    logging.debug("Radar UI: Initialized POST settings to " + url_settings_set)


def start_radar_mode():
    global mode
    mode = 1


def communicate_limits(radarrange, threshold):
    global url_settings_set

    print("COMMUNICATE LIMITS: Radius " + str(radarrange) + " Height " + str(threshold))
    try:
        requests.post(url_settings_set, data={'RadarLimits': threshold*100, 'RadarRange': radarrange})
    except requests.exceptions.RequestException as e:
        logging.debug("Posting limits exception", e)


def check_user_input():
    global time_middle
    global radius
    global height
    global status_middle

    current_time = time.time()
    if mode == 1:  # radar mode
        if GPIO.event_detected(LEFT):
            radius += 1
            if radius >= len(display_radius):
                radius = 0
            communicate_limits(display_radius[radius], height_diff[height])

        if GPIO.event_detected(RIGHT):
            height += 1
            if height >= len(height_diff):
                height = 0
            communicate_limits(display_radius[radius], height_diff[height])

        if GPIO.input(MIDDLE) == GPIO.LOW:
            if not status_middle:  # now it is pressed
                time_middle = current_time
                status_middle = True
            else:
                if current_time - time_middle > HOLD_TIME:  # pressed for a long time
                    status_middle = False  # reset
                    print("Starting AHRS MODE")
        else:
            status_middle = False
