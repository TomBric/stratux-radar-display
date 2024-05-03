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
from gpiozero import Button
from gpiozero.exc import GPIOZeroError, GPIODeviceError

btn = None   # will be set in init
gear_down_btn = None   # will be set ini int

# global constants
HOLD_TIME = 0.8 # time to trigger the hold activity if one button is pressed longer
GEAR_HOLD_TIME = 0.3   # time until gear is indicated to be down
BOUNCE_TIME = 0.05
LEFT = 26
MIDDLE = 20
RIGHT = 21
GEAR_DOWN = 19

class RadarButton:
    def __init__(self,gpio_number):
        self.btn = Button(gpio_number, bounce_time=BOUNCE_TIME, hold_time=HOLD_TIME)
        self.short = False
        self.long = False
        self.already_triggered = False
        self.btn.when_released = self.released
        self.btn.when_held = self.held

    def released(self):
        if not self.already_triggered:
            self.short = True
        else:
            self.already_triggered = False

    def held(self):
        self.long = True
        self.already_triggered = True

    def check_button(self):
        if self.long:
            self.long = False
            return 2
        if self.short:
            self.short = False
            return 1
        return 0


def init():
    global rlog
    global btn

    rlog = logging.getLogger('stratux-radar-log')
    try:
        btn = [RadarButton(LEFT), RadarButton(MIDDLE), RadarButton(RIGHT)]
    except:
        rlog.debug("ERROR: GPIO-Pins busy! No input possible. Please clarify!")
        return False  # indicate errors
    rlog.debug("Radarbuttons: Initialized.")
    return True    # indicate everything is fine



def check_buttons():  # returns 0=nothing 1=short press 2=long press and returns Button (0,1,2)
    for index, but in enumerate(btn):
        stat = but.check_button()
        if stat > 0:
            rlog.debug("Button press: button {0} presstime {1} (1=short, 2=long)".format(index, stat))
            return stat, index
    return 0, 0


def gear_is_down():
    return gear_down_btn.is_held

def init_gear_indicator(global_config, gear_down_indication):
    global gear_down_btn

    global_config['gear_indication_active'] = False
    if gear_down_indication:
        try:
            gear_down_btn = Button(GEAR_DOWN, bounce_time=BOUNCE_TIME, hold_time=GEAR_HOLD_TIME)
        except:
            rlog.debug("Radarbuttons ERROR: GPIO-Pin {0} for gear down indication busy! Please clarify!".format(GEAR_DOWN))
        else:
            global_config['gear_indication_active'] = True
            rlog.debug("Radarbuttons: Gear down indicator on GPIO{0} initialized.".format(GEAR_DOWN))