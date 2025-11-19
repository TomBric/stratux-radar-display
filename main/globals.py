#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2021-2025, Thomas Breitbach
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
from enum import Enum

class Modes(Enum):
    NO_CHANGE = 0
    RADAR = 1
    TIMER = 2
    SHUTDOWN = 3
    REFRESH_RADAR = 4
    AHRS = 5
    REFRESH_AHRS = 6
    STATUS = 7
    REFRESH_STATUS = 8
    GMETER = 9
    REFRESH_GMETER = 10
    COMPASS = 11
    REFRESH_COMPASS = 12
    VSI = 13
    REFRESH_VSI = 14
    STRATUX_STATUS = 15
    REFRESH_STRATUX_STATUS = 16
    FLIGHTTIME = 17
    REFRESH_FLIGHTTIME = 18
    COWARNER = 19
    REFRESH_CO_WARNER = 20
    SITUATION = 21    # for ground_distance
    REFRESH_SITUATION = 22
    CHECKLIST = 23
    REFRESH_CHECKLIST = 24




# Initialize logger
rlog = logging.getLogger('stratux-radar-log')

# Global configuration dictionary
global_config = {}

# Display control object
display_control = None

# Global mode for radar display
global_mode = Modes.RADAR  # Start with RADAR mode

# Status flags
bluetooth_active = False
extsound_active = False
measure_flighttime = False
co_warner_activated = False
grounddistance_activated = False

# Configuration file path
CONFIG_FILE = ""

# File paths
SAVED_FLIGHTS = "saved_flights.json"
SAVED_STATISTICS = "saved_statistics.json"
SITUATION_DEBUG = 0  # 0=off, 1=some debug, 2=more debug

mode_sequence = []  # list of modes to display
