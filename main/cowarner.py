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
import ADS1x15       # https://github.com/chandrawi/ADS1x15-ADC
import time
import asyncio
import statusui
import radarbluez
import RPi.GPIO as GPIO
import numpy
import radarmodes


# constants
# Remark: Sensoror graphics of MICS 5524 shows a logarithmic scale.
# Deriving the function for this gives the linear equation 10**(RS/R0) = -0.867 (10**ppm) + 0.6
# a good explanation can be found e.g. on https://jayconsystems.com/blog/understanding-a-gas-sensor
# But sensor behaves not according data sheet. My own measurements revealed:    ppm = 10^(((RS/RO)-3.3)/-1.4)

RSR0_CLEAN = 3.333   # 3.3 ppm, see data sheet of MICS-5524
R_DIVIDER = 10000.0   # Value of divider resistor 10 kOhm
SENSOR_VOLTAGE = 5.0   # voltage for sensor board and divider
# Measurement cycle
CO_MEASUREMENT_WINDOW = 60 * 60   # one hour, sliding window that is stored for display of ppm values
CALIBRATION_TIME = 15   # time for calibration of sensor
MIN_SENSOR_READ_TIME = 3
# minimal time in secs when sensor reading thread  is generally started
MIN_SENSOR_WAIT_TIME = 0.01
# minimal time in secs to wait when sensor is not yet ready
MIN_SENSOR_CALIBRATION_WAIT_TIME = 0.5
# minimal time in secs to wait during calibration and two sensor readings
IOPIN = 16   # GPIO16 for indication of co warning, high on alarm (physical #36, connect to ground #34)
INDICATION_TEST_TIME = 1   # time during startup when indication will be switched on for test

WARNLEVEL = (   # ppmvalue, time after level is reached, alarmstring, time between repeats for spoken warning
    (0, 0, "No CO alarm", 0),
    (50, 5 * 60, "50 ppm > 5 mins", 3 * 60),
    (70, 3 * 60, "70 ppm > 3 mins", 2 * 60),
    (100, 2 * 60, "100 ppm > 2 mins", 45),
    (300, 1 * 60, "300 ppm > 1 min", 15),
    (400, 0.5 * 60, "400 ppm > 30 secs", 10)
)


# globals
alarmlevel = 0   # see above level for warnlevel 0-5
# time when this alarmlevel was first reached or underrun
r0 = 900.0     # value for R0 in clean air. Calculated during calibration, 900 is a good starting point
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
co_timeout = 1.0    # timeout of reader process, time intervall of readings
co_max_values = 100   # max number of values, is calculated in init
speak_warning = True
indicate_co_warning = False    # GPIO 16 indication
last_warning = 0.0   # timestamp of last warning
#


def ppm(rsr0):
    val = 10 ** ((math.log10(rsr0) - 0.9) / -0.75)
    # val = 10 ** ((rsr0 - 3.3) / -1.33)
    if val < 5:
        return 0    # no valid measurements below 5
    if val > 1000:
        return 1000
    return val
    # based on own measurements compared with a CO warner


def init(activate, config, debug_level, co_indication):
    global rlog
    global cowarner_active
    global voltage_factor
    global ADS
    global g_config
    global value_debug_level
    global r0
    global co_timeout
    global co_max_values
    global indicate_co_warning

    rlog = logging.getLogger('stratux-radar-log')
    if not activate:
        rlog.debug("CO-Warner - not activated")
        cowarner_active = False
        return False
    g_config = config
    if 'CO_warner_R0' in g_config:
        r0 = g_config['CO_warner_R0']
        rlog.debug("CO-Warner: found R0 in config, set to {:.1f} Ohms".format(r0))
    value_debug_level = debug_level
    co_timeout = MIN_SENSOR_READ_TIME
    co_max_values = math.floor(CO_MEASUREMENT_WINDOW / co_timeout)
    try:
        ADS = ADS1x15.ADS1115(1, 0x48)    # ADS on I2C bus 1 with default adress
    except OSError:
        cowarner_active = False
        rlog.debug("CO-Warner - AD sensor not found")
        return False
    # set gain to 4.096V max
    ADS.setMode(ADS.MODE_SINGLE)  # Single shot mode
    ADS.setGain(ADS.PGA_4_096V)
    voltage_factor = ADS.toVoltage()
    cowarner_active = True
    rlog.debug("CO-Warner: AD converter active.")
    if co_indication:
        indicate_co_warning = True
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(IOPIN, GPIO.OUT, initial=GPIO.LOW)
        rlog.debug("CO-Warner: indication for co alarm on PIN " + str(IOPIN) + " activated")
    return cowarner_active


def request_read():
    return ADS.requestADC(0)  # analog 0 input


def ready():
    return ADS.isReady()


def alarm_level():   # to be called from outside, returns 0 if no alarm, 1-5 depending on ALARMLEVEL and alarmstring
    return alarmlevel, WARNLEVEL[alarmlevel][2]


def check_alarm_level():   # check wether new alarm level should be reached, called by sensor reader thread
    global alarmlevel

    for i in range(len(WARNLEVEL)-1, 0, -1):    # check all warnleves starting high e.g. (50, 3*30, "No CO alarm", None)
        num_values = math.floor(WARNLEVEL[i][1] / MIN_SENSOR_READ_TIME)   # number of values to take into account
        if len(co_values) >= num_values:   # if less values available, do not alarm
            average = numpy.average(co_values[len(co_values)-num_values: len(co_values)])
            # print("Average " + str(WARNLEVEL[i]) + ": " + str(num_values) + " values " + str(average) + " ppm")
            if average >= WARNLEVEL[i][0]:
                if alarmlevel != i:
                    alarmlevel = i
                    return True    # level was changed
                else:
                    return False   # no level change
    if alarmlevel != 0:
        alarmlevel = 0
        return True
    return False


def read_co_value():     # called by sensor_read thread
    global cowarner_changed
    global co_values
    global co_max

    cowarner_changed = True  # to display new value
    value = ADS.getValue()
    sensor_volt = value * voltage_factor
    rs_gas = ((SENSOR_VOLTAGE * R_DIVIDER) / sensor_volt) - R_DIVIDER  # calculate resistor of sensor
    ppm_value = round(ppm(rs_gas / r0))
    rlog.log(value_debug_level,
             "C0-Warner: Analog0: {0:5d}  {1:.3f} V  RS_gas: {2:5.3f} kOhms   RS_gas/R0: {3:3.3f}    PPM value: {4:d}"
             .format(value, sensor_volt, rs_gas/1000, rs_gas/r0, ppm_value))
    # print("C0-Warner: Analog0: {0:5d}  {1:2.3f} V    RS_gas: {2:5.3f} kOhms
    # RS_gas/R0: {3:3.3f}  PPM value: {4:d}".format(value, sensor_volt, rs_gas/1000, rs_gas / r0, ppm_value))
    if ppm_value > co_max:
        co_max = ppm_value
    co_values.append(ppm_value)
    if len(co_values) > co_max_values:    # sliding window, remove the oldest values
        co_values.pop(0)
    return check_alarm_level()


def draw_cowarner(display_control, changed):
    global cowarner_changed
    global co_warner_status

    if cowarner_active and (changed or cowarner_changed):
        cowarner_changed = False
        display_control.clear()
        if co_warner_status == 0:   # normal mode, display status line
            display_control.cowarner(co_values, co_max, r0, co_timeout, alarmlevel, WARNLEVEL[alarmlevel][0],
                                     WARNLEVEL[alarmlevel][1])
        elif co_warner_status == 1:   # calibration mode
            countdown = calibration_end - math.floor(time.time())
            if countdown < 0:
                countdown = 0   # sometimes draw thread was quicker, thus to avoid -1
            timeleft = str(countdown) + " secs"
            display_control.text_screen("Calibrate sensor", timeleft,
                                        "\n\nKeep sensor in fresh air.\n", "", "", "")
        display_control.display()


def calibration():   # called by user-input thread, performs calibration and ends calibration mode
    global co_warner_status
    global sample_sum
    global no_samples
    global r0
    global g_config
    global cowarner_changed

    cowarner_changed = True  # to display new value
    countdown = calibration_end - math.floor(time.time())
    if countdown > 0:   # continue sensor reading
        value = ADS.getValue()
        sensor_volt = value * voltage_factor
        rs_air = ((SENSOR_VOLTAGE * R_DIVIDER) / sensor_volt) - R_DIVIDER  # calculate RS in fresh air
        r0_act = rs_air / RSR0_CLEAN  # r0, based on clean air measurement
        sample_sum += r0_act
        no_samples += 1
    else:
        r0 = sample_sum / no_samples
        rlog.debug("CO-Warner: Calibration finished. # samples: {0:d} r0: {1:.1f} ppm"
                   .format(no_samples, r0))
        g_config['CO_warner_R0'] = r0
        statusui.write_config(g_config)
        co_warner_status = 0


def user_input():
    global cowarner_changed
    global co_max
    global co_values
    global co_warner_status
    global calibration_end
    global sample_sum
    global no_samples

    if not cowarner_active:
        rlog.debug("CO-Warner: not active, switching to next mode")
        return radarmodes.next_mode_sequence(19)     # immediately go to next mode, if warner is not activated
    btime, button = radarbuttons.check_buttons()
    if btime == 0 or co_warner_status == 1:   # in calibration mode, do not react
        return 0  # stay in current mode
    cowarner_changed = True
    if button == 1 and (btime == 1 or btime == 2):  # middle in any case
        return radarmodes.next_mode_sequence(19)    # next mode
    if button == 0 and btime == 1:  # left and short
        calibration_end = math.floor(time.time() + CALIBRATION_TIME)
        sample_sum = 0.0
        no_samples = 0
        calibration()
        co_warner_status = 1
    if button == 0 and btime == 2:  # left and long
        return 3  # start next mode shutdown!
    if button == 2 and btime == 1:  # right and short, reset max value
        co_max = 0
        co_values.clear()  # clear all history
    if button == 2 and btime == 2:  # right and long: refresh
        return 20  # start next mode for display driver: refresh called
    return 19  # no mode change


def speak_co_warning(changed):
    global last_warning
    if speak_warning and alarmlevel > 0:
        if changed or time.time() - last_warning >= WARNLEVEL[alarmlevel][3]:
            radarbluez.speak("CO Alarm! " + str(WARNLEVEL[alarmlevel][0]) + " ppm")
            last_warning = time.time()


def set_co_indication(changed):
    if changed and indicate_co_warning:
        if alarmlevel > 0:
            GPIO.output(IOPIN, GPIO.HIGH)
            rlog.debug("CO-Warner: setting GPIO Pin " + str(IOPIN) + " to HIGH for co-alarm")
        else:
            GPIO.output(IOPIN, GPIO.LOW)
            rlog.debug("CO-Warner: setting GPIO Pin " + str(IOPIN) + " to LOW for no co-alarm")


async def read_sensors():
    if cowarner_active:
        try:
            rlog.debug("Sensor reader active ...")
            if indicate_co_warning:
                rlog.debug("CO-Warner: Flashing GPIO Pin " + str(IOPIN) + " to test indication")
                GPIO.output(IOPIN, GPIO.HIGH)
                await asyncio.sleep(INDICATION_TEST_TIME)
                GPIO.output(IOPIN, GPIO.LOW)
            while True:
                request_read()
                while not ready():
                    await asyncio.sleep(MIN_SENSOR_WAIT_TIME)
                if co_warner_status == 0:   # normal read
                    changed = read_co_value()
                    speak_co_warning(changed)
                    set_co_indication(changed)
                    await asyncio.sleep(MIN_SENSOR_READ_TIME)
                else:
                    calibration()
                    await asyncio.sleep(MIN_SENSOR_CALIBRATION_WAIT_TIME)
        except (asyncio.CancelledError, RuntimeError):
            rlog.debug("Sensor reader terminating ...")
    else:
        rlog.debug("No co-sensor active.")
