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
import requests
import radarbuttons
import time
import socket

# constants
STATUS_TIMEOUT = 1.0

# globals
status_url = ""
stratux_ip = "0.0.0.0"
last_status_get = 0.0  # time stamp of the last status request


def init(display_control, url, target_ip):   # prepare everything
    global status_url
    global stratux_ip

    status_url = url
    stratux_ip = target_ip
    logging.debug("Status UI: Initialized GET settings to " + status_url)


def get_status():
    global status_url

    try:
        answer = requests.get(status_url)
        status_answer = answer.json()
        print(status_answer)
    except (requests.exceptions.RequestException, ValueError) as e:
        print("Status UI: Status GET exception", e)
        logging.debug("Status UI: Status GET exception", e)
        return None
    return status_answer


def draw_status(draw, display_control):
    global status_changed

    now = time.time()
    if now >= last_status_get + STATUS_TIMEOUT:
        status_answer = get_status()
        try:
            hostname = socket.gethostname()
            my_ip = socket.gethostbyname(hostname)
        except OSError:
            hostname = "undef"
            my_ip = "0.0.0.0"
            print("StatusUI: Unable to get Hostname and IP")
        display_control.clear(draw)
        display_control.status(draw, status_answer, hostname, my_ip, stratux_ip)
        display_control.display()


def user_input():
    global status_ui_changed

    btime, button = radarbuttons.check_buttons()
    # start of ahrs global behaviour
    if btime == 0:
        return 0  # stay in timer mode
    status_ui_changed = True
    if button == 1 and btime == 2:  # middle and long
        return 1  # next mode to be radar
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 2 and btime == 2:  # right and long- refresh
        return 6  # start next mode for display driver: refresh called from ahrs
    return 7  # no mode change
