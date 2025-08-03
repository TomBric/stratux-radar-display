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
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE

from .. import dcommon

class NoDisplay(dcommon.GenericDisplay):
    def init(self, fullcircle=False, dark_mode=False):    # explicit init to be implemented for every device type
        self.rlog.debug("Running Radar with NoDisplay! ")
        return self.max_pixel, self.zerox, self.zeroy, self.display_refresh

    # define all functions which are defined in dcommon for external calls
    def clear(self):
        pass

    def modesaircraft(self, radius, height, arcposition, vspeed, tail, width=3):
        pass

    def aircraft(self, x, y, direction, height, vspeed, nspeed_length, tail):
        pass


    def timer(self, utctime, stoptime, laptime, laptime_head, left_text, middle_text, right_t, timer_runs,
              utc_color=None, timer_color=None, second_color=None):
        pass

    def compass(self, heading, error_message):
        pass

    def ahrs(self, pitch, roll, heading, slipskid, error_message):
        pass

    def screen_input(self, headline, subline, text, left, middle, right, prefix, inp, suffix):
        pass

    def flighttime(self, last_flights, side_offset=0, long_version=False):
        pass

    def distance_statistics(self, values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings):
        pass

    def checklist(self, checklist_name, checklist_items, current_index, last_list, color=None):
        pass

    def shutdown(self, countdown, shutdownmode):
        pass

    def text_screen(self, headline, subline, text, left_text, middle_text, r_text, offset=0):
        pass

# instantiate a single object in the file, needs to be done and inherited in every display module
radar_display = NoDisplay()
