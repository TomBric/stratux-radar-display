#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2022, Thomas Breitbach
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
import math
import radarbuttons
import ADS1x15
import time
import asyncio
import statusui


# constants
# Remark: Sensor graphics of MICS 5524 shows a logarithmic scael.
# Deriving the function for this give the linear equation 10**(RS/R0) = -0.867 (10**ppm) + 0.6
# a good explanation can be found e.g. on https://jayconsystems.com/blog/understanding-a-gas-sensor
M = -0.867
B = 0.6
RSR0_CLEAN = 3333.0   # 3.3 kOhm
R_DIVIDER = 10000.0   # Value of divider resistor 10 kOhm
SENSOR_VOLTAGE = 5.0   # voltage for sensor board and divider
# Measurement cycle
CO_TIMEOUT = 3     # measure ppm value every 10 secs
CO_MEASUREMENT_WINDOW = 60 * 60   # one hour, sliding window that is stored for display of ppm values
CO_MAX_VALUES = CO_MEASUREMENT_WINDOW / CO_TIMEOUT    # maximum no of stored values, currently one hour
CALIBRATION_TIME = 15   # time for calibration of sensor

# Alarm-Levels, SAE AS 412B-2001 gives some hints
WARNLEVEL = (
    (50, 5 * 60),        # give indication. 50 ppm more than 5 mins
    (70, 3 * 60),        # more than 70 ppm over 3 mins
    (100, 2 * 60),       # more than 100 ppm over 2 mins
    (300, 1 * 60),      # more than 300 ppm over 1 min
    (400, 0.5 * 60)     # more than 400 ppm over 30 secs
)

ALARM_RESET = (50, 3 * 60)       # reset alarm, if for 3 mins CO level below 50 ppm


# globals
r0 = 1.0     # value for R0 in clean air. Calculated during calibration
cowarner_active = False
voltage_factor = 1.0
ADS = None
rlog = None
g_config = {}
value_debug_level = 0   # debug level for printing ad-values
co_values = []    # all values are here in ppm, maximum
co_max = 0      # max value read during this run or after reset
co_warner_status = 0     # 0 - nomal status  1 - calibration in progress  2 - calibration done
calibration_end = 0.0     # timer for calibration
sample_sum = 0.0        # sum of sample-values
no_samples = 0       # no of samples taken during calibration
cowarner_changed = True   # for display driver, true if there is something to display
#


def ppm(rsr0):
    return 10 ** (math.log10(rsr0) - B) / M


def init(activate, config, debug_level):
    global rlog
    global cowarner_active
    global voltage_factor
    global ADS
    global g_config
    global value_debug_level
    global r0

    rlog = logging.getLogger('stratux-radar-log')
    if not activate:
        rlog.debug("CO-Warner - not activated")
        cowarner_active = False
        return False
    g_config = config
    if 'CO_warner_R0' in g_config:
        r0 = g_config['CO_warner_R0']
        rlog.debug("CO-Warner: found R0 in config, set to {1:.1f} Ohms".format(r0), r0)
    value_debug_level = debug_level
    ADS = ADS1x15.ADS1115(1, 0x48)    # ADS on I2C bus 1 with default adress
    if ADS is None:
        cowarner_active = False
        rlog.debug("CO-Warner - AD sensor not found")
        return cowarner_active
    # set gain to 4.096V max
    ADS.setMode(ADS.MODE_SINGLE)  # Single shot mode
    ADS.setGain(ADS.PGA_4_096V)
    voltage_factor = ADS.toVoltage()
    cowarner_active = True
    rlog.debug("CO-Warner: AD converter active. ADS1X15_LIB_VERSION: {}".format(ADS1x15.LIB_VERSION))
    return cowarner_active


def request_read():
    return ADS.requestADC(0)  # analog 0 input

def ready():
    return ADS.isReady()

def read_co_value():     # called by sensor_read thread
    global cowarner_changed
    global co_values
    global co_max

    cowarner_changed = True  # to display new value
    value = ADS.getValue()
    sensor_volt = value * voltage_factor
    rs_gas = ((SENSOR_VOLTAGE * R_DIVIDER) / sensor_volt) - R_DIVIDER  # calculate RS in fresh air
    ppm_value = round(ppm(rs_gas / r0))

    # for testing when nothings connected
    ppm_value = math.floor(time.time()) % 140

    rlog.log(value_debug_level, "C0-Warner: Analog0: {0:d}\t{1:.3f} V  PPM value: {0:d}"
             .format(value, sensor_volt, ppm_value))
    if ppm_value > co_max:
        co_max = ppm_value
    co_values.append(ppm_value)
    if len(co_values) > CO_MAX_VALUES:    # sliding window, remove oldest values
        co_values.pop(0)


def draw_cowarner(draw, display_control, changed):
    global cowarner_changed
    global co_warner_status


    if changed or cowarner_changed:
        cowarner_changed = False
        display_control.clear(draw)
        if co_warner_status == 0:   # normal mode, display status line
            display_control.cowarner(draw, co_values, co_max, r0, CO_MEASUREMENT_WINDOW)
        elif co_warner_status == 1:   # calibration mode
            countdown = math.floor(calibration_end - time.time())
            timeleft = str(countdown) + " secs"
            display_control.text_screen(draw, "CO Warner", "calibration",
                                        "Keep sensor in fresh air.\n" + timeleft, "", "", "")
        display_control.display()


async def calibration():   # called by user-input thread, performs calibration and ends calibration mode
    global co_warner_status
    global sample_sum
    global no_samples
    global r0
    global g_config
    global cowarner_changed

    cowarner_changed = True  # to display new value
    countdown = math.floor(calibration_end - time.time())
    if countdown > 0:   # continue sensor reading
        ADS.requestADC(0)  # analog 0 input
        while not ADS.isReady():
            await asyncio.sleep(0.01)
        value = ADS.getValue()
        sensor_volt = value * voltage_factor
        rs_air = ((SENSOR_VOLTAGE * R_DIVIDER) / sensor_volt) - R_DIVIDER  # calculate RS in fresh air
        r0_act = rs_air / RSR0_CLEAN  # r0, based on clean air measurement
        sample_sum += r0_act
        no_samples += 1
    else:
        r0 = sample_sum / no_samples
        rlog.debug("CO-Warner: Calibration finished. # samples: {0:d} r0: {1:.1f} Ohms"
                   .format(no_samples, r0))
        g_config['CO_warner_R0'] = r0
        statusui.write_config(g_config)
        co_warner_status = 0


def user_input():
    global cowarner_changed
    global co_max
    global co_warner_status
    global calibration_end
    global sample_sum
    global no_samples

    if not cowarner_active:
        rlog.debug("CO-Warner: not active, switching to radar-mode")
        return 1        # immediately go to next mode, if warner is not activated
    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        return 0  # stay in current mode
    cowarner_changed = True
    if button == 1 and (btime == 1 or btime == 2):  # middle in any case
        return 1  # next mode to be radar
    if button == 0 and btime == 1:  # left and short
        calibration_end = time.time() + CALIBRATION_TIME
        sample_sum = 0.0
        no_samples = 0
        calibration()
        co_warner_status = 1
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 2 and btime == 1:  # right and short, reset max value
        co_max = 0
    if button == 2 and btime == 2:  # right and long- refresh
        return 20  # start next mode for display driver: refresh called
    return 19  # no mode change
