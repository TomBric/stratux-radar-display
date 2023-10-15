#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2023, Thomas Breitbach
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

# To use Ultrasonic sensor, which is connected via UART add the following lines to /boot/config.txt
# enable_uart=1
# dtoverlay=miniuart-bt

import logging
import json

rlog = None  # radar specific logger
simulation_mode = False

# constants
SIM_DATA_FILE = "simulation_data.json"
# file with JSON content, e.g.:   {"g_distance": 10,"gps_speed": 0,"own_altitude": 10}


def init(sim_mode):
    global rlog
    global simulation_mode

    simulation_mode = sim_mode
    rlog = logging.getLogger('stratux-radar-log')
    if simulation_mode:
        rlog.debug('Simulation mode activated - Reading sim data from: ' + SIM_DATA_FILE + '.')
        sim_data = read_simulation_data()
        if sim_data is not None:
            rlog.debug('Initial simulation data: ' + json.dumps(sim_data))
        else:
            rlog.debug('Error reading simulation data in file ' + SIM_DATA_FILE + '.')


def read_simulation_data():  # returns dictionary with all contents of the SIM_DATA_FILE, None if file operation failed
    try:
        with open(SIM_DATA_FILE) as f:
            sim_data = json.load(f)
    except (OSError, IOError, ValueError) as e:
        rlog.debug("Simulation: Error " + str(e) + " reading " + SIM_DATA_FILE)
        return None
    return sim_data
