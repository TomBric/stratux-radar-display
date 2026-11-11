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

from globals import rlog
import os
import time
import radarbluez
import math
import asyncio
import subprocess
import string
import json
import datetime
import tempfile
from radarmodes import Modes, next_mode_sequence
from button_input import get_button_event, is_left, is_left_short, is_left_long, is_middle, is_middle_short, is_middle_long, is_right, is_right_short, is_right_long

# constants
STATUS_TIMEOUT = 0.3
BLUETOOTH_SCAN_TIME = 30.0
BT_SCAN_WAIT = 0.2
CHARSET = " " + string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation
DEFAULT_WIFI = "stratux         "
DEFAULT_PASS = "                "
MAX_WIFI_LENGTH = 16

# global
bt_scan_task = None  # asyncio task for bluetooth scan

# globals
g_config_file = "undefined"   # filename of config file, set in init
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
wifi_ip = ""
refresh_time = 0.0
new_wifi = DEFAULT_WIFI
new_pass = DEFAULT_PASS
charpos = 0         # position of current input char

REMOVED_CONFIG_KEYS = frozenset({'stratux_ip', 'display_tail', 'distance_warnings', 'sound_volume'})


def default(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def read_config(config_file):
    try:
        with open(config_file) as f:
            config = json.load(f)
    except (OSError, IOError, ValueError) as e:
        rlog.debug("StatusUI: Error " + str(e) + " reading " + config_file)
        return None
    if not isinstance(config, dict):
        rlog.error("StatusUI: Configuration in %s is not a JSON object", config_file)
        return None
    if REMOVED_CONFIG_KEYS.intersection(config):
        config = {key: value for key, value in config.items() if key not in REMOVED_CONFIG_KEYS}
        try:
            save_config_file(config_file, config)
        except (OSError, ValueError, TypeError) as e:
            rlog.error("StatusUI: Could not remove obsolete settings from %s: %s", config_file, e)
    rlog.debug("StatusUI: Configuration read from " + config_file + ": " +
               json.dumps(config, sort_keys=True, indent=4, default=default))
    return config


def save_config_file(config_file, config):
    directory = os.path.dirname(os.path.abspath(config_file))
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory, delete=False) as out:
            temp_name = out.name
            json.dump(config, out, sort_keys=True, indent=4, default=default)
        if os.path.exists(config_file):
            os.chmod(temp_name, os.stat(config_file).st_mode & 0o777)
        os.replace(temp_name, config_file)
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)


def write_config(config):
    saved_config = {key: value for key, value in config.items() if key not in REMOVED_CONFIG_KEYS}
    try:
        save_config_file(g_config_file, saved_config)
        rlog.debug("StatusUI: Configuration saved to " + g_config_file + ": " + json.dumps(saved_config, sort_keys=True, indent=4,
                                                                                            default=default))
    except (OSError, ValueError, TypeError) as e:
        rlog.error("StatusUI: Error %s writing %s", e, g_config_file)


def init(config_file, url, target_ip, refresh):   # prepare everything
    global status_url
    global stratux_ip
    global refresh_time
    global new_pass
    global new_wifi
    global g_config_file

    g_config_file = config_file
    status_url = url
    stratux_ip = target_ip
    rlog.debug("Status UI: Initialized GET settings to " + status_url)
    refresh_time = refresh
    new_pass = DEFAULT_PASS
    new_wifi = DEFAULT_WIFI


def get_status():
    global status_url

    if not status_url:
        return None
    import requests

    try:
        answer = requests.get(status_url)
        status_answer = answer.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        rlog.debug("Status UI: Status GET exception", e)
        return None
    return status_answer


def draw_status(display_control, bluetooth_active, extsound_active):
    global status_mode
    global last_status_get
    global left
    global middle
    global right
    global scan_end

    display_control.clear()
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
        display_control.text_screen("Display Status", None, status_text, "Net", " Mode", right)
    elif status_mode == 1:   # scan running
        countdown = math.floor(scan_end - now)
        if countdown > 0:
            subline = str(countdown) + " secs"
            display_control.text_screen("BT-Scan", subline, "", "", "", "")
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
        display_control.text_screen(headline, subline, text, left, middle, right)
    elif status_mode == 3:  # display network information
        display_control.text_screen("WIFI Info", "", "WIFI SSID:\n" + wifi_ssid + "\nStratux-IP:\n" + stratux_ip
                                    + "\nMyIP:" + wifi_ip, "", "Cont", "Chg")
    elif status_mode == 4:  # change network settings
        headline = "Change WIFI"
        subline = "WIFI SSID"
        text = "Enter SSID:\n"
        prefix = new_wifi[0:charpos]
        char = new_wifi[charpos]
        suffix = new_wifi[charpos+1:len(new_wifi)]
        display_control.screen_input(headline, subline, text, "+", "Next/Fin", "-", prefix, char, suffix)
    elif status_mode == 5:   # change password
        headline = "Change WIFI"
        subline = "Password"
        text = "Enter Password\n(none or min 8):"
        prefix = new_pass[0:charpos]
        char = new_pass[charpos]
        suffix = new_pass[charpos + 1:len(new_pass)]
        display_control.screen_input(headline, subline, text, "+", "Next/Fin", "-", prefix, char, suffix)
    elif status_mode == 6:   # "yes" or "no"
        headline = "Change WIFI"
        subline = "Confirm & reboot"
        text = "SSID: " + new_wifi + "\nPass: " + new_pass
        display_control.text_screen(headline, subline, text, "YES", "", "NO")
    elif status_mode == 10:   # Error display
        headline = "Change WIFI"
        subline = "Input Error!"
        if len(new_wifi.strip()) == 0:
            text = "SSID invalid"
        elif 0 < len(new_pass.strip()) < 8:
            text = "Passphrase too\nshort (none\nor min 8 char)"
        else:
            text = "unspecified error"
        display_control.text_screen(headline, subline, text, "Canc", "", "Redo")
    elif status_mode == 11:   # REBOOT DISPLAY
        headline = "Rebooting"
        subline = "Please wait ..."
        text = "New network\nconfig applied."
        display_control.text_screen(headline, subline, text, "", "", "")
    display_control.display()


def remove_device(bt_addr):
    res = subprocess.run(["bluetoothctl", "remove", bt_addr])
    if res.returncode != 0:
        return False
    return True


def scan_result(output):
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
                rlog.debug("BT-Scan: new Device detected " + str(bt_addr) + " " + bt_name)


async def bt_scan():
    rlog.debug("Starting Bluetooth-Scan")
    proc = await asyncio.create_subprocess_exec("bluetoothctl", "--timeout", str(BLUETOOTH_SCAN_TIME),
                                                "scan", "on", stdout=asyncio.subprocess.PIPE)
    while True:
        try:
            stdout_line, stderr_line = await proc.communicate()
            if proc is not None:   # finished
                scan_result(stdout_line.decode("UTF-8"))
                rlog.debug("Blueotooth Scan done")
                return   # subprocess done
            scan_result(stdout_line.decode("UTF-8"))
            await asyncio.sleep(BT_SCAN_WAIT)
        except asyncio.CancelledError:
            rlog.debug("Bluetooth scan sleep cancelled")
            raise


def start_async_bt_scan():   # started by ui-coroutine
    global bt_scan_task
    loop = asyncio.get_event_loop()
    bt_scan_task = loop.create_task(bt_scan(), name="BT-Scan")

def stop_async_bt_scan():   # started by ui-coroutine
    if bt_scan_task is not None:
        bt_scan_task.cancel()


def read_network():
    res = subprocess.run(["sudo", "iwgetid", "--raw"], encoding="UTF-8", capture_output=True)
    if res.returncode != 0:
        return ""
    lines = res.stdout.splitlines()   # stdout delivers a CR at the end
    if len(lines) >= 1:
        ssid = lines[0]
        rlog.debug(f'Network ssid read via iwgetid: {ssid}')
        return ssid
    else:
        rlog.debug(f'No Network ssid read via iwgetid')
        return ""


def read_wlanip():
    res = subprocess.run(["sudo", "hostname", "-I"], encoding="UTF-8", capture_output=True)
    if res.returncode != 0:
        return ""
    lines = res.stdout.splitlines()  # stdout delivers a CR at the end
    if len(lines) >= 1 and len(lines[0]) >= 1:
        wlanip = lines[0].split()[0]     # if ip4 and ip6 present just take ipv4 adress
        rlog.debug(f'WLAN-IP read via hostname: {wlanip}')
        return wlanip
    else:
        rlog.debug(f'No WLAN-IP received via hostname.')
        return ""


def set_network(wifi, passw):
    wifi = wifi.strip()
    passw = passw.strip()
    res = subprocess.run(
        ["sudo", "raspi-config", "nonint", "do_wifi_ssid_passphrase", wifi, passw],
        check=False,
    )
    if res.returncode != 0:
        rlog.debug("STATUSUI: Setting Wifi network failed.")
        return
    rlog.debug("STATUSUI: Rebooting!")
    res = subprocess.run(["sudo", "reboot"], check=False)
    if res.returncode != 0:
        rlog.debug("STATUSUI: Reboot attempt failed.")


def next_char(current):
    return CHARSET[(CHARSET.find(current) + 1) % len(CHARSET)]


def prev_char(current):
    pos = CHARSET.find(current) - 1
    if pos < 0:
        pos = len(CHARSET)-1
    return CHARSET[pos]


def user_input(extsound_active, bluetooth_active):
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

    if status_mode == 0:
        middle = "Mode"
        left = "Netw"
        if bluetooth_active:
            right = "Scan"
        else:
            right = ""

    event = get_button_event()
    if event is None and status_mode != 11:
        return Modes.NO_CHANGE
    if event is not None and is_left_long(event):
        return Modes.SHUTDOWN

    if status_mode == 0:
        if event is not None and is_middle(event):
            return next_mode_sequence(Modes.STATUS)
        if event is not None and bluetooth_active and is_right_short(event):
            status_mode = 1
            start_async_bt_scan()
            scan_end = time.time() + BLUETOOTH_SCAN_TIME
        if event is not None and is_left_short(event):
            status_mode = 3
            wifi_ssid = read_network()
            wifi_ip = read_wlanip()
            if wifi_ssid != "":
                new_wifi = wifi_ssid.ljust(MAX_WIFI_LENGTH)
    elif status_mode == 1:
        pass
    elif status_mode == 2:
        if len(new_devices) == 0:
            if event is not None and bluetooth_active and is_right_short(event):
                status_mode = 1
                start_async_bt_scan()
                scan_end = time.time() + BLUETOOTH_SCAN_TIME
                return Modes.STATUS
        if len(new_devices) > 0:
            if event is not None and is_left_short(event):
                rlog.debug("Connecting: " + new_devices[0][1])
                radarbluez.trust_pair_connect(new_devices[0][0])
                del new_devices[0]
            if event is not None and is_right_short(event):
                rlog.debug("Not Connecting: " + new_devices[0][1])
                remove_device(new_devices[0][0])
                del new_devices[0]
        if len(new_devices) == 0 or (event is not None and is_middle_short(event)):
            new_devices = []
            status_mode = 0
    elif status_mode == 3:
        if event is not None and is_right_short(event):
            charpos = 0
            status_mode = 4
        if event is not None and is_middle_short(event):
            status_mode = 0
    elif status_mode == 4:
        if event is not None and is_left_short(event):
            new_wifi = new_wifi[:charpos] + next_char(new_wifi[charpos]) + new_wifi[charpos+1:]
        if event is not None and is_middle_short(event):
            charpos += 1
            if charpos >= len(new_wifi):
                charpos = 0
                status_mode = 5
        if event is not None and is_middle_long(event):
            charpos = 0
            status_mode = 5
        if event is not None and is_right_short(event):
            new_wifi = new_wifi[:charpos] + prev_char(new_wifi[charpos]) + new_wifi[charpos+1:]
    elif status_mode == 5:
        if event is not None and is_left_short(event):
            new_pass = new_pass[:charpos] + next_char(new_pass[charpos]) + new_pass[charpos+1:]
        if event is not None and is_middle_short(event):
            charpos += 1
            if charpos >= len(new_pass):
                charpos = 0
                check_wifi = new_wifi.strip()
                check_new_pass = new_pass.strip()
                status_mode = 6 if check_wifi and (not check_new_pass or len(check_new_pass) >= 8) else 10
        if event is not None and is_middle_long(event):
            check_wifi = new_wifi.strip()
            check_new_pass = new_pass.strip()
            if len(check_wifi) > 0 and (len(check_new_pass) == 0 or len(check_new_pass) >= 8):
                charpos = 0
                status_mode = 6
            else:
                status_mode = 10
        if event is not None and is_right_short(event):
            new_pass = new_pass[:charpos] + prev_char(new_pass[charpos]) + new_pass[charpos+1:]
    elif status_mode == 6:
        if event is not None and is_right_short(event):
            status_mode = 3
        elif event is not None and is_left_short(event):
            status_mode = 11
    elif status_mode == 10:
        if event is not None and is_right_short(event):
            charpos = 0
            status_mode = 4
        if event is not None and is_left_short(event):
            status_mode = 3
    elif status_mode == 11:
        new_wifi = new_wifi.strip()
        new_pass = new_pass.strip()
        set_network(new_wifi, new_pass)

    return Modes.STATUS
