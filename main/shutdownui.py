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

import os
import subprocess
import radarbuttons
import time
import requests
import logging
import radarmodes

SHUTDOWN_WAIT_TIME = 6.0
shutdown_time = 0.0
shutdown_mode = 0   # 0 = both shutdown, 1 = display shutdown only, 2 = reboot stratux + display
clear_before_shutoff = False

url_reboot = ""
url_shutdown = ""
rlog = None


def init(shutdown, reboot):
    global url_reboot
    global url_shutdown
    global rlog

    url_reboot = reboot
    url_shutdown = shutdown
    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("ShutdownUI: Initialized settings to: reboot url " + url_reboot + " shutdown url " + url_shutdown)



def clear_lingering_radar():     # remove other radar.py processes, necessary sind lingering is enabled for bluetooth
    current_pid = os.getpid()   # my processid
    pid_list = []
    pname = "radar.py"
    try:
        output = subprocess.check_output(['pgrep', '-f', pname]).decode('utf-8').strip()
        pid_list = output.split('\n')   # generate a list
    except subprocess.CalledProcessError:
        pass
    for proc in pid_list:
        if proc != current_pid:
            try:
                os.kill(proc, 15)   # Terminate signal
            except OSError :
                pass


def draw_shutdown(display_control):
    global clear_before_shutoff
    global shutdown_mode

    if shutdown_time > 0:
        display_control.clear()
        rest_time = int(shutdown_time - time.time())
        if rest_time < 0:
            rest_time = 0   # if clear is too slow, so that not a minus is displayed
        display_control.shutdown(rest_time, shutdown_mode)
        display_control.display()
    if clear_before_shutoff:   # this is signal for display driver to initiate shutdown/reboot
        display_control.cleanup()

        if shutdown_mode == 0:   # shutdown display and stratux
            rlog.debug("Posting shutdown.")
            try:
                requests.post(url_shutdown)
            except requests.exceptions.RequestException as e:
                rlog.debug("Posting shutdown exception: ", e)
            os.popen("sudo shutdown --poweroff now").read()
        elif shutdown_mode == 1:   # only display shutdown
            os.popen("sudo shutdown --poweroff now").read()
        elif shutdown_mode == 2:   # reboot display and stratux
            rlog.debug("Posting reboot.")
            try:
                requests.post(url_reboot)
            except requests.exceptions.RequestException as e:
                rlog.debug("Posting shutdown exception: ", e)
            os.popen("sudo shutdown --reboot now").read()

        clear_before_shutoff = False
        return True
    else:
        return False


def user_input():
    global shutdown_time
    global shutdown_mode
    global clear_before_shutoff

    if shutdown_time == 0.0:     # first time or after stopped shutdwon
        shutdown_time = time.time() + SHUTDOWN_WAIT_TIME
    btime, button = radarbuttons.check_buttons()
    if btime == 0:   # nothing pressed
        if time.time() > shutdown_time:
            rlog.debug("Shutdown now")
            clear_before_shutoff = True  # enable display driver to trigger shutdown
        return 0  # stay in current mode
    if button == 0:  # left
        shutdown_mode = 0
        shutdown_time = 0.0
        return radarmodes.first_mode_sequence()  # go back to first mode selected
    if button == 1:  # middle, display only shutdown
        shutdown_mode = 1
        shutdown_time = 0.0
        return 3  # stay in shutdown mode
    if button == 2:  # right, reboot all
        shutdown_mode = 2
        shutdown_time = 0.0
        return 3  # stay in shutdown mode
    return 3  # no mode change
