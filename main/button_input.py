#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2026, Thomas Breitbach
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

import radarbuttons


class ButtonSide:
    LEFT = 0
    MIDDLE = 1
    RIGHT = 2


class ButtonLength:
    SHORT = 1
    LONG = 2


class ButtonEvent:
    def __init__(self, side, length):
        self.side = side
        self.length = length

    def matches(self, side, length=None):
        if self.side != side:
            return False
        if length is not None and self.length != length:
            return False
        return True


def get_button_event():
    btime, button = radarbuttons.check_buttons()
    if btime == 0:
        return None
    if button not in (ButtonSide.LEFT, ButtonSide.MIDDLE, ButtonSide.RIGHT):
        return None
    if btime not in (ButtonLength.SHORT, ButtonLength.LONG):
        return None
    return ButtonEvent(button, btime)


def is_left(event):
    return event is not None and event.side == ButtonSide.LEFT


def is_middle(event):
    return event is not None and event.side == ButtonSide.MIDDLE


def is_right(event):
    return event is not None and event.side == ButtonSide.RIGHT


def is_left_short(event):
    return event is not None and event.matches(ButtonSide.LEFT, ButtonLength.SHORT)


def is_left_long(event):
    return event is not None and event.matches(ButtonSide.LEFT, ButtonLength.LONG)


def is_middle_short(event):
    return event is not None and event.matches(ButtonSide.MIDDLE, ButtonLength.SHORT)


def is_middle_long(event):
    return event is not None and event.matches(ButtonSide.MIDDLE, ButtonLength.LONG)


def is_right_short(event):
    return event is not None and event.matches(ButtonSide.RIGHT, ButtonLength.SHORT)


def is_right_long(event):
    return event is not None and event.matches(ButtonSide.RIGHT, ButtonLength.LONG)
