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

from .. import dcommon
from PIL import Image, ImageDraw
import math
import time
from . import radar_opts
from pathlib import Path

class ST7789(dcommon.GenericDisplay):
    EXTREMELARGE = 60  # countdown distance
    VERYLARGE = 48  # timer
    MORELARGE = 32
    LARGE = 28  # size of height indications of aircraft, size of meter TEXT
    SMALL = 20  # size of information indications on top and bottom
    VERYSMALL = 18  # used for "nm" and "ft"
    AIRCRAFT_SIZE = 6  # size of aircraft arrow
    MINIMAL_CIRCLE = 20  # minimal size of mode-s circle
    AWESOME_FONTSIZE = 18
    ARCPOSITION_EXCLUDE_FROM = 110
    ARCPOSITION_EXCLUDE_TO = 250
    ANGLE_OFFSET = 270  # offset for calculating angles in displays
    UP_CHARACTER = '\u2191'  # character to show ascending aircraft
    DOWN_CHARACTER = '\u2193'  # character to show descending aircraft


    def __init__(self):
        super().__init__()
        # color attributes are later set in set_dark_mode
        # Other attributes
        self.device = None
        self.image = None
        self.draw = None
        self.mask = None
        self.dark_mode = False

    def init(self, fullcircle=False, dark_mode=False):
        config_path = str(Path(__file__).resolve().parent.joinpath('st7789.conf'))
        self.device = radar_opts.get_device(['-f', config_path])
        self.device.contrast(255)  # set full contrast
        self.image = Image.new(self.device.mode, self.device.size)
        self.draw = ImageDraw.Draw(self.image)
        self.set_dark_mode(dark_mode)
        self.sizex = self.device.width
        self.sizey = self.device.height
        if not fullcircle:
            self.zeroy = 150  # not centered
            self.max_pixel = 290
        else:
            self.zeroy = self.sizey / 2
            self.max_pixel = self.sizey
        self.zerox = self.sizex // 2
        # self.zerox = 214               # BGL
        # self.zeroy = 120               # BGL
        # self.max_pixel =  213 # self.sizex    # BGL  so that we get a full circle
        self.ah_zeroy = self.sizey // 2  # zero line for ahrs
        self.ah_zerox = self.sizex // 2
        self.czerox = self.sizex // 2
        self.czeroy = self.sizey // 2
        start = time.time()
        # do sync version of display to measure time
        self.display()
        end = time.time()
        display_refresh = end - start
        # compass
        pic_path = str(Path(__file__).resolve().parent.joinpath('plane-white-128x128.bmp'))
        self.compass_aircraft = Image.open(pic_path).convert("RGBA")
        if not self.dark_mode:
            self.compass_aircraft = Image.eval(self.compass_aircraft, lambda x: 255 - x)
        self.mask = Image.new('1', (self.LARGE * 2, self.LARGE * 2))
        self.cdraw = ImageDraw.Draw(self.mask)
        self.rlog.debug(f'ST7789 selected: sizex={self.sizex} sizey={self.sizey} '
                        f'zero=({self.zerox}, {self.zeroy}) refresh-time: {round(self.display_refresh, 2)} secs')
        return self.sizex, self.zerox, self.zeroy, display_refresh

    def set_dark_mode(self, dark_mode):
        """Set dark mode and update color constants accordingly"""
        self.dark_mode = dark_mode
        if dark_mode:
            self.BG_COLOR = "black"
            self.TEXT_COLOR = "white"
            self.HIGHLIGHT_COLOR = "red"
            self.AIRCRAFT_COLOR = "red"
            self.AIRCRAFT_OUTLINE = "white"
            self.MODE_S_COLOR = "white"
            # AHRS colors
            self.AHRS_EARTH_COLOR = "sandybrown"
            self.AHRS_SKY_COLOR = "skyblue"
            self.AHRS_HORIZON_COLOR = "white"
            self.AHRS_MARKS_COLOR = "white"
            self.WARNING_COLOR = "red"
        else:
            self.BG_COLOR = "white"
            self.TEXT_COLOR = "black"
            self.HIGHLIGHT_COLOR = "red"
            self.AIRCRAFT_COLOR = "red"
            self.AIRCRAFT_OUTLINE = "black"
            self.MODE_S_COLOR = "black"
            # AHRS colors
            self.AHRS_EARTH_COLOR = "sandybrown"
            self.AHRS_SKY_COLOR = "skyblue"
            self.AHRS_HORIZON_COLOR = "white"
            self.AHRS_MARKS_COLOR = "white"
            self.WARNING_COLOR = "red"

    def cleanup(self):
        self.device.cleanup()

    def refresh(self):
        pass

    def display(self):
        self.device.display(self.image)

    def is_busy(self):
        # tft is never busy, no refresh
        return False

    @staticmethod
    def next_arcposition(old_arcposition, exclude_from=0, exclude_to=0):
        return dcommon.GenericDisplay().next_arcposition(old_arcposition,
                                                         exclude_from=ST7789().ARCPOSITION_EXCLUDE_FROM,
                                                         exclude_to=ST7789().ARCPOSITION_EXCLUDE_TO)

    def clear(self):
        self.draw.rectangle((0, 0, self.sizex - 1, self.sizey - 1), fill=self.BG_COLOR)

    def startup(self, version, target_ip, seconds):
        logopath = Path(__file__).resolve().parent / 'stratux-logo-128x128.bmp'
        logo = Image.open(logopath)
        self.draw.rectangle((0, 0, self.sizex-1, self.sizey-1), fill=self.BG_COLOR)
        self.draw.rectangle((self.zerox - 64, 10, self.zerox + 64, 128+10), fill="blue")
        self.draw.bitmap((self.zerox - 64, 10), logo, fill="white")
        self.centered_text(self.sizey - 2*self.VERYLARGE, "Radar "+version, self.VERYLARGE, color=self.TEXT_COLOR)
        self.centered_text(self.sizey - 10 - self.SMALL, "Connecting to " + target_ip, self.SMALL, color=self.TEXT_COLOR)
        self.display()
        time.sleep(seconds)


    def situation(self, connected, gpsconnected, ownalt, course, rrange, altdifference, bt_devices, sound_active,
                  gps_quality, gps_h_accuracy, optical_alive, basemode, extsound, co_alarmlevel, co_alarmstring):
        self.draw.ellipse((self.zerox - self.max_pixel // 2, self.zeroy - self.max_pixel // 2,
                           self.zerox + self.max_pixel // 2, self.zeroy + self.max_pixel // 2), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - self.max_pixel // 4, self.zeroy - self.max_pixel // 4,
                           self.zerox + self.max_pixel // 4, self.zeroy + self.max_pixel // 4), outline=self.TEXT_COLOR)
        self.draw.ellipse((self.zerox - 2, self.zeroy - 2, self.zerox + 2, self.zeroy + 2), outline=self.TEXT_COLOR)

        self.draw.text((5, 1), f"{rrange} nm", font=self.fonts[self.SMALL], fill=self.TEXT_COLOR)

        if gps_quality == 0:
            t = "GPS-NoFix"
        elif gps_quality == 1:
            t = f"3D GPS\n{round(gps_h_accuracy)}m"
        elif gps_quality == 2:
            t = f"DGNSS\n{round(gps_h_accuracy)}m"
        else:
            t = ""
        if basemode:
            t += "\nGround\nmode"
        self.draw.text((5, self.SMALL + 5), t, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)

        t = f"FL{round(ownalt / 100)}"
        textlength = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - textlength - 5, self.SMALL + 5), t, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)

        t = f"{altdifference} ft"
        textlength = self.draw.textlength(t, self.fonts[self.SMALL])
        self.draw.text((self.sizex - textlength - 5, 1), t, font=self.fonts[self.SMALL], fill=self.TEXT_COLOR, align="right")

        self.centered_text(5, f"{course}°", self.SMALL)

        if not gpsconnected:
            self.centered_text(55, "No GPS", self.SMALL)
        if not connected:
            self.centered_text(30, "No Connection!", self.SMALL)
        if co_alarmlevel > 0:
            self.centered_text(self.sizey - 2 * self.SMALL, f"CO Alarm: {co_alarmstring}", self.SMALL,
                               color=self.WARNING_COLOR)
        if extsound or bt_devices > 0:  # extsound means and sound devices has been found
            if sound_active:  # means user left sound switched on
                if extsound:
                    btcolor = "orange"
                    text = "\uf028"  # volume symbol
                    if bt_devices > 0:
                        btcolor = "blue"
                else:  # bt_devices is > 0 anyhow
                    btcolor = "blue"
                    text = '\uf293'  # bluetooth symbol
            else:
                btcolor = "red"
                text = '\uf1f6'  # bell off symbol
            tl = self.draw.textlength(text, self.awesomefont)
            self.draw.text((self.sizex - tl, self.sizey - 2 * self.SMALL), text, font=self.awesomefont,
                           fill=btcolor, align="right")

    def gmeter(self, current, maxg, ming, error_message):
        gm_size = self.sizey
        self.meter(current, -3, 5, 110, 430, gm_size, self.sizey//2, self.sizey//2, 1, 0.25,
                   "G-Force", None)
        self.draw.text((self.zerox + 40, self.sizey//2-self.SMALL), f"max:", font=self.fonts[self.SMALL], fill="magenta")
        self.draw.text((self.zerox + 90, self.sizey // 2 - self.SMALL), f"{maxg:+1.2f}", font=self.fonts[self.SMALL],
                       fill="magenta")
        if error_message:
            self.centered_text(77, error_message, self.LARGE, color="red")
        self.draw.text((self.zerox + 40, self.sizey//2), f"min:", font=self.fonts[self.SMALL], fill="magenta")
        self.draw.text((self.zerox + 90, self.sizey//2), f"{ming:+1.2f}", font=self.fonts[self.SMALL], fill="magenta")
        self.bottom_line("", "                   Mode", "Reset")

    def vsi(self, vertical_speed, flight_level, gps_speed, gps_course, gps_altitude, vertical_max, vertical_min,
            error_message):
        self.meter(vertical_speed / 100, -20, 20, 110, 430, self.sizey, self.czerox,
                   self.czeroy, 5, 1, "Vert Spd", "100ft/min",
                   middle_fontsize=self.SMALL)
        self.draw.text((12, self.sizey // 2 - self.VERYSMALL - 10), "up", font=self.fonts[self.VERYSMALL],
                       fill=self.TEXT_COLOR, align="left")
        self.draw.text((12, self.sizey // 2 + 10), "dn", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR,
                       align="left")
        if error_message:
            self.centered_text(30, error_message, self.LARGE, color="red")
        self.bottom_line("", "", "")


    def stratux(self, stat, altitude, gps_alt, gps_quality):
        starty = 0
        self.centered_text(0, f"Stratux {stat['version']}", self.SMALL)
        starty += self.SMALL+6
        bar_start, bar_end = 80, 260
        line_offset = 4
        colors = {'outline': self.TEXT_COLOR, 'green': self.TEXT_COLOR}
        starty = self.bar(starty, "1090", stat['ES_messages_last_minute'], stat['ES_messages_max'],
                          bar_start, bar_end, colors, line_offset=line_offset)
        if stat['OGN_connected']:
            starty = self.bar(starty, "OGN", stat['OGN_messages_last_minute'], stat['OGN_messages_max'],
                              bar_start, bar_end, colors, line_offset=line_offset)
            noise_text = f"{round(stat['OGN_noise_db'], 1)}@{round(stat['OGN_gain_db'], 1)}dB"
            starty = self.bar(starty, "noise", stat['OGN_noise_db'], 25,
                              bar_start, bar_end, colors, unit="dB", minval=1, valtext=noise_text, line_offset=line_offset)
        if stat['UATRadio_connected']:
            starty = self.bar(starty, "UAT", stat['UAT_messages_last_minute'], stat['UAT_messages_max'],
                              bar_start, bar_end, colors, line_offset=line_offset)
        colors = {'outline': self.TEXT_COLOR, 'green': 'lime', 'yellow': 'DarkOrange',
                  'red': 'red', 'yellow_value': 70, 'red_value': 80}
        if stat['CPUTemp'] > -300:    # -300 means no value available
            starty = self.bar(starty, "temp", round(stat['CPUTemp'], 1), round(stat['CPUTempMax'], 0),
                              bar_start, bar_end, colors, unit="°C", line_offset=line_offset)
        self.draw.text((0, starty), "GPS hw", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        self.draw.text((bar_start, starty), stat['GPS_detected_type'], font=self.fonts[self.VERYSMALL],
                       fill=self.TEXT_COLOR)
        starty += self.VERYSMALL + 2
        t = "3D GPS " if gps_quality == 1 else "DGNSS " if gps_quality == 2 else "GPS"
        self.draw.text((0, starty), t, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        gps = f"{round(stat['GPS_position_accuracy'], 1)}m" if stat['GPS_position_accuracy'] < 19999 else "NoFix"
        self.draw.text((bar_start, starty), gps, font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        t = f"{stat['GPS_satellites_locked']}/{stat['GPS_satellites_seen']}/{stat['GPS_satellites_tracked']}"
        self.right_text(starty, t, self.VERYSMALL)
        starty += self.VERYSMALL + 2

        alt = f"{gps_alt:.0f}" if stat['GPS_position_accuracy'] < 19999 else " ---"
        self.draw.text((0, starty), f"P-Alt {round(altitude)} ft", font=self.fonts[self.VERYSMALL],
                       fill=self.TEXT_COLOR)
        self.draw.text((bar_start + 20, starty), f"Corr {stat['AltitudeOffset']:+} ft", font=self.fonts[self.VERYSMALL],
                       fill=self.TEXT_COLOR)
        self.right_text(starty, f"GPS-Alt {alt} ft", self.VERYSMALL)
        starty += self.VERYSMALL + 4

        self.draw.text((0, starty), "sensors", font=self.fonts[self.VERYSMALL], fill=self.TEXT_COLOR)
        col = "lime" if stat['IMUConnected'] else "red"
        x = self.round_text(bar_start, starty, "IMU", bg_color=col, text_color=self.TEXT_COLOR)
        col = "lime" if stat['BMPConnected'] else "red"
        self.round_text(x, starty, "BMP", bg_color=col, text_color=self.TEXT_COLOR)
        self.bottom_line("+10ft", "Mode", "-10ft")

    def cowarner(self, co_values, co_max, r0, timeout, alarmlevel, alarmtext, simulation_mode=False): # draw graph and co values
        self.centered_text(0, alarmtext, self.LARGE)
        graphpos = (0, self.LARGE + 5)
        graphsize = (300, 150)
        self.graph(graphpos, graphsize, co_values, 0, 120, timeout, value_line1=50, value_line2=100,
                   glinewidth=2, linewidth=2)
        if len(co_values) > 0:
            color = "lime" if co_values[-1] < 50 else "red"
            self.round_text(50, self.sizey - 2 * self.VERYSMALL - 6, "act: {:3d}".format(co_values[-1]),
                            bg_color=color, text_color=self.TEXT_COLOR)
        color = "lime" if co_max < 50 else "red"
        self.round_text(self.sizex // 2 + 50, self.sizey - 2 * self.VERYSMALL - 6, "max: {:3d}".format(co_max),
                        bg_color=color, text_color=self.TEXT_COLOR)
        if simulation_mode:
            self.round_text(4 * self.VERYSMALL + 10, self.sizey // 4 + 4, "simulation mode", out_color=self.TEXT_COLOR)
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
            self.centered_text(80, error_message, self.LARGE, self.WARNING_COLOR)
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
        offset = 5
        if 'start_time' in values:
            st = values['start_time'].strftime("%H:%M:%S,%f")[:-5]
        else:
            st = '---'
        lines = [
            ("t-off time", st),
            ("t-off alt [ft]", self.form_line(values, 'start_altitude', "{:5.1f}")),
            ("t-off dist [m]", self.form_line(values, 'takeoff_distance', "{:3.1f}")),
            ("obst dist [m]", self.form_line(values, 'obstacle_distance_start', "{:3.1f}")),
        ]
        starty = self.dashboard(offset, self.SMALL, self.sizex - 2* offset, lines)
        if 'landing_time' in values:
            lt = values['landing_time'].strftime("%H:%M:%S,%f")[:-5]
        else:
            lt = '---'
        lines = [
            ("ldg time", lt),
            ("ldg alt [ft]", self.form_line(values, 'landing_altitude', "{:5.1f}")),
            ("ldg dist [m]", self.form_line(values, 'landing_distance', "{:3.1f}")),
            ("obst dist [m]", self.form_line(values, 'obstacle_distance_landing', "{:3.1f}")),
        ]
        starty = self.dashboard(offset, starty, self.sizex - 2 * offset, lines)
        if current_stats:
            if ground_warnings:
                dest_alt_str = f"{dest_altitude:+5.0f}" if dest_alt_valid else "---"
                gps_alt_str = f"{gps_altitude:+5.0f}" if gps_valid else "---"
                lines = [
                    ("Act GPS-Alt [ft]", gps_alt_str),
                    ("Dest. Alt [ft]", dest_alt_str),
                ]
                self.dashboard(offset, starty, self.sizex- 2 * offset  , lines)
                self.bottom_line("+/-100ft", "  Back", "+/-10ft")
            else:
                self.bottom_line("", "Back", "")
        else:  # stored stats
            left = "Prev" if prev_stat else ""
            right = "Next" if next_stat else ""
            self.bottom_line(left, "Exit", right)


# instantiate a single object in the file, needs to be done and inherited in every display module
radar_display = ST7789()
