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
# from espeakng import ESpeakNG
import subprocess
import alsaaudio
from queue import Queue
import threading    # for espeak-ng, so that there is no blocking of other sensor functions during that time


# DBus object paths
BLUEZ_SERVICE = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'

# global variables
rlog = None
bus = None
manager = None
adapter = None
bluetooth_active = False
extsound_active = False
bt_devices = 0          # no of active bluetooth devices last time checked via connected devices
mixer = None
global_config = None
sound_queue = None    # external sound queue
sound_thread = None
sound_card = None     # number of sound card, is initialized if external_sound_output is True

def find_mixer(mixer_name):    # searches for an "Audio" mixer, independent whether it was selected
    found = False
    mix = None
    cardno = 0
    kwargs = {}
    for cardno in alsaaudio.card_indexes():
        kwargs = {'cardindex': cardno}
        for m in alsaaudio.mixers(**kwargs):
            rlog.debug("Audio: Available Card:" + alsaaudio.card_name(cardno)[0] + " Mixer: " + m)
            if m == mixer_name:
                rlog.debug("Audio: Selected Mixer:" + alsaaudio.card_name(cardno)[0] + " Mixer: " + m)
                found = True
                break
        if found:   # stop outer loop as well, if first suitable mixer is found
            break
    if not found:
        return -1, None

    try:
        mix = alsaaudio.Mixer(mixer_name, **kwargs)
    except alsaaudio.ALSAAudioError:
        rlog.debug("Radarbluez: Could not get mixer '" + mixer_name + "'")
    rlog.debug("Radarbluez: Mixer '" + mixer_name + "' selected")
    return cardno, mix


def sound_init(config, bluetooth, mixer_name):
    global bluetooth_active
    global extsound_active
    global mixer
    global sound_queue
    global sound_thread
    global sound_card
    global rlog
    global global_config

    extsound_active = False
    bluetooth_active = False
    global_config = config
    rlog = logging.getLogger('stratux-radar-log')
    sound_card, mixer = find_mixer(mixer_name)   # search for mixer in any case
    if not mixer:
        rlog.debug("Radarbluez: Mixer not found!")
    else:
        mixer.setvolume(global_config['sound_volume'])
        extsound_active = True
        rlog.debug("Radarbluez: Setting ExtSound to " + str(global_config['sound_volume']))
    if bluetooth:
        bluetooth_active = bluez_init()

    if bluetooth_active or extsound_active:
        sound_queue = Queue()
        sound_thread = threading.Thread(target=audio_speaker, args=(sound_queue,))  # external thread that speaks
        sound_thread.start()
        speak("Stratux Radar connected")
    rlog.debug("SoundInit: Bluetooth active:" + str(bluetooth_active) + " ExtSound active: " + str(extsound_active) +
               " ExtSound volume: " + str(global_config['sound_volume']) + ".")
    return extsound_active, bluetooth_active


def sound_terminate():
    if sound_queue:
        sound_queue.put('STOP')
    if sound_thread:
        sound_thread.join()    # wait for termination


def bluez_init():
    global bus
    global manager
    global adapter
    global bluetooth_active

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
    if mixer is not None:
        mixer.setvolume(new_volume)


def speak(text):
    if (extsound_active and global_config['sound_volume'] > 0) or (bluetooth_active and bt_devices > 0):
        sound_queue.put(text)
    rlog.debug("Speak: "+text)


def audio_speaker(queue):
    rlog.debug("Radarbluez: Audio-Speaker thread active.")
    while True:
        msg = queue.get()
        if msg == 'STOP':
            break
        else:
            pico_result = subprocess.run(["pico2wave", "-w", "/tmp/radar.wav", msg])  # generate wave
            if pico_result.returncode == 0:
                if bluetooth_active and bt_devices > 0:
                    aplay_result = subprocess.Popen(["aplay", "/tmp/radar.wav"])
                    if aplay_result.returncode != 0:
                        rlog.debug("Radarbluez: Error running aplay for bluetooth")
                if extsound_active and global_config['sound_volume'] > 0:
                    deviceopt = "--device=plughw:" + str(sound_card)
                    aplay_result = subprocess.Popen(["aplay", deviceopt, "/tmp/radar.wav"])
                    if aplay_result.returncode != 0:
                        rlog.debug("Radarbluez: Error running aplay {0}.".format(deviceopt))
            else:
                rlog.debug("Radarbluez: Error using pico2wave TTS")
    rlog.debug("Radarbluez: Sound-Speaker thread terminated.")


def connected_devices():
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
    res = subprocess.run(["bluetoothctl", "pair", bt_addr])
    if res.returncode != 0:
        rlog.debug("Bluetooth: pair failed for adr " + str(bt_addr))
        return False
    res = subprocess.run(["bluetoothctl", "connect", bt_addr])
    if res.returncode != 0:
        rlog.debug("Bluetooth: pair failed for adr " + str(bt_addr))
        return False
    res = subprocess.run(["bluetoothctl", "trust", bt_addr])
    # trust made at the end due to strange behaviour of bluez
    if res.returncode != 0:
        rlog.debug("Bluetooth: trust failed for adr " + str(bt_addr))
        return False
    return True