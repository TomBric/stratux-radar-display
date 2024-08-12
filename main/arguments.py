#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2024, Thomas Breitbach
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

# radar command line arguments

import argparse

CONFIG_DIR = "config"
DEFAULT_URL_HOST_BASE = "192.168.10.1"
DEFAULT_MIXER = "Speaker"  # default mixer name to be used for sound output
DEFAULT_CHECKLIST = str(Path(__file__).resolve().parent.parent.joinpath(CONFIG_DIR, "checklist.xml"))


def add(ap):
    ap.add_argument("-d", "--device", required=True, help="Display device to use")
    ap.add_argument("-b", "--bluetooth", required=False, help="Bluetooth speech warnings on", action='store_true',
                    default=False)
    ap.add_argument("-sd", "--speakdistance", required=False, help="Speech with distance", action='store_true',
                    default=False)
    ap.add_argument("-n", "--north", required=False, help="Ground mode: always display north up", action='store_true',
                    default=False)
    ap.add_argument("-chl", "--checklist", required=False, help="Checklist file name to use",
                    default=DEFAULT_CHECKLIST)
    ap.add_argument("-c", "--connect", required=False, help="Connect to Stratux-IP", default=DEFAULT_URL_HOST_BASE)
    ap.add_argument("-v", "--verbose", type=int, required=False, help="Debug output level [0-3]",
                    default=0)
    ap.add_argument("-r", "--registration", required=False, help="Display registration no (epaper only)",
                    action="store_true", default=False)
    ap.add_argument("-e", "--fullcircle", required=False, help="Display full circle radar (3.7 epaper only)",
                    action="store_true", default=False)
    ap.add_argument("-y", "--extsound", type=int, required=False, help="Ext sound on with volume [0-100]",
                    default=0)
    ap.add_argument("-nf", "--noflighttime", required=False, help="Suppress detection and display of flighttime",
                    action="store_true", default=False)
    ap.add_argument("-nc", "--nocowarner", required=False, help="Suppress activation of co-warner",
                    action="store_true", default=False)
    ap.add_argument("-ci", "--coindicate", required=False, help="Indicate co warning via GPIO16",
                    action="store_true", default=False)
    ap.add_argument("-gd", "--grounddistance", required=False, help="Activate ground distance sensor",
                    action="store_true", default=False)
    ap.add_argument("-gb", "--groundbeep", required=False, help="Indicate ground distance via sound",
                    action="store_true", default=False)
    ap.add_argument("-gi", "--gearindicate", required=False, help="Indicate gear warning",
                    action="store_true", default=False)
    ap.add_argument("-sim", "--simulation", required=False, help="Simulation mode for testing",
                    action="store_true", default=False)
    ap.add_argument("-mx", "--mixer", required=False, help="Mixer name to be used for sound output",
                    default=DEFAULT_MIXER)
    ap.add_argument("-modes", "--displaymodes", required=False,
                    help="Select display modes that you want to see ""R=radar T=timer A=ahrs D=display-status "
                         "G=g-meter K=compass V=vsi I=flighttime S=stratux-status C=co-sensor "
                         "M=distance measurement L=checklist  Example: -modes RADCM", default="RTAGKVICMDSL")