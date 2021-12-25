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
import subprocess
import alsaaudio

# DBus object paths
BLUEZ_SERVICE = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'
MIXERNAME = "Speaker"     # this is the name, when you plug in a usb device

# global variables
rlog = None
bus = None
manager = None
adapter = None
esng = None
bluetooth_active = False
extsound_active = False
bt_devices = 0          # no of active bluetooth devices last time checked via connected devices
mixer = None
cardno = -1         # cardno where "Speaker" was detected, on Pi3B with USB typically 1

def find_mixer():    # searches for a "Audio" mixer, independent whether it was selected
    found = False
    kwargs = {}
    for cardno in alsaaudio.card_indexes():
        kwargs = {'cardindex': cardno}
        for m in alsaaudio.mixers(**kwargs):
            rlog.debug("Audio: Available Card:" + alsaaudio.card_name(cardno)[0] + " Mixer: " + m)
            if m == MIXERNAME:
                rlog.debug("Audio: Selected Mixer:" + alsaaudio.card_name(cardno)[0] + " Mixer: " + m)
                found = True
                break
    if not found:
        return None

    try:
        mix = alsaaudio.Mixer(MIXERNAME, **kwargs)
    except alsaaudio.ALSAAudioError:
        rlog.debug("Radarbluez: Could not get mixer '" + MIXERNAME + "'")
    rlog.debug("Radarbluez: Mixer '" + MIXERNAME + "' selected")
    return mix


def sound_init(config, bluetooth):
    global bluetooth_active
    global extsound_active
    global esng
    global mixer
    global cardno
    global rlog

    extsound_active = False
    bluetooth_active = False
    rlog = logging.getLogger('stratux-radar-log')
    mixer = find_mixer()   # search for mixer in any case
    if mixer and config['sound_volume']>=0 :
        mixer.setvolume(config['sound_volume'])
        extsound_active = True
        rlog.debug("Radarbluez: Setting ExtSound to " + str(config['sound_volume']))
    elif mixer and config['sound_volume'] == -1:   # audio device and mixer found, but no speaker selected
        mixer.setvolume(0)
        extsound_active = False
        rlog.debug("Radarbluez: Setting ExtSound to " + str(config['sound_volume']))
    if bluetooth:
        bluetooth_active = bluez_init()

    if extsound_active or bluetooth_active:
        if esng is None:
            if bluetooth_active:
                esng = ESpeakNG(voice='en-us', pitch=30, speed=175)  # pulseaudio then also uses speaker output
            elif extsound_active:
                audio = "plughw:" + str(cardno)
                esng = ESpeakNG(voice='en-us', pitch=30, speed=175, audio_dev="audio")
            if esng is None:   # could not initialize esng
                extsound_active = False
                bluetooth_active = False
                rlog.debug("Radarbluez: espeak-ng not initialized")
                return extsound_active, bluetooth_active
        rlog.debug("Radarbluez: espeak-ng successfully initialized.")
        esng.say("Stratux Radar connected")
        rlog.debug("SPEAK: Stratux Radar connected")

    rlog.debug("SoundInit: Bluetooth active:" + str(bluetooth_active) + " ExtSound active: " + str(extsound_active) +
               " ExtSound volume: " + str(config['sound_volume']) + ".")
    return extsound_active, bluetooth_active


def bluez_init():
    global bus
    global manager
    global adapter
    global bluetooth_active
    global bt_devices
    global rlog

    bus = pydbus.SystemBus()

    if bus is None:
        rlog.debug("Systembus not received")
        return False
    try:
        manager = bus.get(BLUEZ_SERVICE, '/')
        adapter = bus.get(BLUEZ_SERVICE, ADAPTER_PATH)
    except (KeyError, TypeError):
        rlog.debug("Bluetooth: BLUEZ-SERVICE not initialised")
        return False
    bluetooth_active = True
    rlog.debug("Bluetooth: BLUEZ-SERVICE successfully activated.")
    connected_devices()     # check if already devices are connected
    return True


def setvolume(new_volume):
    global mixer
    mixer.setvolume(new_volume)


def speak(text):
    global esng
    global extsound_active

    if extsound_active or (bluetooth_active and bt_devices > 0):
        if esng is None:   # first initialization failed, may happen with bluetooth, try again
            esng = ESpeakNG(voice='en-us', pitch=30, speed=175)
            if esng is None:
                rlog.debug("Radarbluez: espeak-ng not initialized")
                return
            rlog.debug("Radarbluez: espeak-ng successfully initialized.")
        esng.say(text)
        rlog.debug("Speak: "+text)


def connected_devices():
    global manager
    global bt_devices

    if not bluetooth_active:
        return 0, []
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
