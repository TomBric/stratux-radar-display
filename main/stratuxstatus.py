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
import string
import ipaddress
import json


# constants

# globals
status = {}
status_url = ""
rlog = None

def init(display_control, url):   # prepare everything
    global status_url
    global rlog

    status_url = url
    rlog = logging.getLogger('stratux-radar-log')
    rlog.debug("StratuxStatus UI: Initialized with URL "+ status_url)

def start():  # start listening on status websocket
    pass


def stop(): # stop listening on status websocket



def draw_stratux(draw, display_control):
    global status

    display_control.clear(draw)
    now = time.time()
    if status_mode == 0:
        # if now >= last_status_get + STATUS_TIMEOUT:
        #    last_status_get = now
        # status_answer = get_status()  not used for now
        status_text = "Strx: " + format(stratux_ip) + "\n"
        status_text += "DispRefresh: " + str(round(refresh_time, 2)) + " s\n"
        bt_devices, bt_names = radarbluez.connected_devices()
        if bt_devices is not None:
            status_text += "BT-Devices: " + str(bt_devices) + "\n"
        if bt_names is not None:
            for name in bt_names:
                status_text += " " + name + "\n"
        if bluetooth_active:
            right = "Scan"
        else:
            right = ""
        display_control.text_screen(draw, "Display Status", None, status_text, "Netw", "Mode", right)
    elif status_mode == 1:   # scan running
        countdown = math.floor(scan_end - now)
        if countdown > 0:
            subline = str(countdown) + " secs"
            display_control.text_screen(draw, "BT-Scan", subline, "", "", "", "")
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
        display_control.text_screen(draw, headline, subline, text, left, middle, right)
    elif status_mode == 3:  # display network information
        display_control.text_screen(draw, "WIFI Info", "", "WIFI SSID:\n" + wifi_ssid + "\nStratux-IP:\n" + stratux_ip
                                    + "\nMyIP:" + wifi_ip, "Opt", "Cont", "Chg")
    elif status_mode == 4:  # change network settings
        headline = "Change WIFI"
        subline = "WIFI SSID"
        text = "Enter SSID:\n"
        prefix = new_wifi[0:charpos]
        char = new_wifi[charpos]
        suffix = new_wifi[charpos+1:len(new_wifi)]
        display_control.screen_input(draw, headline, subline, text, "+", "Next/Fin", "-", prefix, char, suffix)
    elif status_mode == 5:   # change password
        headline = "Change WIFI"
        subline = "Password"
        text = "Enter Password\n(none or min 8):"
        prefix = new_pass[0:charpos]
        char = new_pass[charpos]
        suffix = new_pass[charpos + 1:len(new_pass)]
        display_control.screen_input(draw, headline, subline, text, "+", "Next/Fin", "-", prefix, char, suffix)



        text = "Passphrase too\nshort (none\nor min 8 char)"
        display_control.text_screen(draw, headline, subline, text, "YES", "", "NO")


def status_callback():
    rlog.debug("Status listener running ...")


def start_websocket_listener():   # started by ui-coroutine
    loop = asyncio.get_event_loop()
    loop.create_task(radar.listen_forever(status_url, "StatusListener",status_callback))


def user_input(bluetooth_active):
    global left
    global middle
    global right
    global scan_end
    global status_mode
    global new_devices
    global wifi_ssid
    global wifi_ip
    global new_wifi
    global new_pass
    global charpos
    global new_stratux_ip
    global stratux_ip

    if status_mode == 0:
        middle = "Mode"
        left = "Netw"
        if bluetooth_active:
            right = "Scan"
        else:
            right = ""
    btime, button = radarbuttons.check_buttons()
    # start of ahrs global behaviour
    if btime == 0 and status_mode != 11:   # for 11 do reboot
        return 0  # stay in current mode
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if status_mode == 0:   # normal status display
        if button == 1 and (btime == 2 or btime == 1): # middle
            return 1  # next mode to be radar
        if bluetooth_active and button == 2 and btime == 1:  # right and short
            status_mode = 1
            start_async_bt_scan()
            scan_end = time.time() + BLUETOOTH_SCAN_TIME
        if button == 0 and btime == 1:  # left and short, network config
            status_mode = 3
            wifi_ssid = read_network()
            wifi_ip = read_wlanip()
            if wifi_ssid != "":
                new_wifi = wifi_ssid.ljust(MAX_WIFI_LENGTH)
    elif status_mode == 1:   # active scanning, no interface options, just wait
        pass
    elif status_mode == 2:  # scanning finished, evaluating
        if len(new_devices) == 0:   # device mgmt finished
            if bluetooth_active and button == 2 and btime == 1:  # right and short
                status_mode = 1
                start_async_bt_scan()
                scan_end = time.time() + BLUETOOTH_SCAN_TIME
                return 7
        if len(new_devices) > 0:
            if button == 0 and btime == 1:  # left short, YES
                rlog.debug("Connecting:", new_devices[0][1])
                trust_pair_connect(new_devices[0][0])
                del new_devices[0]
            if button == 2 and btime == 1:  # right short, NO
                rlog.debug("Not Connecting:", new_devices[0][1])
                remove_device(new_devices[0][0])
                del new_devices[0]
        if len(new_devices) == 0 or (button == 1 and btime == 1):   # middle short, Cancel
            new_devices = []
            status_mode = 0
    elif status_mode == 3:  # network display
        if button == 2 and btime == 1:  # right and short, change network config
            charpos = 0
            status_mode = 4
        if button == 1 and btime == 1:  # middle and short, go back to normal status
            status_mode = 0
        if button == 0 and btime == 1:  # left and short, go to options
            status_mode = 12
    elif status_mode == 4:  # change network
        if button == 0 and btime == 1:  # left and short, +
            new_wifi = new_wifi[:charpos] + next_char(new_wifi[charpos]) + new_wifi[charpos+1:]
        if button == 1 and btime == 1:  # middle and short, next charpos
            charpos += 1
            if charpos >= len(new_wifi):
                charpos = 0
                status_mode = 5
        if button == 1 and btime == 2:  # middle and long finish
            charpos = 0
            status_mode = 5
        if button == 2 and btime == 1:  # right and short, -
            new_wifi = new_wifi[:charpos] + prev_char(new_wifi[charpos]) + new_wifi[charpos+1:]
    elif status_mode == 5:  # change wifi PSK
        if button == 0 and btime == 1:  # left and short, +
            new_pass = new_pass[:charpos] + next_char(new_pass[charpos]) + new_pass[charpos+1:]
        if button == 1 and btime == 1:  # middle and short, next charpos
            charpos += 1
            if charpos >= len(new_pass):
                charpos = 0
                status_mode = 7
        if button == 1 and btime == 2:  # middle and long finish
            check_wifi = new_wifi.strip()
            check_new_pass = new_pass.strip()
            if len(check_wifi) > 0 and (len(check_new_pass) == 0 or len(check_new_pass) >= 8):
                charpos = 0
                status_mode = 7
            else:
                status_mode = 10   # invalid input, go back to error display
        if button == 2 and btime == 1:  # right and short, -
            new_pass = new_pass[:charpos] + prev_char(new_pass[charpos]) + new_pass[charpos+1:]
    elif status_mode == 6:  # check yes/no
        if button == 2 and btime == 1:  # right and short, "No"
            status_mode = 3
        elif button == 0 and btime == 1:  # left and short, "yes"
            status_mode = 11
    elif status_mode == 7:   # input stratux_ip
        if button == 0 and btime == 1:  # left and short, +
            new_stratux_ip = new_stratux_ip[:charpos] + next_number(new_stratux_ip[charpos]) \
                             + new_stratux_ip[charpos+1:]
        if button == 2 and btime == 1:  # left and short, -
            new_stratux_ip = new_stratux_ip[:charpos] + prev_number(new_stratux_ip[charpos]) \
                             + new_stratux_ip[charpos+1:]
        if button == 1 and btime == 1:  # middle and short, next charpos
            charpos += 1
            if charpos >= len(new_stratux_ip):
                ip_is_invalid = False
                try:
                    ipaddress.IPv4Address(string_to_ipv4(new_stratux_ip))
                except ValueError:
                    ip_is_invalid = True
                charpos = 0
                if not ip_is_invalid:
                    status_mode = 6
                else:
                    status_mode = 10
            elif charpos == 3 or charpos == 7 or charpos == 11:
                charpos += 1   # skip "."
        if button == 1 and btime == 2:  # middle and long finish
            ip_is_invalid = False
            try:
                ipaddress.IPv4Address(string_to_ipv4(new_stratux_ip))
            except ValueError:
                ip_is_invalid = True
            charpos = 0
            if not ip_is_invalid:
                status_mode = 6
            else:
                status_mode = 10
    elif status_mode == 10:     # display error
        if button == 2 and btime == 1:  # right and short, "redo"
            charpos = 0
            status_mode = 4   # change network
        if button == 0 and btime == 1:  # left and short, "cancel"
            status_mode = 3  # display network
    elif status_mode == 11:  # reboot
        new_wifi = new_wifi.strip()
        new_pass = new_pass.strip()
        stratux_ip = str(ipaddress.IPv4Address(string_to_ipv4(new_stratux_ip)))   # to eliminate zeros
        set_network(new_wifi, new_pass, stratux_ip)
    elif status_mode == 12:  # Set Options Display Registration
        if button == 2 and btime == 1:  # No, do not display registration
            global_config['display_tail'] = False
            write_config(global_config)
            status_mode = 3
        if button == 0 and btime == 1:  # yes, do  display registration
            global_config['display_tail'] = True
            write_config(global_config)
            status_mode = 3
        if button == 1 and btime == 1:  # cancel
            status_mode = 3

    return 7  # no mode change
