#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2020, Thomas Breitbach
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

# radar mode definitions

# 1=Radar 2=Timer 3=Shutdown 4=refresh from radar 5=ahrs 6=refresh from ahrs
# 7=status 8=refresh from status  9=gmeter 10=refresh from gmeter 11=compass 12=refresh from compass
# 13=VSI 14=refresh from VSI 15=dispay stratux status 16=refresh from stratux status
# 17=flighttime 18=refresh flighttime 19=cowarner 20=refresh cowarner 21=situation 22=refresh situation 0=Init


mode_sequence = []    # list of modes to display


def mode_codes(c):
    modes = {
        "R": 1,
        "T": 2,
        "A": 5,
        "D": 7,
        "G": 9,
        "K": 11,
        "V": 13,
        "S": 15,
        "I": 17,
        "C": 19,
        "M": 21,
        "L": 23
    }
    return modes.get(c, 0)


def parse_modes(modes):
    global mode_sequence
    mode_sequence = []
    for c in modes:
        mode_no = mode_codes(c)
        if mode_no > 0:
            mode_sequence.append(mode_no)


def next_mode_sequence(current_mode):
    iterator = iter(mode_sequence)
    next_mode = mode_sequence[0]   # return to first mode, if old mode not found, error proof
    for value in iterator:
        if value == current_mode:
            next_mode = next(iterator, mode_sequence[0])
    return next_mode


def first_mode_sequence():
    return mode_sequence[0]  # return to first mode


def is_mode_contained(mode):
    return mode in mode_sequence  # return true is mode is in mode sequence, false otherwise
