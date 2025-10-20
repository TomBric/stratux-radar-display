#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
#
# BSD 3-Clause License
# Copyright (c) 2025, Thomas Breitbach
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

from . import epd1in54_V2
from .. import dcommon
from PIL import Image, ImageDraw, ImageFont
import math
import time
import datetime
from pathlib import Path
import logging


class Epaper1in54(dcommon.GenericDisplay):
    VERYLARGE = 30  # timer
    MORELARGE = 26
    LARGE = 24  # size of height indications of aircraft
    SMALL = 20  # size of information indications on top and bottom
    VERYSMALL = 18
    AWESOME_FONTSIZE = 18  # bluetooth indicator
    AIRCRAFT_SIZE = 4  # size of aircraft arrow
    MINIMAL_CIRCLE = 10  # minimal size of mode-s circle
    ARCPOSITION_EXCLUDE_FROM = 0
    ARCPOSITION_EXCLUDE_TO = 0
    # colors will be initialized in __init__
    ANGLE_OFFSET = 270  # offset for calculating angles in displays
    # attributes later defined in explicit init
    def __init__(self):
        super().__init__()
        # Initialize color attributes
        self.BG_COLOR = "white"
        self.TEXT_COLOR = "black"
        self.HIGHLIGHT_COLOR = "black"
        self.AIRCRAFT_COLOR = "black"
        self.AIRCRAFT_OUTLINE = "black"
        self.MODE_S_COLOR = "black"
        # AHRS colors
        self.AHRS_EARTH_COLOR = "white"
        self.AHRS_SKY_COLOR = "white"
        self.AHRS_HORIZON_COLOR = "black"
        self.AHRS_MARKS_COLOR = "black"
        # Other attributes
        self.device = None
        self.image = None
        self.mask = None
        self.dark_mode = False

    def set_dark_mode(self, dark_mode):
        """Set dark mode and update color constants accordingly"""
        self.dark_mode = dark_mode
        if dark_mode:
            self.BG_COLOR = "black"
            self.TEXT_COLOR = "white"
            self.HIGHLIGHT_COLOR = "white"
            self.AIRCRAFT_COLOR = "white"
            self.AIRCRAFT_OUTLINE = "white"
            self.MODE_S_COLOR = "white"
            self.AHRS_EARTH_COLOR = "black"
            self.AHRS_SKY_COLOR = "black"
            self.AHRS_HORIZON_COLOR = "white"
            self.AHRS_MARKS_COLOR = "white"
        else:
            self.BG_COLOR = "white"
            self.TEXT_COLOR = "black"
            self.HIGHLIGHT_COLOR = "black"
            self.AIRCRAFT_COLOR = "black"
            self.AIRCRAFT_OUTLINE = "black"
            self.MODE_S_COLOR = "black"
            self.AHRS_EARTH_COLOR = "white"
            self.AHRS_SKY_COLOR = "white"
            self.AHRS_HORIZON_COLOR = "black"
            self.AHRS_MARKS_COLOR = "black"

    def init(self, fullcircle=False, dark_mode=False):
        self.device = epd1in54_V2.EPD()
        self.device.init(0)
        self.device.Clear(0xFF)  # necessary to overwrite everything
        self.image = Image.new('1', (self.device.height, self.device.width), 0xFF)
        self.draw = ImageDraw.Draw(self.image)
        self.device.init(1)
        self.device.Clear(0xFF)
        # Initialize dark mode
        self.dark_mode = dark_mode
        self.set_dark_mode(dark_mode)
        self.sizex = self.device.height
        self.sizey = self.device.width
        self.zerox = self.sizex / 2
        self.zeroy = self.sizey / 2
        self.max_pixel = self.sizey
        self.ah_zeroy = self.sizey // 2  # zero line for ahrs
        self.ah_zerox = self.sizex // 2
        self.czerox = self.sizex // 2
        self.czeroy = self.sizey // 2
        # measure time for refresh
        start = time.time()
        # do sync version of display to measure time
        self.device.displayPart_mod(self.device.getbuffer_optimized(self.image))
        end = time.time()
        self.display_refresh = end - start
        # compass preparation
        pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-96x96.bmp'))
        self.compass_aircraft = Image.open(pic_path)
        self.mask = Image.new('1', (self.LARGE * 2, self.LARGE * 2))
        self.cdraw = ImageDraw.Draw(self.mask)
        self.rlog.debug(
            f'Epaper_1in54 selected: sizex={self.sizex} sizey={self.sizey} zero=({self.zerox}, {self.zeroy}) '
            f'refresh-time: {str(round(self.display_refresh, 2))} secs')
        return self.max_pixel, self.zerox, self.zeroy, self.display_refresh

    def display(self):
        self.device.async_displayPart(self.device.getbuffer_optimized(self.image))

    def is_busy(self):
        return self.device.async_is_busy()

    @staticmethod
    def next_arcposition(old_arcposition, exclude_from=0, exclude_to=0):
        return dcommon.GenericDisplay().next_arcposition(old_arcposition,
            exclude_from=Epaper1in54().ARCPOSITION_EXCLUDE_FROM, exclude_to=Epaper1in54().ARCPOSITION_EXCLUDE_TO)

    def cleanup(self):
        self.device.init(0)
        self.device.Clear(0xFF)
        self.device.sleep_nowait()

    def refresh(self):
        self.device.Clear(0xFF)  # necessary to overwrite everything
        self.device.init(1)

    def startup(self, version, target_ip, seconds):
        logopath = str(Path(__file__).resolve().parent.joinpath('stratux-logo-150x150.bmp'))
        logo = Image.open(logopath)
        self.draw.bitmap((self.zerox-150//2, 0), logo, fill=self.TEXT_COLOR)
        versionstr = f"Radar {version}"
        self.centered_text(150, versionstr, self.VERYLARGE)
        self.display()
        time.sleep(seconds)

    def situation(self, connected, gpsconnected, ownalt, course, rrange, altdifference, bt_devices, sound_active,
                  gps_quality, gps_h_accuracy, optical_bar, basemode, extsound, co_alarmlevel, co_alarmstring):
        self.draw.ellipse((self.zerox - self.max_pixel // 2, self.zeroy - self.max_pixel // 2,
                           self.zerox + self.max_pixel // 2 - 1, self.zeroy + self.max_pixel // 2 - 1), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - self.max_pixel // 4, self.zeroy - self.max_pixel // 4,
                           self.zerox + self.max_pixel // 4 - 1, self.zeroy + self.max_pixel // 4 - 1), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - 2, self.zeroy - 2, self.zerox + 2, self.zeroy + 2), outline=self.TEXT_COLOR)
        self.draw.text((0, 0), f"{rrange}", font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)
        self.draw.text((0, self.SMALL), "nm", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((0, self.sizey - self.SMALL), f"FL{round(ownalt / 100)}", font=self.fonts[self.SMALL],
                       fill=self.TEXT_COLOR)

        t = f"{altdifference // 1000}k" if altdifference >= 10000 else f"{altdifference}"
        tl = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - tl, 0), t, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR, align="right")
        text = "ft"
        tl = self.draw.textlength(text, self.fonts[self.VERYSMALL])
        self.draw.text((self.sizex - tl, self.SMALL), text, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR,
                       align="right")

        text = f"{course}°"
        tl = self.draw.textlength(text, self.fonts[self.SMALL])
        self.draw.text((self.sizex - tl, self.sizey - self.SMALL), text, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR, align="right")

        if not gpsconnected:
            self.centered_text(15, "No GPS", self.SMALL)
        if not connected:
            self.centered_text(75, "No connection!", self.SMALL)
        if co_alarmlevel > 0:
            self.centered_text(self.sizey - 3 * self.SMALL, "CO Alarm!", self.SMALL)
            self.centered_text(self.sizey - 2 * self.SMALL, co_alarmstring, self.SMALL)
        if extsound or bt_devices > 0:
            t = "\uf028" * extsound + "\uf293" * (bt_devices > 0) if sound_active else "\uf1f6"
            tl = self.draw.textlength(t, self.awesomefont)
            self.draw.text((self.sizex - tl, self.sizey - 2 * self.SMALL), t, font=self.awesomefont,
                           fill=self.TEXT_COLOR)
        self.draw.line((2, 150 + (optical_bar % 5) * 5, 2, 150 + (optical_bar % 5) * 5 + 6),
                       fill=self.TEXT_COLOR, width=4)

    def gmeter(self, current, maxg, ming, error_message):
        gm_size = self.sizex
        self.meter(current, -3, 5, 120, 420, gm_size, self.zerox, self.zeroy, 1, 0.25, "G-Force", None)
        self.draw.text((self.zerox + 13, 80), "max", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.right_text(80, f"{maxg:+1.2f}", self.SMALL)
        if error_message:
            self.centered_text(57, error_message, self.LARGE)
        self.draw.text((self.zerox + 13, 102), "min", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.right_text(102, f"{ming:+1.2f}", self.SMALL)
        self.bottom_line("", "", "Rst")

    def vsi(self, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
            error_message):
        self.meter(vertical_speed / 100, -20, 20, 110, 430, self.sizey, self.sizey // 2,
                   self.sizey // 2, 5, 1, "Vert Spd", "100ft/min",
                   middle_fontsize=self.VERYSMALL)
        self.draw.text((15, self.sizey // 2 - self.VERYSMALL - 10), "up", font=self.fonts[self.VERYSMALL],
                       fill=self.TEXT_COLOR, align="left")
        self.draw.text((15, self.sizey // 2 + 10), "dn", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR,
                       align="left")
        if error_message:
            self.centered_text(40, error_message, self.LARGE)
        self.bottom_line("", "", "")

    def earthfill(self, pitch, roll, length, scale):   # possible function for derived classed to implement fillings for earth
        # draws some type of black shading for the earth
        for pm in range(0, -180-1, -3):
            self.draw.line((self.linepoints(pitch, roll, pm, length, scale)), fill=self.TEXT_COLOR, width=1)

    def stratux(self, stat, altitude, gps_alt, gps_quality):
        starty = 0
        self.centered_text(0, f"Stratux {stat['version']}", self.SMALL)
        starty += self.SMALL + 6
        colors = {'outline': self.TEXT_COLOR, 'black_white_offset': 5}
        bar_start, bar_end = 50, 150
        line_offset = 4
        outline_offset = 1
        starty = self.bar(starty, "1090", stat['ES_messages_last_minute'], stat['ES_messages_max'],
                          bar_start, bar_end, colors, line_offset=line_offset, outline_offset=outline_offset)
        if stat['OGN_connected']:
            starty = self.bar(starty, "OGN", stat['OGN_messages_last_minute'], stat['OGN_messages_max'],
                              bar_start, bar_end, colors, line_offset=line_offset, outline_offset=outline_offset)
            noise_text = f"{round(stat['OGN_noise_db'], 1)}@{round(stat['OGN_gain_db'], 1)}dB"
            starty = self.bar(starty, "noise", stat['OGN_noise_db'], 25,
                bar_start, bar_end, colors, unit="dB", minval=1, valtext=noise_text, line_offset=line_offset,
                outline_offset=outline_offset)
        if stat['UATRadio_connected']:
            starty = self.bar(starty, "UAT", stat['UAT_messages_last_minute'], stat['UAT_messages_max'],
                              bar_start, bar_end, colors, line_offset=line_offset, outline_offset=outline_offset)
        if stat['CPUTemp'] > -300:
            starty = self.bar(starty, "temp", round(stat['CPUTemp'], 1), round(stat['CPUTempMax'], 0),
                              bar_start, bar_end, colors, unit="°C", line_offset=line_offset,
                              outline_offset=outline_offset)
        t = "3D GPS " if gps_quality == 1 else "DGNSS " if gps_quality == 2 else "GPS"
        # GPS
        self.draw.text((0, starty), t, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        t = f"{stat['GPS_satellites_locked']}/{stat['GPS_satellites_seen']}/{stat['GPS_satellites_tracked']}"
        self.draw.text((70, starty), t, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        gps = f"{round(stat['GPS_position_accuracy'], 1)}m" if stat['GPS_position_accuracy'] < 19999 else "NoFix"
        self.right_text(starty, gps, self.VERYSMALL)
        starty += self.VERYSMALL + 2
        self.draw.text((0, starty), f"P-Alt {altitude:.0f}ft", font=self.fonts[self.VERYSMALL])
        self.right_text(starty, f"Corr {stat['AltitudeOffset']:+}ft", self.VERYSMALL)
        starty += self.VERYSMALL + 6
        x = self.round_text(0, starty, "IMU", yesno=stat['IMUConnected'], out_color =self.TEXT_COLOR)
        self.round_text(x, starty, "BMP", yesno=stat['BMPConnected'], out_color=self.TEXT_COLOR)
        alt = f"{gps_alt:.0f}" if stat['GPS_position_accuracy'] < 19999 else "---"
        self.right_text(starty, f"GAlt {alt}ft", self.VERYSMALL)
        self.bottom_line("+10ft", "Mode", "-10ft")

    def cowarner(self, co_values, co_max, r0, timeout, alarmlevel, alarmtext, simulation_mode=False):   # draw graph and co values
        self.centered_text(0, alarmtext, self.LARGE)
        graphpos = (0, self.SMALL + 5)
        graphsize = (self.sizex-20, self.sizey-3*self.VERYSMALL-self.SMALL-5)
        self.graph(graphpos, graphsize, co_values, 0, 120, timeout, value_line1=50, value_line2=100,
                   glinewidth=2, linewidth=2)
        if len(co_values) > 0:
            self.round_text(30, self.sizey-2*self.VERYSMALL-5, "act: {:3d}".format(co_values[len(co_values) - 1]),
                            bg_color=self.TEXT_COLOR, text_color=self.BG_COLOR)
        self.round_text(self.sizex // 2 + 15, self.sizey-2*self.VERYSMALL-5, "max: {:3d}".format(co_max),
                        bg_color=self.TEXT_COLOR, text_color=self.BG_COLOR)
        if simulation_mode:
            self.round_text(3*self.VERYSMALL-4, self.sizey//4+4, "simulation mode", out_color=self.TEXT_COLOR)
        self.bottom_line("Cal", "Mode", "Reset")

    def distance(self, now, gps_valid, gps_quality, gps_h_accuracy, distance_valid, gps_distance, gps_speed, baro_valid,
                         own_altitude, alt_diff, alt_diff_takeoff, vert_speed, ahrs_valid, ahrs_pitch, ahrs_roll,
                         ground_distance_valid, grounddistance, error_message):
        self.centered_text(0, "GPS-Distance", self.SMALL)
        gps_dist_str = f"{gps_distance:.0f}" if distance_valid else "---"
        gps_speed_str = f"{gps_speed:.1f}" if gps_valid else "---"
        lines = (
            ("UTC", "{:0>2d}:{:0>2d}:{:0>2d},{:1d}".format(now.hour, now.minute, now.second,
                                                           math.floor(now.microsecond / 100000))),
            ("GPS-Dist [m]", gps_dist_str),
            ("GPS-Spd [kts]", gps_speed_str),
        )
        starty = self.dashboard(0, self.SMALL, self.sizex, lines)
        if baro_valid:
            takeoff_str = f"{alt_diff_takeoff:+5.1f}" if alt_diff_takeoff is not None else "---"
            lines = (
                ("VSpeed [ft]", f"{vert_speed:+4.0f}"),
                ("BaDif tof [ft]", takeoff_str),
            )
            starty = self.dashboard(0, starty, self.sizex, lines)
        if ground_distance_valid:
            lines = (
                ("GrdDist [cm]", f"{grounddistance / 10:+3.1f}"),
            )
            self.dashboard(0, starty, self.sizex, lines)
        if error_message is not None:
            self.centered_text(80, error_message, self.LARGE)
        self.bottom_line("Set", "His/Mode", "Start")

    def distance_statistics(self, values, gps_valid, gps_altitude, dest_altitude, dest_alt_valid, ground_warnings,
                            current_stats=True, next_stat=False, prev_stat=False, index=-1):
        if current_stats:  # current data, still flying
            self.centered_text(0, "Act Start-/Landing", self.SMALL)
        else:
            if index >= 0:
                self.centered_text(0, f"Start-/Land #{index + 1}", self.SMALL)
            else:
                self.centered_text(0, f"No Start-/Land Data", self.SMALL)
        st = '---'
        if 'start_time' in values:
            dt = values['start_time']
            if not isinstance(dt, datetime.datetime):
                dt = datetime.fromisoformat(dt)
            st = dt.strftime("%H:%M:%S,%f")[:-5]
        lines = (
            ("t-off time", st),
            ("t-off dist [m]", self.form_line(values, 'takeoff_distance', "{:3.1f}")),
            ("obst dist [m]", self.form_line(values, 'obstacle_distance_start', "{:3.1f}")),
        )
        starty = self.dashboard(0, self.SMALL+2 , self.sizex, lines)

        lt = '---'
        if 'landing_time' in values:
            dt = values['landing_time']
            if not isinstance(dt, datetime.datetime):
                dt = datetime.fromisoformat(dt)
            lt = dt.strftime("%H:%M:%S,%f")[:-5]
        lines = (
            ("ldg time", lt),
            ("ldg dist [m]", self.form_line(values, 'landing_distance', "{:3.1f}")),
            ("obst dist [m]", self.form_line(values, 'obstacle_distance_landing', "{:3.1f}")),
        )
        starty = self.dashboard(0, starty, self.sizex, lines)
        if current_stats:
            if ground_warnings:
                dest_alt_str = f"{dest_altitude:+5.0f}" if dest_alt_valid else "---"
                lines = (
                    ("Dest. Alt [ft]", dest_alt_str),
                )
                self.dashboard(0, starty, self.sizex, lines)
                self.bottom_line("+/-100ft", "  Back", "+/-10ft")
            else:
                self.bottom_line("", "Back", "")
        else: # stored stats
            left="Prev" if prev_stat else ""
            right="Next" if next_stat else ""
            self.bottom_line(left, "Exit", right)


# instantiate a single object in the file, needs to be done and inherited in every display module
radar_display = Epaper1in54()