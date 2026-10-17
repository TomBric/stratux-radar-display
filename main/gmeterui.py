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

import radarbuttons
from globals import rlog, Modes
import requests
import radarmodes
from button_input import get_button_event, is_middle, is_left_long, is_right_long, is_right_short

# constants
MSG_NO_CONNECTION = "No Connection!"
REQUEST_TIMEOUT = 5.0
# globals
url_gmeter_reset = ""
gmeterui_changed = True


def init(url):
    global url_gmeter_reset

    url_gmeter_reset = url
    rlog.debug("GMeterUI: Initialized POST settings to " + url_gmeter_reset)


def reset_gmeter():
    rlog.debug("GMeterUI: Reset gmeter triggered")
    try:
        requests.post(url_gmeter_reset, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as e:
        rlog.debug(f"Posting gmeter-reset exception: {e}")


def draw_gmeter(display_control, ui_changed, connected, gmeter):
    global gmeterui_changed

    if ui_changed or gmeter['was_changed'] or gmeterui_changed:
        gmeterui_changed = False
        error_message = None
        if not connected:
            error_message = MSG_NO_CONNECTION
        display_control.clear()
        display_control.gmeter(gmeter['current'], gmeter['max'], gmeter['min'], error_message)
        display_control.display()


def user_input():
    global gmeterui_changed

    event = get_button_event()
    if event is None:
        return Modes.NO_CHANGE
    rlog.debug("GMeter UI: button pressed")
    gmeterui_changed = True
    if is_middle(event):
        return radarmodes.next_mode_sequence(Modes.GMETER)
    if is_left_long(event):
        return Modes.SHUTDOWN
    if is_right_long(event):
        return Modes.REFRESH_GMETER
    if is_right_short(event):
        reset_gmeter()
        return Modes.GMETER
    return Modes.GMETER
