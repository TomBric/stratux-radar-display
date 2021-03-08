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
import string
import ipaddress
import json

# constants
CONFIG_FILE = "stratux-radar.conf"
STATUS_TIMEOUT = 0.3
BLUETOOTH_SCAN_TIME = 30.0
BT_SCAN_WAIT = 0.2
CHARSET = " " + string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation
NUMBERS = string.digits
DEFAULT_WIFI = "stratux         "
DEFAULT_PASS = "                "
MAX_WIFI_LENGTH = 16

# globals
global_config = {'stratux_ip': "192.168.10.1", }
status_url = ""
stratux_ip = "0.0.0.0"
last_status_get = 0.0  # time stamp of the last status request
left = ""           # button text
middle = ""         # button text
right = ""          # button text
scan_end = 0.0      # time, when a bt scan will be finished
new_devices = []
status_mode = 0
# 0 = normal, 1 = scan running, 2 = scan evaluation, 3-network display, 4-network set ssid 5-network set passw
wifi_ssid = ""
refresh_time = 0.0
new_wifi = DEFAULT_WIFI
new_pass = DEFAULT_PASS
new_stratux_ip = stratux_ip
charpos = 0         # position of current input char


def read_config():
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except (OSError, IOError, ValueError) as e:
        logging.debug("StatusUI: Error " + str(e) + " reading " + CONFIG_FILE)
        return None
    logging.debug("StatusUI: Configuration saved to " + CONFIG_FILE + ": " +
                  json.dumps(config, sort_keys=True, indent=4))
    return config


def write_config(config):
    try:
        with open(CONFIG_FILE, 'wt') as out:
            json.dump(config, out, sort_keys=True, indent=4)
    except (OSError, IOError, ValueError) as e:
        logging.debug("StatusUI: Error " + str(e) + " writing " + CONFIG_FILE)
    logging.debug("StatusUI: Configuration read from " + CONFIG_FILE + ": " +
                  json.dumps(config, sort_keys=True, indent=4))


def init(display_control, url, target_ip, refresh):   # prepare everything
    global status_url
    global stratux_ip
    global refresh_time

    status_url = url
    stratux_ip = target_ip
    logging.debug("Status UI: Initialized GET settings to " + status_url)
    refresh_time = refresh


def get_status():
    global status_url

    try:
        answer = requests.get(status_url)
        status_answer = answer.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        logging.debug("Status UI: Status GET exception", e)
        return None
    return status_answer


def draw_status(draw, display_control, bluetooth_active):
    global status_mode
    global last_status_get
    global left
    global middle
    global right
    global scan_end
    global new_wifi
    global new_pass
    global stratux_ip

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
        display_control.text_screen(draw, "Status", None, status_text, "Netw", "Mode", right)
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
        display_control.text_screen(draw, "WIFI Info", "", "WIFI SSID:\n" + wifi_ssid + "\nStratux-IP:\n" + stratux_ip,
                                    "", "Cont", "Chg")
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
    elif status_mode == 6:   # "yes" or "no"
        headline = "Change WIFI"
        subline = "Confirm & reboot"
        text = "SSID: " + new_wifi + "\nPass: " + new_pass \
               + "\nStrx: " + new_stratux_ip
        display_control.text_screen(draw, headline, subline, text, "YES", "", "NO")
    elif status_mode == 7:   # input of stratux-ip
        headline = "Change WIFI"
        subline = "Stratux IP Addr"
        text = "Enter IP of Stratux:\n"
        prefix = new_stratux_ip[0:charpos]
        char = new_stratux_ip[charpos]
        suffix = new_stratux_ip[charpos + 1:len(new_stratux_ip)]
        display_control.screen_input(draw, headline, subline, text, "+", "Next/Fin", "-", prefix, char, suffix)
    elif status_mode == 10:   # Error dispay
        headline = "Change WIFI"
        subline = "Input Error!"
        ip_is_invalid = False
        try:
            ipaddress.ip_address(new_stratux_ip)
        except ValueError:
            ip_is_invalid = True
        if len(new_wifi) == 0:
            text = "SSID invalid"
        elif 0 < len(new_pass) <= 8:
            text = "Passphrase too\nshort (none\nor min 8 char)"
        elif ip_is_invalid:
            text = "Stratux IP invalid"
        else:
            text = "unspecified error"
        display_control.text_screen(draw, headline, subline, text, "Canc", "", "Redo")
    elif status_mode == 11:   # REBOOT DISPLAY
        headline = "Rebooting"
        subline = "Please wait ..."
        text = "New network\nconfig applied."
        display_control.text_screen(draw, headline, subline, text, "", "", "")
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


def read_network():
    res = subprocess.run(["sudo", "wpa_cli", "list_networks"], encoding="UTF-8", capture_output=True)
    if res.returncode != 0:
        return ""
    lines = res.stdout.splitlines()
    if len(lines) >= 2:
        line2 = lines[2].split()
    else:
        return ""
    if len(line2) >= 1:
        ssid = line2[1]
        return ssid
    else:
        return ""


async def set_network(wifi, passw, new_stratux):
    global global_config

    global_config['stratux_ip'] = new_stratux
    write_config(global_config)
    res = subprocess.run(["sudo", "raspi-config", "nonint", "do_wifi_ssid_passphrase", wifi, passw])
    if res != 0:
        logging.debug("STATUSUI: Setting Wifi network failed.")
        return
    # wait a second to give the display driver time for a goodbye message
    await asyncio.sleep(1)
    res = subprocess.run(["sudo", "reboot"])
    if res != 0:
        logging.debug("STATUSUI: Reboot attempt failed.")


def next_char(current):
    return CHARSET[(CHARSET.find(current) + 1) % len(CHARSET)]


def prev_char(current):
    pos = CHARSET.find(current) - 1
    if pos < 0:
        pos = len(CHARSET)-1
    return CHARSET[pos]


def next_number(current):
    return NUMBERS[(NUMBERS.find(current) + 1) % len(NUMBERS)]


def prev_number(current):
    pos = NUMBERS.find(current) - 1
    if pos < 0:
        pos = len(NUMBERS)-1
    return NUMBERS[pos]


def ipv4_to_string(ip):   # generate string with leading zeros
    s = str((int(ip) >> 24) % 256,).zfill(3) + "." + str((int(ip) >> 16) % 256).zfill(3) + "." \
        + str((int(ip) >> 8) % 256).zfill(3) + "." + str(int(ip) % 256).zfill(3)
    return s


def string_to_ipv4(ipv4str):
    parts = ipv4str.split('.')
    ipaddr = (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
    return ipaddr


def user_input(bluetooth_active):
    global left
    global middle
    global right
    global scan_end
    global status_mode
    global new_devices
    global wifi_ssid
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
    if btime == 0:
        return 0  # stay in timer mode
    if button == 1 and btime == 2 and status_mode != 4 and status_mode != 5 and status_mode != 7:  # middle and long
        return 1  # next mode to be radar
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if status_mode == 0:   # normal status display
        if bluetooth_active and button == 2 and btime == 1:  # right and short
            status_mode = 1
            start_async_bt_scan()
            scan_end = time.time() + BLUETOOTH_SCAN_TIME
        if button == 0 and btime == 1:  # left and short, network config
            status_mode = 3
            wifi_ssid = read_network()
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
                logging.debug("Connecting:", new_devices[0][1])
                trust_pair_connect(new_devices[0][0])
                del new_devices[0]
            if button == 2 and btime == 1:  # right short, NO
                logging.debug("Not Connecting:", new_devices[0][1])
                remove_device(new_devices[0][0])
                del new_devices[0]
        if len(new_devices) == 0 or (button == 1 and btime == 1):   # middle short, Cancel
            new_devices = []
            status_mode = 0
    elif status_mode == 3:  # network display
        if button == 2 and btime == 1:  # right and short, change network config
            charpos = 0
            if wifi_ssid != "":
                new_wifi = wifi_ssid.ljust(MAX_WIFI_LENGTH)
            else:
                new_wifi = DEFAULT_WIFI
            new_pass = DEFAULT_PASS
            new_stratux_ip = stratux_ip
            status_mode = 4
        if button == 1 and btime == 1:  # middle and short, go back to normal status
            status_mode = 0
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
            new_wifi = new_wifi.strip()
            new_pass = new_pass.strip()
            if len(new_wifi) > 0 and (len(new_pass) == 0 or len(new_pass) >= 8):
                new_stratux_ip = ipv4_to_string(string_to_ipv4(stratux_ip))  # to normalize and have leading zeros
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
            set_network(new_wifi, new_pass, new_stratux_ip)
            stratux_ip = new_stratux_ip
            status_mode = 11
    elif status_mode == 7:   # input stratux_ip
        if button == 0 and btime == 1:  # left and short, +
            new_stratux_ip = new_stratux_ip[:charpos] + next_number(new_stratux_ip[charpos]) \
                             + new_stratux_ip[charpos+1:]
        if button == 2 and btime == 1:  # left and short, +
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
            new_wifi = DEFAULT_WIFI
            new_pass = DEFAULT_PASS
            new_stratux_ip = stratux_ip
            charpos = 0
            status_mode = 4   # change network
        if button == 0 and btime == 1:  # left and short, "cancel"
            new_wifi = DEFAULT_WIFI
            new_pass = DEFAULT_PASS
            new_stratux_ip = stratux_ip
            status_mode = 3  # display network
    return 7  # no mode change
