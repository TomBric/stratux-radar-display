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
import signal
import time
import requests
from globals import rlog, Modes
import radarmodes
from button_input import get_button_event, is_left, is_middle, is_right
import dispatcher

SHUTDOWN_WAIT_TIME = 6.0
shutdown_time = 0.0
shutdown_mode = 0   # 0 = both shutdown, 1 = display shutdown only, 2 = reboot stratux + display
clear_before_shutoff = False

url_reboot = ""
url_shutdown = ""


def init(shutdown, reboot):
    global url_reboot
    global url_shutdown

    url_reboot = reboot
    url_shutdown = shutdown
    rlog.debug("ShutdownUI: Initialized settings to: reboot url " + url_reboot + " shutdown url " + url_shutdown)


def _find_radar_pids():   # scan /proc instead of starting pgrep, finds python processes running radar.py
    pids = []
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            with open(f'/proc/{entry}/cmdline', 'rb') as f:
                args = f.read().decode('utf-8', errors='ignore').split('\0')
        except OSError:
            continue
        if len(args) > 1 and 'python' in os.path.basename(args[0]) and \
                any(os.path.basename(a) == 'radar.py' for a in args[1:3]):
            pids.append(int(entry))
    return pids


def clear_lingering_radar():     # remove other radar.py processes, necessary since lingering is enabled for bluetooth
    current_pid = os.getpid()   # my processid
    for pid in _find_radar_pids():
        if pid == current_pid:
            continue
        try:
            print("Terminating other process {0}".format(pid))
            os.kill(pid, signal.SIGTERM)   # SIGTERM signal
        except OSError:
            continue
        deadline = time.time() + 5   # give him some time to terminate, but continue as soon as he is gone
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.05)

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
        # display_control.cleanup()
        dispatcher.emit_shutdown()
        # cleanup all ressources, running task is not immediately terminated
        # so that display driver can finish cleanup and shutdown
        rlog.debug("ShutdownUI: Cleanup all tasks done.")
        display_control.cleanup()
        rlog.debug("ShutdownUI: Display control cleanup done, now shutdown/reboot")
        if shutdown_mode == 0:   # shutdown display and stratux
            if url_shutdown:
                rlog.debug("Posting shutdown.")
                try:
                    requests.post(url_shutdown)
                except requests.exceptions.RequestException as e:
                    rlog.debug(f"Exception posting shutdown: {e}")
            try:
                subprocess.run(["sudo", "shutdown", "--poweroff", "now"], check=False)
            except OSError as e:
                rlog.debug(f"Shutdown command failed: {e}")
        elif shutdown_mode == 1:   # only display shutdown
            try:
                subprocess.run(["sudo", "shutdown", "--poweroff", "now"], check=False)
            except OSError as e:
                rlog.debug(f"Shutdown command failed: {e}")
        elif shutdown_mode == 2:   # reboot display and stratux
            if url_reboot:
                rlog.debug("Posting reboot.")
                try:
                    requests.post(url_reboot)
                except requests.exceptions.RequestException as e:
                    rlog.debug(f"Exception posting reboot: {e}")
            try:
                subprocess.run(["sudo", "shutdown", "--reboot", "now"], check=False)
            except OSError as e:
                rlog.debug(f"Shutdown command failed: {e}")
        clear_before_shutoff = False
        return True
    else:
        return False


def user_input():
    global shutdown_time
    global shutdown_mode
    global clear_before_shutoff

    if shutdown_time == 0.0:
        shutdown_time = time.time() + SHUTDOWN_WAIT_TIME

    event = get_button_event()
    if event is None:
        if time.time() > shutdown_time:
            rlog.debug("Shutdown now")
            clear_before_shutoff = True
        return Modes.NO_CHANGE
    if is_left(event):
        shutdown_mode = 0
        shutdown_time = 0.0
        return radarmodes.first_mode_sequence()
    if is_middle(event):
        shutdown_mode = 1
        shutdown_time = 0.0
        return Modes.SHUTDOWN
    if is_right(event):
        shutdown_mode = 2
        shutdown_time = 0.0
        return Modes.SHUTDOWN
    return Modes.SHUTDOWN
