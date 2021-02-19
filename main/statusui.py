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
import radarbluez
import math
import asyncio
import subprocess

# constants
STATUS_TIMEOUT = 0.5
BLUETOOTH_SCAN_TIME = 15.0
BT_SCAN_WAIT = 0.2

# globals
status_url = ""
stratux_ip = "0.0.0.0"
last_status_get = 0.0  # time stamp of the last status request
left = ""           # button text
middle = ""         # button text
right = ""          # button text
scan_end = 0.0      # time, when a bt scan will be finished
new_devices = []


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
    except (requests.exceptions.RequestException, ValueError) as e:
        logging.debug("Status UI: Status GET exception", e)
        return None
    return status_answer


def draw_status(draw, display_control):
    global scan_end
    global last_status_get

    now = time.time()
    if now >= last_status_get + STATUS_TIMEOUT:
        last_status_get = now

        display_control.clear(draw)
        if scan_end == 0:
            status_answer = get_status()
            bt_devices, devnames = radarbluez.connected_devices()
            display_control.status(draw, status_answer, left, middle, right, stratux_ip, bt_devices, devnames)
        else:
            countdown = math.floor(scan_end - now)
            if countdown > 0:
                display_control.bt_scanning(draw, countdown, new_devices)
            else:
                scan_end = 0
        display_control.display()


def trust_pair_connect(bt_addr):
    res = subprocess.run(["bluetoothctl", "trust", bt_addr])
    if res.returncode != 0:
        return False
    res = subprocess.run(["bluetoothctl", "pair", bt_addr])
    if res.returncode != 0:
        return False
    res = subprocess.run(["bluetoothctl", "connect", bt_addr])
    if res.returncode != 0:
        return False
    return True


def scan_result(line):
    global new_devices

    print("Scan result: ", line)
    split = line.split(maxsplit=2)
    if len(split) >= 2:
        if split[0] == '[NEW]' and split[1] == 'Device':
            bt_addr = split[2]
            bt_name = split[3]
            new_devices.append([bt_addr, bt_name])


async def bt_scan():
    print("Starting Bluetooth-Scan")
    proc = await asyncio.create_subprocess_exec("bluetoothctl", "--timeout", str(BLUETOOTH_SCAN_TIME), "scan", "on",
                                                stdout=asyncio.subprocess.PIPE)
    while True:
        stdout_line, stderr_line = await proc.communicate()
        print("Communicate: RetCod ", proc.returncode, " stdout ", stdout_line)
        if proc is not None:   # finished
            scan_result(stdout_line)
            print("Blueotooth Scan Off")
            subprocess.run(["bluetoothctl", "scan", "off"])
            return   # subprocess done
        scan_result(stdout_line)
        await asyncio.sleep(BT_SCAN_WAIT)


def start_async_bt_scan():   # started by ui-coroutine
    loop = asyncio.get_event_loop()
    loop.create_task(bt_scan())


def user_input(bluetooth_active):
    global left
    global middle
    global right
    global scan_end

    middle = "Mode"
    if bluetooth_active:
        right = "Scan"
    else:
        right = ""
    btime, button = radarbuttons.check_buttons()
    # start of ahrs global behaviour
    if btime == 0:
        return 0  # stay in timer mode
    if button == 1 and btime == 2:  # middle and long
        return 1  # next mode to be radar
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if bluetooth_active and button == 2 and btime == 1:  # right and short
        start_async_bt_scan()
        scan_end = time.time() + BLUETOOTH_SCAN_TIME
        return 7  # stay in status mode
    if button == 2 and btime == 2:  # right and long- refresh
        return 6  # start next mode for display driver: refresh called from ahrs
    return 7  # no mode change
