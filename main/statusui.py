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
STATUS_TIMEOUT = 0.3
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
status_mode = 0     # 0 = normal, 1 = scan running, 2 = scan evaluation


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
    global status_mode
    global last_status_get
    global left
    global middle
    global right
    global scan_end

    display_control.clear(draw)
    now = time.time()
    if status_mode == 0:
        if now >= last_status_get + STATUS_TIMEOUT:
            last_status_get = now
        status_answer = get_status()
        bt_devices, devnames = radarbluez.connected_devices()
        display_control.status(draw, status_answer, left, middle, right, stratux_ip, bt_devices, devnames)
    elif status_mode == 1:   # scan running
        countdown = math.floor(scan_end - now)
        if countdown > 0:
            headline = "BT-Scan"
            subline = str(countdown) + " secs"
            text = ""
            display_control.bt_scanning(draw, headline, subline, text, left, middle, right)
        else:
            status_mode = 2
    elif status_mode == 2:   # scan evaluation
        headline = "BT-Scan"
        subline = "finished."
        text = str(len(new_devices)) + " new devices found: \n"
        if len(new_devices) > 0:
            text += "Connect?\n"
            text += new_devices[0][1]
            left = "YES"
            middle = "Cancel"
            right = "NO"
        else:
            left = ""
            middle = "Cont"
            right = "Scan"
            text += "No detections."
        display_control.bt_scanning(draw, headline, subline, text, left, middle, right)
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


def remove_device(bt_addr):
    res = subprocess.run(["bluetoothctl", "remove", bt_addr])
    if res.returncode != 0:
        return False


def scan_result(output):
    global new_devices

    lines = output.splitlines()
    for line in lines:
        split = line.split(maxsplit=3)
        if len(split) >= 2:
            if 'NEW' in split[0] and 'Device' in split[1]:
                bt_addr = split[2]
                if len(split) >= 3:
                    bt_name = split[3]
                else:
                    bt_name = ''
                new_devices.append([bt_addr, bt_name])
                logging.debug("BT-Scan: new Device detected ", bt_addr, " ", bt_name)


async def bt_scan():
    logging.debug("Starting Bluetooth-Scan")
    proc = await asyncio.create_subprocess_exec("bluetoothctl", "--timeout", str(BLUETOOTH_SCAN_TIME), "scan", "on",
                                                stdout=asyncio.subprocess.PIPE)
    while True:
        stdout_line, stderr_line = await proc.communicate()
        if proc is not None:   # finished
            scan_result(stdout_line.decode("UTF-8"))
            logging.debug("Blueotooth Scan done")
            return   # subprocess done
        scan_result(stdout_line.decode("UTF-8"))
        await asyncio.sleep(BT_SCAN_WAIT)


def start_async_bt_scan():   # started by ui-coroutine
    loop = asyncio.get_event_loop()
    loop.create_task(bt_scan())


def user_input(bluetooth_active):
    global left
    global middle
    global right
    global scan_end
    global status_mode
    global new_devices

    if status_mode == 0:
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
    if status_mode == 0:
        if bluetooth_active and button == 2 and btime == 1:  # right and short
            status_mode = 1
            left = ""
            middle = ""
            right = ""
            start_async_bt_scan()
            scan_end = time.time() + BLUETOOTH_SCAN_TIME
    if status_mode == 1:   # active scanning, no interface options, just wait
        pass
    if status_mode == 2:  # scanning finished, evaluating
        if len(new_devices) == 0:   # device mgmt finished
            if bluetooth_active and button == 2 and btime == 1:  # right and short
                status_mode = 1
                left = ""
                middle = ""
                right = ""
                start_async_bt_scan()
                scan_end = time.time() + BLUETOOTH_SCAN_TIME
                return 7
        if len(new_devices) > 0:
            if button == 0 and btime == 1:  # left short, YES
                print("Connecting:", new_devices[0][1])
                trust_pair_connect(new_devices[0][0])
                del new_devices[0]
            if button == 2 and btime == 1:  # right short, NO
                print("Not Connecting:", new_devices[0][1])
                remove_device(new_devices[0][0])
                del new_devices[0]
        if len(new_devices)==0 or (button == 1 and btime == 1):   # middle short, Cancel
            new_devices = []
            left = ""
            middle = "Mode"
            right = "Scan"
            status_mode = 0
    return 7  # no mode change
