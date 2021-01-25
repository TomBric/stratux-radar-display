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
import os
import radarbuttons
import time
import asyncio

SHUTDOWN_WAIT_TIME = 6.0
shutdown_time = 0.0
clear_before_shutoff = False


def draw_shutdown(draw, display_control):
    global clear_before_shutoff

    if shutdown_time > 0:
        display_control.clear(draw)
        display_control.shutdown(draw, int(shutdown_time - time.time()))
        display_control.display()
    if clear_before_shutoff:
        display_control.cleanup(draw)
        clear_before_shutoff = False
        return True
    else:
        return False

async def user_input(display_time):
    global shutdown_time
    global clear_before_shutoff

    if shutdown_time == 0.0:     # first time or after stopped shutdwon
        shutdown_time = time.time() + SHUTDOWN_WAIT_TIME
    btime, button = radarbuttons.check_buttons()
    if btime > 0:   # any button pressed
        shutdown_time = 0.0
        return 1  # go back to radar mode
    if time.time() > shutdown_time:
        logging.debug("Initiating shutdown ...")
        print("Shutdown now")
        clear_before_shutoff = True   # enable display driver to shut off
        await asyncio.sleep(display_time*3)  # time for the display to shut off
        os.popen("sudo shutdown --poweroff now").read()
        shutdown_time = 0.0
        return 1  # go back to radar mode; but never reached normally
    return 3   # go back to shutdown mode
