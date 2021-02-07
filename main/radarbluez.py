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


import re
import pydbus
import logging
from espeakng import ESpeakNG

# DBus object paths
BLUEZ_SERVICE = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'

# global variables
bus = None
manager = None
adapter = None
esng = None
bluetooth_active = False
bt_devices = 0          # no of active bluetooth devices last time checked via connected devices


def bluez_init():
    global bus
    global manager
    global adapter
    global esng
    global bluetooth_active
    global bt_devices

    bus = pydbus.SystemBus()
    if bus is None:
        logging.debug("Systembus not received")
        return
    try:
        manager = bus.get(BLUEZ_SERVICE, '/')
        adapter = bus.get(BLUEZ_SERVICE, ADAPTER_PATH)
    except (KeyError, TypeError):
        logging.debug("Bluetooth: BLUEZ-SERVICE not initialised")
        return
    bluetooth_active = True
    connected_devices()     # check if already devices are connected
    if esng is None:
        esng = ESpeakNG(voice='en-us', pitch=30, speed=175)
        if esng is None:
            logging.info("Bluetooth: espeak-ng not initialized")
            return
        logging.info("Bluetooth: espeak-ng successfully initialized.")
    esng.say("Stratux Radar connected")
    print("SPEAK: Stratux Radar connected")


def speak(text):
    global esng

    if bluetooth_active and bt_devices > 0:
        if esng is None:   # first initialization failed
            esng = ESpeakNG(voice='en-us', pitch=30, speed=175)
            if esng is None:
                logging.info("Bluetooth: espeak-ng not initialized")
                return
            logging.info("Bluetooth: espeak-ng successfully initialized.")
        esng.say(text)
        logging.debug("Bluetooth speak: "+text)


def connected_devices():
    global manager
    global bt_devices

    if not bluetooth_active:
        return
    managed_objects = manager.GetManagedObjects()
    r = re.compile('\/org\/bluez\/hci\d*\/dev_(.*)')
    # to match strings like /org/bluez/hci0/dev_58_C9_35_2F_A1_EF
    device_names = []
    for key, value in managed_objects.items():
        m = r.match(key)
        if m is not None:
            if 'org.bluez.Device1' in value:
                if value['org.bluez.Device1']['Connected']:
                    device_names.append(value['org.bluez.Device1']['Name'])
    bt_devices = len(device_names)
    return bt_devices, device_names
